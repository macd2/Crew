#!/usr/bin/env python3
"""Crew Runtime Events: in-process lifecycle hooks and REST notification dispatch.

Replaces brittle background terminal watchers (`crew_card.py watch --card <id>`) with
deterministic, in-process event pub/sub and HTTP/REST notification mechanisms.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

_logger = logging.getLogger("crew.runtime_events")

# Standard Card Event Kinds
CARD_CREATED = "card_created"
CARD_CLAIMED = "card_claimed"
CARD_BLOCKED = "card_blocked"
CARD_REVIEW = "card_review"
CARD_COMPLETED = "card_completed"
CARD_ABANDONED = "card_abandoned"
CARD_UPDATED = "card_updated"

ALL_CARD_EVENTS: Set[str] = {
    CARD_CREATED,
    CARD_CLAIMED,
    CARD_BLOCKED,
    CARD_REVIEW,
    CARD_COMPLETED,
    CARD_ABANDONED,
    CARD_UPDATED,
}


@dataclass(frozen=True)
class Event:
    """An immutable runtime event describing a card state transition or lifecycle action."""

    kind: str
    card_id: str
    status: str = ""
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a JSON-serializable dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize event to a JSON string."""
        return json.dumps(self.to_dict(), default=str)


class EventBus:
    """Thread-safe in-process publish/subscribe event bus.

    Provides subscriber error isolation: an exception raised by one callback
    is logged and captured without disrupting subsequent subscribers or the publisher.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self._logger = logger or _logger

    def subscribe(self, kind: str, callback: Callable[[Event], None]) -> Callable[[], None]:
        """Register a callback for an event kind, or '*' for all events.

        Returns an unregister callable for convenience.
        """
        with self._lock:
            if kind not in self._subscribers:
                self._subscribers[kind] = []
            if callback not in self._subscribers[kind]:
                self._subscribers[kind].append(callback)

        def _unsubscribe() -> None:
            self.unsubscribe(kind, callback)

        return _unsubscribe

    def unsubscribe(self, kind: str, callback: Callable[[Event], None]) -> bool:
        """Remove a previously registered callback."""
        with self._lock:
            if kind in self._subscribers and callback in self._subscribers[kind]:
                self._subscribers[kind].remove(callback)
                if not self._subscribers[kind]:
                    del self._subscribers[kind]
                return True
            return False

    def publish(self, event: Event) -> List[Exception]:
        """Dispatch event to all matching subscribers.

        Executes callbacks synchronously with strict exception isolation.
        Returns a list of caught exceptions (empty if all callbacks succeeded).
        """
        callbacks: List[Callable[[Event], None]] = []
        with self._lock:
            # Targeted subscribers
            if event.kind in self._subscribers:
                callbacks.extend(self._subscribers[event.kind])
            # Wildcard subscribers
            if "*" in self._subscribers:
                callbacks.extend(self._subscribers["*"])

        errors: List[Exception] = []
        for cb in callbacks:
            try:
                cb(event)
            except Exception as exc:
                errors.append(exc)
                self._logger.warning(
                    "Subscriber %r raised an unhandled exception for event %s on card %s: %s",
                    getattr(cb, "__name__", str(cb)),
                    event.kind,
                    event.card_id,
                    exc,
                    exc_info=True,
                )
        return errors

    def clear(self) -> None:
        """Remove all subscribers (used for cleanup and testing)."""
        with self._lock:
            self._subscribers.clear()

    def subscriber_count(self, kind: Optional[str] = None) -> int:
        """Return the number of active subscribers for a kind (or total across all kinds)."""
        with self._lock:
            if kind is not None:
                return len(self._subscribers.get(kind, []))
            return sum(len(cbs) for cbs in self._subscribers.values())


class RESTNotifier:
    """Dispatches Event payloads to configured HTTP/REST endpoints.

    Designed for resilience: timeouts, network failures, and HTTP errors are
    safely caught, logged, and isolated from core agent execution.
    """

    def __init__(
        self,
        endpoints: List[str] | str,
        timeout: float = 2.0,
        headers: Optional[Dict[str, str]] = None,
        logger: Optional[logging.Logger] = None,
        opener: Optional[Any] = None,
    ):
        if isinstance(endpoints, str):
            endpoints = [endpoints]
        self.endpoints = [ep.strip() for ep in endpoints if ep and ep.strip()]
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}
        if headers:
            self.headers.update(headers)
        self._logger = logger or _logger
        self._opener = opener or urllib.request.urlopen

    def notify(self, event: Event) -> Dict[str, bool]:
        """Post the event to all configured endpoints.

        Returns a dictionary mapping endpoint URL to boolean success status.
        """
        results: Dict[str, bool] = {}
        data = event.to_json().encode("utf-8")

        for endpoint in self.endpoints:
            req = urllib.request.Request(endpoint, data=data, headers=self.headers, method="POST")
            try:
                with self._opener(req, timeout=self.timeout) as resp:
                    status = getattr(resp, "status", None) or getattr(resp, "code", 200)
                    results[endpoint] = 200 <= status < 300
            except urllib.error.HTTPError as http_err:
                self._logger.warning(
                    "REST notification to %s failed with HTTP %d: %s",
                    endpoint,
                    http_err.code,
                    http_err.reason,
                )
                results[endpoint] = False
            except (urllib.error.URLError, TimeoutError, OSError) as net_err:
                self._logger.warning(
                    "REST notification network error reaching %s: %s",
                    endpoint,
                    net_err,
                )
                results[endpoint] = False
            except Exception as exc:
                self._logger.error(
                    "Unexpected error during REST notification to %s: %s",
                    endpoint,
                    exc,
                    exc_info=True,
                )
                results[endpoint] = False

        return results

    def handle_event(self, event: Event) -> None:
        """Subscriber callback adapter for EventBus registration."""
        self.notify(event)


# Global default event bus instance
_DEFAULT_BUS = EventBus()


def get_event_bus() -> EventBus:
    """Return the global default EventBus instance."""
    return _DEFAULT_BUS


def emit_card_event(
    kind: str,
    card_id: str,
    status: str = "",
    bus: Optional[EventBus] = None,
    payload: Optional[Dict[str, Any]] = None,
    **extra: Any,
) -> Event:
    """Convenience helper to construct and publish a card domain event."""
    merged_payload = dict(payload or {})
    merged_payload.update(extra)
    event = Event(
        kind=kind,
        card_id=card_id,
        status=status,
        payload=merged_payload,
    )
    target_bus = bus or _DEFAULT_BUS
    target_bus.publish(event)
    return event


def handle_kanban_lifecycle_event(
    event_name: str,
    task_id: str,
    bus: Optional[EventBus] = None,
    **fields: Any,
) -> Optional[Event]:
    """Translate Hermes core Kanban lifecycle hooks into Crew domain events.

    Maps:
      - kanban_task_completed -> CARD_COMPLETED (status="done")
      - kanban_task_blocked   -> CARD_BLOCKED   (status="blocked")
      - kanban_task_claimed   -> CARD_CLAIMED   (status="in_progress")
      - on_kanban_task_updated-> CARD_UPDATED
    """
    mapping = {
        "kanban_task_completed": (CARD_COMPLETED, "done"),
        "kanban_task_blocked": (CARD_BLOCKED, "blocked"),
        "kanban_task_claimed": (CARD_CLAIMED, "in_progress"),
        "on_kanban_task_updated": (CARD_UPDATED, str(fields.get("status") or "")),
    }

    if event_name not in mapping:
        return None

    kind, status = mapping[event_name]
    return emit_card_event(kind=kind, card_id=task_id, status=status, bus=bus, payload=dict(fields))


@dataclass
class WebhookSubscription:
    """Represents an active webhook subscription."""
    url: str
    events: List[str]
    headers: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    unsub_handles: List[Callable[[], None]] = field(default_factory=list, repr=False)


class WebhookManager:
    """Manages active webhook subscriptions dispatching via RESTNotifier."""

    def __init__(self, bus: Optional[EventBus] = None):
        self._bus = bus or _DEFAULT_BUS
        self._lock = threading.RLock()
        self._webhooks: Dict[str, WebhookSubscription] = {}

    def register(
        self,
        url: str,
        events: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 2.0,
        opener: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Register a webhook endpoint URL to receive events."""
        url = url.strip()
        if not url:
            raise ValueError("URL cannot be empty")
        ev_list = [e.strip() for e in (events or ["*"]) if e.strip()]
        if not ev_list:
            ev_list = ["*"]

        with self._lock:
            if url in self._webhooks:
                self.unregister(url)

            notifier = RESTNotifier(endpoints=[url], timeout=timeout, headers=headers, opener=opener)
            handles: List[Callable[[], None]] = []
            for ev in ev_list:
                unsub = self._bus.subscribe(ev, notifier.handle_event)
                handles.append(unsub)

            sub = WebhookSubscription(
                url=url,
                events=ev_list,
                headers=dict(headers or {}),
                unsub_handles=handles,
            )
            self._webhooks[url] = sub
            return {
                "status": "ok",
                "url": url,
                "events": ev_list,
                "active_webhooks": len(self._webhooks),
            }

    def unregister(self, url: str) -> bool:
        """Unregister a webhook endpoint URL."""
        url = url.strip()
        with self._lock:
            sub = self._webhooks.pop(url, None)
            if sub:
                for h in sub.unsub_handles:
                    try:
                        h()
                    except Exception:
                        pass
                return True
            return False

    def list_all(self) -> List[Dict[str, Any]]:
        """Return all active webhook subscriptions."""
        with self._lock:
            return [
                {
                    "url": sub.url,
                    "events": list(sub.events),
                    "created_at": sub.created_at,
                }
                for sub in self._webhooks.values()
            ]

    def clear(self) -> int:
        """Clear all active webhook subscriptions."""
        with self._lock:
            count = len(self._webhooks)
            for url in list(self._webhooks.keys()):
                self.unregister(url)
            return count


_DEFAULT_WEBHOOK_MANAGER = WebhookManager()


def get_webhook_manager() -> WebhookManager:
    """Return the global default WebhookManager instance."""
    return _DEFAULT_WEBHOOK_MANAGER

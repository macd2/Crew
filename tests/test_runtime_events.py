#!/usr/bin/env python3
"""Tests for crew runtime events: in-process pub/sub, card lifecycle hooks, and REST notifications."""
import email.message
import json
import sys
import urllib.error
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest import TestCase, mock

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime_events import (  # noqa: E402
    CARD_BLOCKED,
    CARD_CLAIMED,
    CARD_COMPLETED,
    CARD_CREATED,
    CARD_REVIEW,
    Event,
    EventBus,
    RESTNotifier,
    WebhookManager,
    emit_card_event,
    handle_kanban_lifecycle_event,
)


class EventModelTests(TestCase):
    def test_event_immutability_and_defaults(self):
        ev = Event(kind=CARD_COMPLETED, card_id="c_123", status="done", payload={"summary": "all done"})
        self.assertEqual(ev.kind, CARD_COMPLETED)
        self.assertEqual(ev.card_id, "c_123")
        self.assertEqual(ev.status, "done")
        self.assertTrue(ev.timestamp > 0)
        self.assertTrue(len(ev.event_id) > 0)

        # Frozen dataclass should reject mutations
        with self.assertRaises(FrozenInstanceError):
            ev.status = "failed"  # type: ignore

    def test_event_serialization(self):
        ev = Event(kind=CARD_BLOCKED, card_id="c_456", status="blocked", payload={"reason": "tests failed"})
        d = ev.to_dict()
        self.assertEqual(d["kind"], CARD_BLOCKED)
        self.assertEqual(d["card_id"], "c_456")
        self.assertEqual(d["payload"]["reason"], "tests failed")

        s = ev.to_json()
        parsed = json.loads(s)
        self.assertEqual(parsed["card_id"], "c_456")
        self.assertEqual(parsed["kind"], CARD_BLOCKED)


class EventBusTests(TestCase):
    def setUp(self):
        self.bus = EventBus()

    def test_targeted_subscription_and_dispatch(self):
        received = []
        self.bus.subscribe(CARD_COMPLETED, lambda e: received.append(e))

        ev_done = Event(kind=CARD_COMPLETED, card_id="card_1", status="done")
        ev_blocked = Event(kind=CARD_BLOCKED, card_id="card_1", status="blocked")

        errors = self.bus.publish(ev_done)
        self.assertEqual(errors, [])
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].card_id, "card_1")

        # Blocked event should not trigger the completed subscriber
        self.bus.publish(ev_blocked)
        self.assertEqual(len(received), 1)

    def test_wildcard_subscription(self):
        received = []
        self.bus.subscribe("*", lambda e: received.append(e.kind))

        self.bus.publish(Event(kind=CARD_CREATED, card_id="c1"))
        self.bus.publish(Event(kind=CARD_CLAIMED, card_id="c1"))
        self.bus.publish(Event(kind=CARD_COMPLETED, card_id="c1"))

        self.assertEqual(received, [CARD_CREATED, CARD_CLAIMED, CARD_COMPLETED])

    def test_unsubscription(self):
        received = []
        unsub = self.bus.subscribe(CARD_COMPLETED, lambda e: received.append(e))
        self.assertEqual(self.bus.subscriber_count(CARD_COMPLETED), 1)

        ev = Event(kind=CARD_COMPLETED, card_id="c_test")
        self.bus.publish(ev)
        self.assertEqual(len(received), 1)

        # Unsubscribe via closure
        unsub()
        self.assertEqual(self.bus.subscriber_count(CARD_COMPLETED), 0)

        self.bus.publish(ev)
        self.assertEqual(len(received), 1)

    def test_subscriber_error_isolation(self):
        """A subscriber raising an exception must not crash other subscribers or the publisher."""
        success_calls = []

        def failing_cb(e):
            raise ValueError("simulated subscriber bug")

        def working_cb(e):
            success_calls.append(e.card_id)

        self.bus.subscribe(CARD_COMPLETED, failing_cb)
        self.bus.subscribe(CARD_COMPLETED, working_cb)

        ev = Event(kind=CARD_COMPLETED, card_id="c_isolated")
        errors = self.bus.publish(ev)

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ValueError)
        self.assertEqual(success_calls, ["c_isolated"])

    def test_clear_subscribers(self):
        self.bus.subscribe(CARD_COMPLETED, lambda e: None)
        self.bus.subscribe("*", lambda e: None)
        self.assertGreater(self.bus.subscriber_count(), 0)

        self.bus.clear()
        self.assertEqual(self.bus.subscriber_count(), 0)


class DomainEventAndBridgeTests(TestCase):
    def setUp(self):
        self.bus = EventBus()

    def test_emit_card_event(self):
        received = []
        self.bus.subscribe(CARD_REVIEW, lambda e: received.append(e))

        ev = emit_card_event(
            kind=CARD_REVIEW,
            card_id="c_rev",
            status="review",
            bus=self.bus,
            reviewer="crew-verifier",
            summary="ready for test",
        )

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].card_id, "c_rev")
        self.assertEqual(received[0].payload["reviewer"], "crew-verifier")
        self.assertEqual(ev, received[0])

    def test_kanban_lifecycle_event_bridge(self):
        captured = []
        self.bus.subscribe("*", lambda e: captured.append(e))

        # Test completion
        ev_comp = handle_kanban_lifecycle_event(
            "kanban_task_completed",
            "t_1",
            bus=self.bus,
            summary="shipped feature",
            run_id=42,
        )
        self.assertIsNotNone(ev_comp)
        assert ev_comp is not None
        self.assertEqual(ev_comp.kind, CARD_COMPLETED)
        self.assertEqual(ev_comp.status, "done")
        self.assertEqual(ev_comp.payload["summary"], "shipped feature")

        # Test blocked
        ev_block = handle_kanban_lifecycle_event(
            "kanban_task_blocked",
            "t_2",
            bus=self.bus,
            reason="missing api key",
            kind="needs_input",
        )
        self.assertIsNotNone(ev_block)
        assert ev_block is not None
        self.assertEqual(ev_block.kind, CARD_BLOCKED)
        self.assertEqual(ev_block.status, "blocked")
        self.assertEqual(ev_block.payload["reason"], "missing api key")

        # Test claimed
        ev_claim = handle_kanban_lifecycle_event(
            "kanban_task_claimed",
            "t_3",
            bus=self.bus,
            assignee="crew-worker",
            run_id=1,
        )
        self.assertIsNotNone(ev_claim)
        assert ev_claim is not None
        self.assertEqual(ev_claim.kind, CARD_CLAIMED)
        self.assertEqual(ev_claim.status, "in_progress")

        # Test unhandled event returns None
        ev_unknown = handle_kanban_lifecycle_event("unknown_event", "t_4", bus=self.bus)
        self.assertIsNone(ev_unknown)

        self.assertEqual(len(captured), 3)


class RESTNotifierTests(TestCase):
    def test_successful_rest_notification(self):
        mock_response = mock.MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response

        mock_opener = mock.MagicMock(return_value=mock_response)

        notifier = RESTNotifier(
            endpoints=["http://localhost:8000/api/plugins/crew/events"],
            headers={"Authorization": "Bearer token123"},
            opener=mock_opener,
        )

        ev = Event(kind=CARD_COMPLETED, card_id="c_rest", status="done", payload={"result": "ok"})
        results = notifier.notify(ev)

        self.assertEqual(results, {"http://localhost:8000/api/plugins/crew/events": True})
        self.assertTrue(mock_opener.called)
        req = mock_opener.call_args[0][0]
        self.assertEqual(req.full_url, "http://localhost:8000/api/plugins/crew/events")
        self.assertEqual(req.headers.get("Authorization"), "Bearer token123")
        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["card_id"], "c_rest")
        self.assertEqual(payload["kind"], CARD_COMPLETED)

    def test_http_error_handling(self):
        msg = email.message.Message()
        mock_opener = mock.MagicMock(
            side_effect=urllib.error.HTTPError(
                url="http://endpoint/err",
                code=500,
                msg="Server Error",
                hdrs=msg,
                fp=None,
            )
        )

        notifier = RESTNotifier(
            endpoints=["http://endpoint/err"],
            opener=mock_opener,
        )

        ev = Event(kind=CARD_BLOCKED, card_id="c_err")
        results = notifier.notify(ev)

        self.assertEqual(results, {"http://endpoint/err": False})

    def test_network_timeout_handling(self):
        mock_opener = mock.MagicMock(side_effect=TimeoutError("Connection timed out"))

        notifier = RESTNotifier(
            endpoints=["http://endpoint/timeout"],
            timeout=1.0,
            opener=mock_opener,
        )

        ev = Event(kind=CARD_BLOCKED, card_id="c_timeout")
        results = notifier.notify(ev)

        self.assertEqual(results, {"http://endpoint/timeout": False})

    def test_event_bus_integration_with_rest_notifier(self):
        bus = EventBus()
        mock_response = mock.MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        mock_opener = mock.MagicMock(return_value=mock_response)

        notifier = RESTNotifier("http://localhost:8000/events", opener=mock_opener)
        bus.subscribe(CARD_COMPLETED, notifier.handle_event)

        ev = Event(kind=CARD_COMPLETED, card_id="c_bus_rest", status="done")
        bus.publish(ev)

        self.assertEqual(mock_opener.call_count, 1)


class EndToEndEventDrivenWorkflowTest(TestCase):
    """Verifies complete card state transition tracking without background terminal polling."""

    def test_full_card_lifecycle_callback_flow(self):
        bus = EventBus()
        timeline = []

        # Client registers to watch the card
        def on_timeline(ev: Event):
            timeline.append((ev.kind, ev.status, ev.payload.get("step")))

        bus.subscribe("*", on_timeline)

        # 1. Card opened
        emit_card_event(CARD_CREATED, "card_e2e", status="ready", bus=bus, step=1)
        # 2. Worker claimed card
        emit_card_event(CARD_CLAIMED, "card_e2e", status="in_progress", bus=bus, step=2)
        # 3. Worker submitted for review
        emit_card_event(CARD_REVIEW, "card_e2e", status="review", bus=bus, step=3)
        # 4. Verifier passes card, marking completed
        emit_card_event(CARD_COMPLETED, "card_e2e", status="done", bus=bus, step=4, summary="Verified successfully")

        expected = [
            (CARD_CREATED, "ready", 1),
            (CARD_CLAIMED, "in_progress", 2),
            (CARD_REVIEW, "review", 3),
            (CARD_COMPLETED, "done", 4),
        ]
        self.assertEqual(timeline, expected)


class WebhookManagerTests(TestCase):
    def setUp(self):
        self.bus = EventBus()
        self.mgr = WebhookManager(bus=self.bus)

    def test_register_and_list(self):
        res = self.mgr.register("http://example.com/webhook", events=["card_created"])
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["url"], "http://example.com/webhook")
        self.assertEqual(res["events"], ["card_created"])
        self.assertEqual(res["active_webhooks"], 1)

        all_subs = self.mgr.list_all()
        self.assertEqual(len(all_subs), 1)
        self.assertEqual(all_subs[0]["url"], "http://example.com/webhook")

    def test_unregister(self):
        self.mgr.register("http://example.com/webhook")
        self.assertTrue(self.mgr.unregister("http://example.com/webhook"))
        self.assertFalse(self.mgr.unregister("http://example.com/webhook"))
        self.assertEqual(len(self.mgr.list_all()), 0)

    def test_clear(self):
        self.mgr.register("http://example.com/w1")
        self.mgr.register("http://example.com/w2")
        self.assertEqual(self.mgr.clear(), 2)
        self.assertEqual(len(self.mgr.list_all()), 0)

    def test_webhook_dispatches_on_bus_event(self):
        called_with = []

        def mock_opener(req, timeout=2.0):
            called_with.append(json.loads(req.data.decode("utf-8")))
            resp = mock.MagicMock()
            resp.status = 200
            return resp

        self.mgr.register(
            "http://example.com/webhook",
            events=["card_completed"],
            opener=mock_opener,
        )

        # Emit irrelevant event
        emit_card_event(CARD_CREATED, "c1", bus=self.bus)
        self.assertEqual(len(called_with), 0)

        # Emit subscribed event
        emit_card_event(CARD_COMPLETED, "c1", status="done", bus=self.bus, summary="Done")
        self.assertEqual(len(called_with), 1)
        self.assertEqual(called_with[0]["card_id"], "c1")
        self.assertEqual(called_with[0]["kind"], CARD_COMPLETED)

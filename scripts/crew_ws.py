"""Minimal WebSocket client (stdlib only) for talking to the Chrome DevTools protocol.

The package is stdlib-only by design: no `pip install websockets` on a fresh profile. This speaks
just enough of RFC 6455 (text frames, masked client frames, no extensions) for CDP calls.
"""
import base64
import json
import os
import socket
import struct
import urllib.parse


class WSError(RuntimeError):
    pass


class WSClient:
    def __init__(self, url, timeout=20):
        u = urllib.parse.urlparse(url)
        if u.scheme not in ("ws", "http"):
            raise WSError("unsupported scheme %s" % u.scheme)
        self.host = u.hostname or "127.0.0.1"
        self.port = u.port or 80
        self.path = u.path + (("?" + u.query) if u.query else "")
        self.timeout = timeout
        self.sock = socket.create_connection((self.host, self.port), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = ("GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n"
               % (self.path, self.host, self.port, key))
        self.sock.sendall(req.encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise WSError("devtools closed the connection during handshake")
            head += chunk
        if b"101" not in head.split(b"\r\n", 1)[0]:
            raise WSError("devtools refused the handshake: %s" % head.split(b"\r\n", 1)[0].decode())
        self._rest = head.split(b"\r\n\r\n", 1)[1]

    def _send_text(self, text):
        data = text.encode()
        mask = os.urandom(4)
        header = bytearray([0x81])                     # FIN + text
        n = len(data)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(bytes(header) + mask + masked)

    def _read_exact(self, n):
        out = b""
        while len(out) < n:
            if self._rest:
                take, self._rest = self._rest[:n - len(out)], self._rest[n - len(out):]
                out += take
                continue
            chunk = self.sock.recv(max(1, n - len(out)))
            if not chunk:
                raise WSError("connection closed")
            out += chunk
        return out

    def _read_frame(self):
        b1, b2 = self._read_exact(2)
        opcode = b1 & 0x0F
        length = b2 & 0x7F
        if length == 126:
            length = struct.unpack(">H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", self._read_exact(8))[0]
        masked = b2 & 0x80
        mask = self._read_exact(4) if masked else b""
        payload = self._read_exact(length)
        if masked:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        return opcode, payload

    def call(self, msg_id, method, params=None):
        self._send_text(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        while True:
            opcode, payload = self._read_frame()
            if opcode == 0x8:
                raise WSError("devtools closed the socket")
            if opcode not in (0x1, 0x2):
                continue
            data = json.loads(payload.decode("utf-8", "replace"))
            if data.get("id") == msg_id:
                return data

    def evaluate(self, expression):
        res = self.call(1, "Runtime.evaluate",
                        {"expression": expression, "returnByValue": True, "awaitPromise": True})
        out = res.get("result", {})
        if "exceptionDetails" in out:
            raise WSError(out["exceptionDetails"].get("text", "javascript error"))
        return out.get("result", {}).get("value")

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass

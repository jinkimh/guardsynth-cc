"""Tiny test-only Chromium CDP client using the standard library, no installation."""

import base64
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import time
from urllib.request import Request, urlopen


class Browser:
    def __init__(self, root, url):
        binary = Path.home() / ".cache/ms-playwright/chromium-1243/chrome-linux64/chrome"
        if not binary.exists():
            raise FileNotFoundError("Set up a locally approved Chromium before browser acceptance tests")
        profile = Path(root) / "chromium_profile"
        self.process = subprocess.Popen([str(binary), "--headless", "--no-sandbox", "--disable-dev-shm-usage",
            "--disable-background-networking", "--disable-component-update", "--disable-sync", "--no-first-run",
            "--disable-default-apps", "--remote-debugging-port=0", "--remote-debugging-address=127.0.0.1",
            "--user-data-dir=" + str(profile), "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            end = time.monotonic() + 15
            while not (profile / "DevToolsActivePort").exists():
                if time.monotonic() > end or self.process.poll() is not None:
                    raise RuntimeError("Chromium did not start")
                time.sleep(.05)
            port = int((profile / "DevToolsActivePort").read_text().splitlines()[0])
            with urlopen(Request(f"http://127.0.0.1:{port}/json/new?{url}", method="PUT"), timeout=5) as response:
                target = json.load(response)
            path = target["webSocketDebuggerUrl"].split(f":{port}", 1)[1]
            self.socket = socket.create_connection(("127.0.0.1", port), timeout=15)
            nonce = base64.b64encode(os.urandom(16)).decode()
            self.socket.sendall((f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {nonce}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
            response = b""
            while b"\r\n\r\n" not in response:
                response += self.socket.recv(1)
            if not response.startswith(b"HTTP/1.1 101 "):
                raise RuntimeError("CDP handshake failed")
            self.sequence = 0
            self.call("Runtime.enable")
            self.wait("location.href === " + json.dumps(url) + " && document.readyState === 'complete' && !!document.getElementById('login_form')")
        except BaseException:
            self.process.terminate();self.process.wait(timeout=5)
            raise

    def receive_bytes(self, count):
        result = b""
        while len(result) < count:
            value = self.socket.recv(count - len(result))
            if not value: raise RuntimeError("CDP connection closed")
            result += value
        return result

    def receive(self):
        data = b""
        while True:
            a, b = self.receive_bytes(2)
            size = b & 127
            if size == 126: size = struct.unpack("!H", self.receive_bytes(2))[0]
            elif size == 127: size = struct.unpack("!Q", self.receive_bytes(8))[0]
            mask = self.receive_bytes(4) if b & 128 else None
            chunk = self.receive_bytes(size)
            if mask: chunk = bytes(v ^ mask[i % 4] for i, v in enumerate(chunk))
            if a & 15 == 8: raise RuntimeError("CDP closed")
            data += chunk
            if a & 128: return json.loads(data)

    def call(self, method, params=None):
        self.sequence += 1
        body = json.dumps({"id": self.sequence, "method": method, "params": params or {}}).encode()
        mask = os.urandom(4)
        size = len(body)
        header = bytes([129, 128 | size]) if size < 126 else (bytes([129, 254]) + struct.pack("!H", size) if size < 65536 else bytes([129, 255]) + struct.pack("!Q", size))
        self.socket.sendall(header + mask + bytes(v ^ mask[i % 4] for i, v in enumerate(body)))
        while True:
            response = self.receive()
            if response.get("id") == self.sequence:
                if "error" in response: raise RuntimeError(str(response["error"]))
                return response.get("result", {})

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", {"expression": expression, "awaitPromise": True, "returnByValue": True})
        if "exceptionDetails" in result:
            raise AssertionError(str(result["exceptionDetails"]))
        return result.get("result", {}).get("value")

    def wait(self, expression):
        end = time.monotonic() + 10
        while time.monotonic() < end:
            try:
                if self.evaluate(expression): return
            except AssertionError: pass
            time.sleep(.05)
        raise AssertionError("Browser condition not reached: " + expression)

    def close(self):
        self.socket.close()
        self.process.terminate()
        self.process.wait(timeout=5)

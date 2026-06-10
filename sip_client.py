import subprocess
import threading
import time
import socket
import os
from config import SIP_SERVER, SIP_PORT, MY_USERNAME, MY_PASSWORD


class SIPClient:
    def __init__(self, on_incoming=None, on_call_state=None):
        self.on_incoming   = on_incoming
        self.on_call_state = on_call_state
        self.process       = None
        self._call_active  = False

    def start(self):
        # Baresip-Account sicherstellen
        os.makedirs(os.path.expanduser("~/.baresip"), exist_ok=True)
        acc_file = os.path.expanduser("~/.baresip/accounts")
        with open(acc_file, "w") as f:
            f.write(
                f"<sip:{MY_USERNAME}@{SIP_SERVER};transport=udp>;"
                f"auth_user={MY_USERNAME};auth_pass={MY_PASSWORD};"
                f"regint=60;outbound=\"sip:{SIP_SERVER}:{SIP_PORT}\";\n"
            )

        self.process = subprocess.Popen(
            ["baresip", "-v"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _send(self, command):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(command + "\n")
                self.process.stdin.flush()
            except BrokenPipeError:
                pass

    def _read_loop(self):
        for line in self.process.stdout:
            line = line.strip()
            if not line:
                continue

            lower = line.lower()

            if "incoming call" in lower:
                self._call_active = True
                remote = ""
                if "from" in lower:
                    try:
                        remote = line.split("from")[-1].strip()
                    except Exception:
                        remote = line
                if self.on_incoming:
                    self.on_incoming(None, remote)
                self._send("/accept")

            elif "call established" in lower:
                self._call_active = True
                if self.on_call_state:
                    self.on_call_state("CONFIRMED", "")

            elif "call terminated" in lower or "session closed" in lower:
                if self._call_active:
                    self._call_active = False
                    if self.on_call_state:
                        self.on_call_state("DISCONNECTED", "")

    def call(self, extension):
        if self._call_active:
            return False
        self._send(f"/dial sip:{extension}@{SIP_SERVER}")
        return True

    def hangup(self):
        self._send("/hangup")
        self._call_active = False

    def mute_mic(self, muted):
        self._send("/mute" if muted else "/mute")

    def mute_speaker(self, muted):
        pass

    def conference_add(self, extension):
        self._send(f"/dial sip:{extension}@{SIP_SERVER}")
        time.sleep(1)
        self._send("/conference")

    def stop(self):
        self._send("/quit")
        if self.process:
            try:
                self.process.wait(timeout=3)
            except Exception:
                self.process.kill()

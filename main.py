#!/usr/bin/env python3
import tkinter as tk
import threading
from sip_client import SIPClient
from ui import IntercomApp


def main():
    root = tk.Tk()

    app = IntercomApp(root, sip_client=None)

    sip = SIPClient(
        on_incoming=app.on_incoming_call,
        on_call_state=app.on_call_state,
    )
    app.sip = sip

    threading.Thread(target=sip.start, daemon=True).start()

    try:
        root.mainloop()
    finally:
        sip.stop()


if __name__ == "__main__":
    main()

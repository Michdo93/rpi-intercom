import tkinter as tk
import time
import os
import subprocess
from config import (ROOMS, MY_ROOM_NAME, FULLSCREEN,
                    DEFAULT_VOLUME, DEFAULT_BRIGHTNESS,
                    MY_USERNAME, SIP_SERVER, SIP_PORT)

BG         = "#0d0d1a"
BG2        = "#131328"
BG3        = "#1a1a38"
BG4        = "#1e1e3a"
ACCENT     = "#378ADD"
ACCENT_DIM = "#185FA5"
GREEN      = "#1D9E75"
GREEN_DIM  = "#0d2420"
RED_BG     = "#7a1c1c"
RED_BORDER = "#a02020"
RED_TEXT   = "#ffaaaa"
TEXT       = "#ffffff"
TEXT_DIM   = "#555566"
TEXT_MID   = "#9090b0"

ROOM_ICONS = {
    "Konferenz":  "🏠",
    "Küche":      "🍳",
    "Bad":        "🚿",
    "IoT":        "💡",
    "Multimedia": "🎬",
}

def _icon(room):
    return ROOM_ICONS.get(room, "📞")


class ScrollableFrame(tk.Frame):
    """
    Scrollbarer Container.
    - Mausrad (Button-4/5) scrollt immer.
    - Touch/Maus-Drag: nur wenn die Maus sich >DRAG_THRESHOLD px bewegt hat.
      Andernfalls wird der Klick an das Widget weitergereicht.
    - Button-1 Click-Handler der Kind-Widgets bleiben erhalten durch
      add="+" beim Binden von ButtonPress/Motion und durch den Schwellenwert.
    """

    DRAG_THRESHOLD = 6  # Pixel bis Drag aktiv wird

    def __init__(self, parent, bg=BG, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win  = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self._drag_y    = None
        self._dragging  = False

        self._bind_all(self.inner)

    # ── Scroll-Binding ────────────────────────────────────────
    def _bind_all(self, widget):
        """Mausrad + Drag auf alle Widgets binden, add='+' schützt Button-1."""
        widget.bind("<Button-4>",     self._scroll_up,   add="+")
        widget.bind("<Button-5>",     self._scroll_down, add="+")
        widget.bind("<MouseWheel>",   self._scroll_wheel, add="+")
        widget.bind("<ButtonPress-1>", self._drag_start,  add="+")
        widget.bind("<B1-Motion>",    self._drag_move,   add="+")
        widget.bind("<ButtonRelease-1>", self._drag_end, add="+")
        for child in widget.winfo_children():
            self._bind_all(child)

    def _scroll_up(self, e):
        self.canvas.yview_scroll(-3, "units")

    def _scroll_down(self, e):
        self.canvas.yview_scroll(3, "units")

    def _scroll_wheel(self, e):
        self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")

    def _drag_start(self, e):
        self._drag_y   = e.y_root
        self._dragging = False

    def _drag_move(self, e):
        if self._drag_y is None:
            return
        delta = self._drag_y - e.y_root
        if not self._dragging and abs(delta) > self.DRAG_THRESHOLD:
            self._dragging = True
        if self._dragging:
            self.canvas.yview_scroll(int(delta / 4), "units")
            self._drag_y = e.y_root

    def _drag_end(self, e):
        self._drag_y   = None
        self._dragging = False

    def _on_inner_configure(self, e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.after(80, lambda: self._bind_all(self.inner))

    def _on_canvas_configure(self, e):
        self.canvas.itemconfig(self._win, width=e.width)

    def scroll_top(self):
        self.canvas.yview_moveto(0)


class IntercomApp:
    def __init__(self, root, sip_client):
        self.root = root
        self.sip  = sip_client

        self.root.title("Intercom")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        if FULLSCREEN:
            self.root.attributes("-fullscreen", True)
        else:
            self.root.geometry("320x520")

        self.root.bind("<Escape>",
                       lambda e: self.root.attributes("-fullscreen", False))

        self.call_active     = False
        self.mic_muted       = False
        self.speaker_muted   = False
        self.call_start_time = None
        self.call_target     = ""
        self.conf_added      = set()

        self.frame_idle     = ScrollableFrame(self.root)
        self.frame_call     = ScrollableFrame(self.root)
        self.frame_settings = ScrollableFrame(self.root)

        self._build_idle()
        self._build_call()
        self._build_settings()

        self._show(self.frame_idle)
        self._tick()

    def _show(self, frame):
        for f in (self.frame_idle, self.frame_call, self.frame_settings):
            f.place_forget()
        frame.place(x=0, y=0, relwidth=1, relheight=1)
        frame.scroll_top()

    def _p(self, frame):
        return frame.inner

    def _divider(self, parent, pady=12):
        tk.Frame(parent, bg=BG4, height=1).pack(fill="x", pady=pady)

    def _section_label(self, parent, text, pady=(0, 10)):
        tk.Label(parent, text=text.upper(), bg=BG,
                 fg=TEXT_DIM, font=("", 9)).pack(pady=pady)

    def _card_btn(self, parent, icon, name, ext, cmd):
        outer = tk.Frame(parent, bg=BG4, padx=1, pady=1)
        inner = tk.Frame(outer, bg=BG2)
        inner.pack(fill="both", expand=True)

        lbl_i = tk.Label(inner, text=icon, bg=BG2, fg=TEXT, font=("", 24))
        lbl_i.pack(pady=(18, 6))
        lbl_n = tk.Label(inner, text=name, bg=BG2, fg=TEXT,
                         font=("", 13, "bold"))
        lbl_n.pack()
        lbl_e = tk.Label(inner, text=ext, bg=BG2, fg=ACCENT_DIM,
                         font=("", 10))
        lbl_e.pack(pady=(3, 18))

        def click(e=None):
            # Nur klicken wenn kein Drag aktiv war
            sf = self._find_scrollable(outer)
            if sf and sf._dragging:
                return
            cmd()

        def enter(e=None):
            for w in (inner, lbl_i, lbl_n, lbl_e): w.config(bg=BG3)
        def leave(e=None):
            for w in (inner, lbl_i, lbl_n, lbl_e): w.config(bg=BG2)

        for w in (outer, inner, lbl_i, lbl_n, lbl_e):
            w.bind("<Button-1>", click)
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)

        return outer

    def _action_btn(self, parent, icon, label, bg, fg, border, cmd):
        outer = tk.Frame(parent, bg=border, padx=1, pady=1)
        inner = tk.Frame(outer, bg=bg, cursor="hand2")
        inner.pack(fill="both", expand=True)
        lbl_i = tk.Label(inner, text=icon, bg=bg, fg=fg, font=("", 22))
        lbl_i.pack(pady=(16, 4))
        lbl_l = tk.Label(inner, text=label, bg=bg, fg=fg, font=("", 10))
        lbl_l.pack(pady=(0, 14))

        def click(e=None):
            sf = self._find_scrollable(outer)
            if sf and sf._dragging:
                return
            cmd()

        for w in (outer, inner, lbl_i, lbl_l):
            w.bind("<Button-1>", click)

        return outer, inner, lbl_i, lbl_l

    def _find_scrollable(self, widget):
        """Findet den ScrollableFrame-Vorfahren eines Widgets."""
        w = widget
        while w is not None:
            if isinstance(w, ScrollableFrame):
                return w
            try:
                w = w.master
            except Exception:
                break
        return None

    # ── IDLE ─────────────────────────────────────────────────
    def _build_idle(self):
        p = self._p(self.frame_idle)

        hdr = tk.Frame(p, bg=BG)
        hdr.pack(fill="x", padx=18, pady=(18, 0))
        self.lbl_status = tk.Label(hdr, text="● Verbunden",
                                   bg=BG, fg=GREEN, font=("", 11, "bold"))
        self.lbl_status.pack(side="left")
        self.lbl_clock_idle = tk.Label(hdr, text="",
                                       bg=BG, fg=TEXT_DIM, font=("", 11))
        self.lbl_clock_idle.pack(side="right")

        tk.Label(p, text="Intercom", bg=BG, fg=TEXT,
                 font=("", 28, "bold")).pack(pady=(20, 3))
        tk.Label(p, text=MY_ROOM_NAME, bg=BG, fg=TEXT_DIM,
                 font=("", 12)).pack()

        self._divider(p, pady=16)
        self._section_label(p, "Raum auswählen")

        grid = tk.Frame(p, bg=BG)
        grid.pack(fill="x", padx=14, pady=(0, 4))
        grid.columnconfigure(0, weight=1, uniform="col")
        grid.columnconfigure(1, weight=1, uniform="col")

        self.room_btns = {}
        rooms = [(r, e) for r, e in ROOMS.items() if r != MY_ROOM_NAME]
        for i, (room, ext) in enumerate(rooms):
            row, col = divmod(i, 2)
            btn = self._card_btn(grid, _icon(room), room, ext,
                                 lambda r=room, e=ext: self._start_call(r, e))
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            grid.rowconfigure(row, weight=1, uniform="row")
            self.room_btns[room] = btn

        self._divider(p, pady=16)

        settings_frame = tk.Frame(p, bg=BG, cursor="hand2")
        settings_frame.pack(fill="x")
        settings_lbl = tk.Label(settings_frame, text="⚙   Einstellungen",
                                bg=BG, fg=TEXT_DIM, font=("", 12), pady=14)
        settings_lbl.pack(fill="x")

        def go_settings(e=None):
            sf = self._find_scrollable(settings_frame)
            if sf and sf._dragging:
                return
            self._show(self.frame_settings)

        def s_enter(e=None):
            settings_frame.config(bg=BG2); settings_lbl.config(bg=BG2)
        def s_leave(e=None):
            settings_frame.config(bg=BG); settings_lbl.config(bg=BG)

        for w in (settings_frame, settings_lbl):
            w.bind("<Button-1>", go_settings)
            w.bind("<Enter>", s_enter)
            w.bind("<Leave>", s_leave)

        tk.Frame(p, bg=BG, height=16).pack()

    # ── CALL ─────────────────────────────────────────────────
    def _build_call(self):
        p = self._p(self.frame_call)

        hdr = tk.Frame(p, bg=BG)
        hdr.pack(fill="x", padx=18, pady=(18, 0))
        tk.Label(hdr, text="● Aktiver Anruf",
                 bg=BG, fg=GREEN, font=("", 11, "bold")).pack(side="left")
        self.lbl_clock_call = tk.Label(hdr, text="",
                                       bg=BG, fg=TEXT_DIM, font=("", 11))
        self.lbl_clock_call.pack(side="right")

        cv = tk.Canvas(p, width=90, height=90, bg=BG, highlightthickness=0)
        cv.pack(pady=(28, 0))
        cv.create_oval(2, 2, 88, 88, fill=ACCENT_DIM,
                       outline=ACCENT, width=1)
        self.avatar_txt = cv.create_text(45, 45, text="",
                                         fill=TEXT, font=("", 28, "bold"))
        self.cv_avatar = cv

        self.lbl_call_name = tk.Label(p, text="", bg=BG, fg=TEXT,
                                      font=("", 24, "bold"))
        self.lbl_call_name.pack(pady=(12, 4))

        self.lbl_call_status = tk.Label(p, text="Verbinde…",
                                        bg=BG, fg=TEXT_MID, font=("", 11))
        self.lbl_call_status.pack()

        self.lbl_timer = tk.Label(p, text="00:00", bg=BG, fg=TEXT,
                                  font=("", 40))
        self.lbl_timer.pack(pady=(16, 22))

        btn_row = tk.Frame(p, bg=BG)
        btn_row.pack(fill="x", padx=14, pady=(0, 4))

        mic_outer, mic_inner, mic_i, mic_l = self._action_btn(
            btn_row, "🎙", "Mikro", BG2, TEXT_MID, BG4, self._toggle_mic)
        mic_outer.pack(side="left", fill="both", expand=True, padx=(0, 4))
        self._mic_widgets = (mic_outer, mic_inner, mic_i, mic_l)

        end_outer, _, _, _ = self._action_btn(
            btn_row, "📵", "Auflegen", RED_BG, RED_TEXT, RED_BORDER,
            self._hangup)
        end_outer.pack(side="left", fill="both", expand=True, padx=4)

        spk_outer, spk_inner, spk_i, spk_l = self._action_btn(
            btn_row, "🔊", "Ton", BG2, TEXT_MID, BG4, self._toggle_speaker)
        spk_outer.pack(side="left", fill="both", expand=True, padx=(4, 0))
        self._spk_widgets = (spk_outer, spk_inner, spk_i, spk_l)

        self._divider(p, pady=16)
        self._section_label(p, "Konferenz", pady=(0, 10))

        conf_frame = tk.Frame(p, bg=BG)
        conf_frame.pack(fill="x", padx=14)

        self.conf_btns   = {}
        self.conf_inners = {}

        for room, ext in ROOMS.items():
            if room == MY_ROOM_NAME:
                continue

            outer = tk.Frame(conf_frame, bg=BG4, pady=1, padx=1)
            outer.pack(fill="x", pady=4)
            inner = tk.Frame(outer, bg=BG2, cursor="hand2")
            inner.pack(fill="both")
            lbl = tk.Label(inner,
                           text=f"＋  {_icon(room)}  {room}",
                           bg=BG2, fg=ACCENT,
                           font=("", 12), pady=12, padx=16, anchor="w")
            lbl.pack(fill="x")

            def make_bindings(i, l, r, ex):
                def click(e=None):
                    sf = self._find_scrollable(i)
                    if sf and sf._dragging:
                        return
                    self._add_conference(r, ex)
                def enter(e=None):
                    if r not in self.conf_added:
                        i.config(bg=BG3); l.config(bg=BG3)
                def leave(e=None):
                    if r not in self.conf_added:
                        i.config(bg=BG2); l.config(bg=BG2)
                for w in (i, l):
                    w.bind("<Button-1>", click)
                    w.bind("<Enter>", enter)
                    w.bind("<Leave>", leave)

            make_bindings(inner, lbl, room, ext)
            self.conf_btns[room]   = lbl
            self.conf_inners[room] = inner

        tk.Frame(p, bg=BG, height=20).pack()

    # ── SETTINGS ─────────────────────────────────────────────
    def _build_settings(self):
        p = self._p(self.frame_settings)

        hdr = tk.Frame(p, bg=BG)
        hdr.pack(fill="x", padx=18, pady=(18, 0))
        back = tk.Label(hdr, text="←  Zurück",
                        bg=BG, fg=ACCENT, font=("", 12), cursor="hand2")
        back.pack(side="left")

        def go_back(e=None):
            sf = self._find_scrollable(back)
            if sf and sf._dragging:
                return
            self._show(self.frame_idle)

        back.bind("<Button-1>", go_back)
        back.bind("<Enter>", lambda e: back.config(fg=TEXT))
        back.bind("<Leave>", lambda e: back.config(fg=ACCENT))

        self.lbl_clock_set = tk.Label(hdr, text="",
                                      bg=BG, fg=TEXT_DIM, font=("", 11))
        self.lbl_clock_set.pack(side="right")

        tk.Label(p, text="Einstellungen", bg=BG, fg=TEXT,
                 font=("", 24, "bold")).pack(pady=(24, 24))

        def slider_block(label, default, from_, to, cmd, store):
            block = tk.Frame(p, bg=BG)
            block.pack(fill="x", padx=20, pady=(0, 22))
            top = tk.Frame(block, bg=BG)
            top.pack(fill="x")
            tk.Label(top, text=label, bg=BG, fg=TEXT_MID,
                     font=("", 12)).pack(side="left")
            val_lbl = tk.Label(top, text=f"{default}%", bg=BG, fg=TEXT,
                               font=("", 12, "bold"))
            val_lbl.pack(side="right")
            store.append(val_lbl)
            var = tk.IntVar(value=default)
            tk.Scale(
                block, from_=from_, to=to, orient="horizontal",
                variable=var, bg=BG, fg=TEXT, troughcolor=BG4,
                activebackground=ACCENT,
                highlightthickness=0, bd=0, showvalue=False,
                command=cmd,
            ).pack(fill="x", pady=(10, 0))
            return var

        self._lbl_vol    = []
        self._lbl_bright = []
        self.vol_var    = slider_block("Lautstärke", DEFAULT_VOLUME,
                                       0, 100, self._set_volume,
                                       self._lbl_vol)
        self.bright_var = slider_block("Helligkeit", DEFAULT_BRIGHTNESS,
                                       10, 100, self._set_brightness,
                                       self._lbl_bright)

        self._divider(p, pady=12)
        self._section_label(p, "SIP-Verbindung", pady=(12, 12))

        info = tk.Frame(p, bg=BG2,
                        highlightbackground=BG4, highlightthickness=1)
        info.pack(fill="x", padx=20)

        for i, (label, val) in enumerate([
            ("Benutzer", MY_USERNAME),
            ("Raum",     MY_ROOM_NAME),
            ("Server",   f"{SIP_SERVER}:{SIP_PORT}"),
        ]):
            if i > 0:
                tk.Frame(info, bg=BG4, height=1).pack(fill="x", padx=14)
            row = tk.Frame(info, bg=BG2)
            row.pack(fill="x", padx=16, pady=12)
            tk.Label(row, text=label, bg=BG2, fg=TEXT_DIM,
                     font=("", 11)).pack(side="left")
            tk.Label(row, text=val, bg=BG2, fg=TEXT,
                     font=("", 11, "bold")).pack(side="right")

        tk.Frame(p, bg=BG, height=24).pack()

    # ── Call-Logik ───────────────────────────────────────────
    def _start_call(self, room, ext):
        self.call_target     = room
        self.call_start_time = None
        self.conf_added      = set()
        self.mic_muted       = False
        self.speaker_muted   = False

        self.lbl_call_name.config(text=room)
        self.lbl_call_status.config(text="Verbinde…", fg=TEXT_MID)
        self.lbl_timer.config(text="00:00")

        for widgets, icon, label in (
            (self._mic_widgets, "🎙", "Mikro"),
            (self._spk_widgets, "🔊", "Ton"),
        ):
            _, inner, lbl_i, lbl_l = widgets
            for w in (inner, lbl_i, lbl_l): w.config(bg=BG2)
            lbl_i.config(fg=TEXT_MID, text=icon)
            lbl_l.config(fg=TEXT_MID, text=label)

        initials = "".join(w[0].upper() for w in room.split()[:2])
        self.cv_avatar.itemconfig(self.avatar_txt, text=initials)

        for r, lbl in self.conf_btns.items():
            inn = self.conf_inners[r]
            if r == room:
                lbl.config(text=f"✓  {_icon(r)}  {r}  (aktiv)",
                           fg=GREEN, bg=GREEN_DIM)
                inn.config(bg=GREEN_DIM)
            else:
                lbl.config(text=f"＋  {_icon(r)}  {r}", fg=ACCENT, bg=BG2)
                inn.config(bg=BG2)

        self._show(self.frame_call)
        self.call_active = True
        self.sip.call(ext)

    def on_call_state(self, state_text, remote_uri):
        def _update():
            if "CONFIRMED" in state_text:
                self.lbl_call_status.config(text="Verbunden", fg=GREEN)
                self.call_start_time = time.time()
            elif "DISCONNECTED" in state_text:
                self.call_active     = False
                self.call_start_time = None
                self._show(self.frame_idle)
        self.root.after(0, _update)

    def on_incoming_call(self, call, remote_uri):
        user = ""
        if "sip:" in remote_uri:
            user = remote_uri.split("sip:")[1].split("@")[0]
        room = next(
            (r for r, e in ROOMS.items() if e == user), user or "Unbekannt")

        def _show():
            self.call_active     = True
            self.call_start_time = time.time()
            self.call_target     = room
            self.lbl_call_name.config(text=room)
            self.lbl_call_status.config(text="Eingehend", fg=GREEN)
            initials = "".join(w[0].upper() for w in room.split()[:2])
            self.cv_avatar.itemconfig(self.avatar_txt, text=initials)
            for r, lbl in self.conf_btns.items():
                inn = self.conf_inners[r]
                if r == room:
                    lbl.config(text=f"✓  {_icon(r)}  {r}  (aktiv)",
                               fg=GREEN, bg=GREEN_DIM)
                    inn.config(bg=GREEN_DIM)
                else:
                    lbl.config(text=f"＋  {_icon(r)}  {r}",
                               fg=ACCENT, bg=BG2)
                    inn.config(bg=BG2)
            self._show(self.frame_call)
        self.root.after(0, _show)

    def _hangup(self):
        self.sip.hangup()
        self.call_active     = False
        self.call_start_time = None
        self._show(self.frame_idle)

    def _toggle_mic(self):
        self.mic_muted = not self.mic_muted
        self.sip.mute_mic(self.mic_muted)
        _, inner, lbl_i, lbl_l = self._mic_widgets
        if self.mic_muted:
            for w in (inner, lbl_i, lbl_l): w.config(bg="#3a1010")
            lbl_i.config(fg="#ff6666", text="🔇")
            lbl_l.config(fg="#ff6666", text="Stumm")
        else:
            for w in (inner, lbl_i, lbl_l): w.config(bg=BG2)
            lbl_i.config(fg=TEXT_MID, text="🎙")
            lbl_l.config(fg=TEXT_MID, text="Mikro")

    def _toggle_speaker(self):
        self.speaker_muted = not self.speaker_muted
        self.sip.mute_speaker(self.speaker_muted)
        _, inner, lbl_i, lbl_l = self._spk_widgets
        if self.speaker_muted:
            for w in (inner, lbl_i, lbl_l): w.config(bg="#3a1010")
            lbl_i.config(fg="#ff6666", text="🔈")
            lbl_l.config(fg="#ff6666", text="Stumm")
        else:
            for w in (inner, lbl_i, lbl_l): w.config(bg=BG2)
            lbl_i.config(fg=TEXT_MID, text="🔊")
            lbl_l.config(fg=TEXT_MID, text="Ton")

    def _add_conference(self, room, ext):
        if room in self.conf_added:
            return
        self.conf_added.add(room)
        self.sip.conference_add(ext)
        lbl = self.conf_btns.get(room)
        inn = self.conf_inners.get(room)
        if lbl and inn:
            lbl.config(text=f"✓  {_icon(room)}  {room}",
                       fg=GREEN, bg=GREEN_DIM)
            inn.config(bg=GREEN_DIM)

    def _set_volume(self, val):
        v = int(float(val))
        if self._lbl_vol:
            self._lbl_vol[0].config(text=f"{v}%")
        subprocess.run(["amixer", "sset", "Master", f"{v}%"],
                       capture_output=True)

    def _set_brightness(self, val):
        v = int(float(val))
        if self._lbl_bright:
            self._lbl_bright[0].config(text=f"{v}%")
        backlight = "/sys/class/backlight/rpi_backlight/brightness"
        if os.path.exists(backlight):
            try:
                with open(backlight, "w") as fh:
                    fh.write(str(int(v * 255 / 100)))
                return
            except Exception:
                pass
        try:
            result = subprocess.run(["xrandr"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if " connected" in line:
                    output = line.split()[0]
                    subprocess.run(
                        ["xrandr", "--output", output,
                         "--brightness", str(round(v / 100, 2))],
                        capture_output=True)
                    break
        except Exception:
            pass

    def _tick(self):
        now = time.strftime("%H:%M")
        for lbl in (self.lbl_clock_idle, self.lbl_clock_call,
                    self.lbl_clock_set):
            lbl.config(text=now)
        if self.call_active and self.call_start_time:
            elapsed = int(time.time() - self.call_start_time)
            m, s    = divmod(elapsed, 60)
            self.lbl_timer.config(text=f"{m:02d}:{s:02d}")
        self.root.after(1000, self._tick)
import tkinter as tk
import threading
import time

PALETTE = {
    "bg":        "#0D0D0D",
    "border":    "#1E1E1E",
    "text":      "#F0F0F0",
    "dim":       "#555555",
    "ready":     "#22C55E",
    "listening": "#3B82F6",
    "thinking":  "#F59E0B",
    "speaking":  "#A855F7",
    "error":     "#EF4444",
}

STATUS_COLOR = {
    "ready":     PALETTE["ready"],
    "listening": PALETTE["listening"],
    "thinking":  PALETTE["thinking"],
    "speaking":  PALETTE["speaking"],
}


class PairOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self._status = "initializing"
        self._pulse_on = True
        self._setup_window()
        self._build_ui()
        self._start_pulse()

    def _setup_window(self):
        self.root.title("Pair")
        self.root.overrideredirect(True)          # borderless
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.93)
        self.root.configure(bg=PALETTE["bg"])

        w, h = 230, 76
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{sw - w - 24}+{sh - h - 70}")

        self.root.bind("<Button-1>", self._drag_start)
        self.root.bind("<B1-Motion>", self._drag_move)

    def _build_ui(self):
        outer = tk.Frame(
            self.root, bg=PALETTE["bg"],
            highlightbackground=PALETTE["border"], highlightthickness=1
        )
        outer.pack(fill=tk.BOTH, expand=True)

        # --- Top row ---
        top = tk.Frame(outer, bg=PALETTE["bg"])
        top.pack(fill=tk.X, padx=14, pady=(10, 0))

        self._logo = tk.Label(
            top, text="⬡  Pair", font=("Helvetica Neue", 13, "bold"),
            fg=PALETTE["text"], bg=PALETTE["bg"]
        )
        self._logo.pack(side=tk.LEFT)

        # Status dot canvas
        self._dot_canvas = tk.Canvas(
            top, width=10, height=10, bg=PALETTE["bg"], highlightthickness=0
        )
        self._dot_canvas.pack(side=tk.RIGHT, pady=1)
        self._dot = self._dot_canvas.create_oval(1, 1, 9, 9, fill=PALETTE["ready"], outline="")

        # --- Status text ---
        self._status_label = tk.Label(
            outer, text="ready",
            font=("Helvetica Neue", 10),
            fg=PALETTE["dim"], bg=PALETTE["bg"]
        )
        self._status_label.pack(anchor=tk.W, padx=14, pady=(2, 8))

    def set_status(self, status: str):
        self._status = status
        key = status.split(" ")[0].split(":")[0]
        color = STATUS_COLOR.get(key, PALETTE["dim"])
        label = status if len(status) <= 28 else status[:25] + "..."

        def _update():
            self._dot_canvas.itemconfig(self._dot, fill=color)
            self._status_label.config(text=label, fg=color)

        self.root.after(0, _update)

    def _start_pulse(self):
        def _pulse():
            while True:
                status = self._status
                if status in ("listening", "speaking"):
                    self._pulse_on = not self._pulse_on
                    key = status
                    color = STATUS_COLOR.get(key, PALETTE["dim"]) if self._pulse_on else PALETTE["border"]
                    self.root.after(0, lambda c=color: self._dot_canvas.itemconfig(self._dot, fill=c))
                time.sleep(0.45)

        threading.Thread(target=_pulse, daemon=True).start()

    def _drag_start(self, e):
        self._ox, self._oy = e.x, e.y

    def _drag_move(self, e):
        x = self.root.winfo_x() + e.x - self._ox
        y = self.root.winfo_y() + e.y - self._oy
        self.root.geometry(f"+{x}+{y}")

    def run(self):
        self.root.mainloop()

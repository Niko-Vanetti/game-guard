"""Widgets reutilizables."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from program_guard.ui.theme import get_theme


class AppHeader(ttk.Frame):
    def __init__(self, parent: tk.Misc, subtitle: str = "Control de programas") -> None:
        super().__init__(parent, style="Header.TFrame")
        self.pack(fill="x")
        inner = ttk.Frame(self, style="Header.TFrame", padding=(20, 16))
        inner.pack(fill="x")
        ttk.Label(inner, text="Program Guard", style="Title.TLabel").pack(anchor="w")
        ttk.Label(inner, text=subtitle, style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))


class Card(ttk.Frame):
    def __init__(self, parent: tk.Misc, padding: int = 16, **kwargs) -> None:
        super().__init__(parent, style="Card.TFrame", padding=padding, **kwargs)

    @classmethod
    def wrap(cls, parent: tk.Misc, padding: int = 16) -> tuple[tk.Frame, "Card"]:
        theme = get_theme()
        outer = tk.Frame(parent, bg=theme.border, padx=1, pady=1)
        card = cls(outer, padding=padding)
        card.pack(fill="both", expand=True)
        return outer, card


def primary_button(parent: tk.Misc, text: str, command) -> tk.Button:
    theme = get_theme()
    return tk.Button(
        parent, text=text, command=command, bg=theme.primary, fg="#ffffff",
        activebackground=theme.primary_hover, activeforeground="#ffffff",
        relief="flat", bd=0, padx=18, pady=9, font=(theme.font_family, 10, "bold"),
        cursor="hand2", highlightthickness=0,
    )


def ghost_button(parent: tk.Misc, text: str, command) -> tk.Button:
    theme = get_theme()
    return tk.Button(
        parent, text=text, command=command, bg=theme.surface_alt, fg=theme.text,
        activebackground=theme.border, activeforeground=theme.text,
        relief="flat", bd=0, padx=14, pady=9, font=(theme.font_family, 10),
        cursor="hand2", highlightthickness=0,
    )


class StatusBadge(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, style="Card.TFrame")
        theme = get_theme()
        self._dot = tk.Canvas(self, width=14, height=14, bg=theme.surface, highlightthickness=0)
        self._dot.pack(side="left", padx=(0, 8))
        self._circle = self._dot.create_oval(2, 2, 12, 12, fill=theme.text_muted, outline="")
        self._label = ttk.Label(self, text="—", style="StatusTitle.TLabel")
        self._label.pack(side="left")

    def set_status(self, text: str, color: str) -> None:
        self._dot.itemconfig(self._circle, fill=color)
        self._label.configure(text=text)


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        theme = get_theme()
        self.canvas = tk.Canvas(self, bg=theme.bg, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self._window, width=e.width))

        def on_wheel(event: tk.Event) -> None:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind("<Enter>", lambda _e: self.canvas.bind_all("<MouseWheel>", on_wheel))
        self.canvas.bind("<Leave>", lambda _e: self.canvas.unbind_all("<MouseWheel>"))


def center_window(window: tk.Misc, width: int, height: int) -> None:
    window.update_idletasks()
    x = max(0, (window.winfo_screenwidth() - width) // 2)
    y = max(0, (window.winfo_screenheight() - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def bring_to_front(window: tk.Misc) -> None:
    window.deiconify()
    window.update_idletasks()
    window.lift()
    window.attributes("-topmost", True)
    window.focus_force()
    window.after(400, lambda: window.attributes("-topmost", False))


def show_toast(parent: tk.Misc, message: str, duration_ms: int = 3200, kind: str = "info") -> None:
    theme = get_theme()
    colors = {"info": (theme.primary, "#FFFFFF"), "success": (theme.success, "#FFFFFF"),
              "warning": (theme.warning, "#18181b"), "error": (theme.danger, "#FFFFFF")}
    bg, fg = colors.get(kind, colors["info"])
    toast = tk.Toplevel(parent)
    toast.overrideredirect(True)
    toast.attributes("-topmost", True)
    toast.configure(bg=bg)
    tk.Label(toast, text=message, bg=bg, fg=fg, font=(theme.font_family, 10), padx=16, pady=10).pack()
    toast.update_idletasks()
    toast.geometry(f"+{toast.winfo_screenwidth() - toast.winfo_width() - 24}+{toast.winfo_screenheight() - toast.winfo_height() - 80}")
    toast.after(duration_ms, toast.destroy)

"""Sistema de temas claro/oscuro."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Literal

ThemeMode = Literal["light", "dark"]

VIOLET = {
    "950": "#4c1d95",
    "900": "#581c87",
    "800": "#6d28d9",
    "700": "#7c3aed",
    "600": "#8b5cf6",
    "500": "#a855f7",
    "400": "#a78bfa",
    "300": "#c4b5fd",
    "200": "#ddd6fe",
    "100": "#ede9fe",
    "50": "#f5f3ff",
}


@dataclass(frozen=True)
class Theme:
    mode: ThemeMode
    bg: str
    surface: str
    surface_alt: str
    border: str
    text: str
    text_muted: str
    primary: str
    primary_hover: str
    success: str
    success_bg: str
    danger: str
    danger_bg: str
    warning: str
    warning_bg: str
    accent: str
    header_bg: str
    header_fg: str
    header_subtitle: str
    select_bg: str
    font_family: str = "Segoe UI"
    font_mono: str = "Consolas"


THEMES: dict[ThemeMode, Theme] = {
    "dark": Theme(
        mode="dark",
        bg="#050508",
        surface="#0a0a12",
        surface_alt="#18181b",
        border="#2e1065",
        text="#fafafa",
        text_muted="#a1a1aa",
        primary=VIOLET["700"],
        primary_hover=VIOLET["500"],
        success="#10b981",
        success_bg="#064e3b",
        danger="#ef4444",
        danger_bg="#7f1d1d",
        warning="#fbbf24",
        warning_bg="#78350f",
        accent=VIOLET["300"],
        header_bg="#0a0a0f",
        header_fg="#fafafa",
        header_subtitle=VIOLET["300"],
        select_bg="#312e81",
    ),
    "light": Theme(
        mode="light",
        bg=VIOLET["50"],
        surface="#ffffff",
        surface_alt=VIOLET["100"],
        border=VIOLET["200"],
        text="#18181b",
        text_muted="#71717a",
        primary=VIOLET["700"],
        primary_hover=VIOLET["800"],
        success="#10b981",
        success_bg="#d1fae5",
        danger="#dc2626",
        danger_bg="#fee2e2",
        warning="#d97706",
        warning_bg="#fef3c7",
        accent=VIOLET["600"],
        header_bg=VIOLET["950"],
        header_fg="#fafafa",
        header_subtitle=VIOLET["200"],
        select_bg=VIOLET["100"],
    ),
}

_current: Theme = THEMES["dark"]


def get_theme() -> Theme:
    return _current


def apply_theme(root: tk.Misc, mode: ThemeMode = "dark") -> Theme:
    global _current
    theme = THEMES.get(mode, THEMES["dark"])
    _current = theme

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=theme.bg)

    style.configure(".", background=theme.bg, foreground=theme.text, font=(theme.font_family, 10))
    style.configure("TFrame", background=theme.bg)
    style.configure("Card.TFrame", background=theme.surface)
    style.configure("CardInner.TFrame", background=theme.surface)
    style.configure("Header.TFrame", background=theme.header_bg)
    style.configure("Surface.TFrame", background=theme.surface)

    style.configure("TLabel", background=theme.bg, foreground=theme.text)
    style.configure("Card.TLabel", background=theme.surface, foreground=theme.text)
    style.configure("Muted.TLabel", background=theme.bg, foreground=theme.text_muted, font=(theme.font_family, 9))
    style.configure("CardMuted.TLabel", background=theme.surface, foreground=theme.text_muted, font=(theme.font_family, 9))
    style.configure("Title.TLabel", background=theme.header_bg, foreground=theme.header_fg, font=(theme.font_family, 14, "bold"))
    style.configure(
        "Subtitle.TLabel",
        background=theme.header_bg,
        foreground=theme.header_subtitle,
        font=(theme.font_family, 9),
    )
    style.configure("StatusTitle.TLabel", background=theme.surface, foreground=theme.text, font=(theme.font_family, 13, "bold"))
    style.configure("StatusValue.TLabel", background=theme.surface, foreground=theme.text_muted, font=(theme.font_family, 10))

    style.configure(
        "TButton",
        background=theme.surface_alt,
        foreground=theme.text,
        bordercolor=theme.border,
        focuscolor=theme.primary,
        padding=(12, 6),
    )
    style.map(
        "TButton",
        background=[("active", theme.border), ("disabled", theme.surface_alt)],
        foreground=[("disabled", theme.text_muted)],
    )

    style.configure(
        "Primary.TButton",
        background=theme.primary,
        foreground="#ffffff",
        bordercolor=theme.primary,
        padding=(14, 8),
        font=(theme.font_family, 10, "bold"),
    )
    style.map(
        "Primary.TButton",
        background=[("active", theme.primary_hover), ("disabled", theme.border)],
        foreground=[("active", "#ffffff"), ("!disabled", "#ffffff"), ("disabled", theme.text_muted)],
    )

    style.configure(
        "Danger.TButton",
        background=theme.danger,
        foreground="#ffffff",
        bordercolor=theme.danger,
        padding=(12, 6),
    )
    style.map("Danger.TButton", background=[("active", "#b91c1c")])

    style.configure("TCheckbutton", background=theme.surface, foreground=theme.text)
    style.map("TCheckbutton", background=[("active", theme.surface)])

    style.configure("TLabelframe", background=theme.surface, foreground=theme.text, bordercolor=theme.border)
    style.configure("TLabelframe.Label", background=theme.surface, foreground=theme.text, font=(theme.font_family, 10, "bold"))

    style.configure("TNotebook", background=theme.bg, bordercolor=theme.border, tabmargins=(4, 4, 4, 0))
    style.configure(
        "TNotebook.Tab",
        background=theme.surface_alt,
        foreground=theme.text_muted,
        padding=(16, 8),
        font=(theme.font_family, 10),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", theme.surface), ("active", theme.surface)],
        foreground=[("selected", theme.accent), ("active", theme.text)],
    )

    style.configure(
        "Treeview",
        background=theme.surface,
        foreground=theme.text,
        fieldbackground=theme.surface,
        bordercolor=theme.border,
        rowheight=28,
    )
    style.configure("Treeview.Heading", background=theme.surface_alt, foreground=theme.text, font=(theme.font_family, 9, "bold"))
    style.map("Treeview", background=[("selected", theme.select_bg)], foreground=[("selected", theme.text)])

    style.configure(
        "TEntry",
        fieldbackground=theme.surface_alt if theme.mode == "dark" else theme.surface,
        foreground=theme.text,
        bordercolor=theme.border,
        insertcolor=theme.text,
    )
    style.configure("TScrollbar", background=theme.surface_alt, troughcolor=theme.bg, bordercolor=theme.border)
    style.configure("TSeparator", background=theme.border)
    style.configure("Horizontal.TSeparator", background=theme.border)

    style.configure("TRadiobutton", background=theme.surface, foreground=theme.text)
    style.map("TRadiobutton", background=[("active", theme.surface)])

    return theme

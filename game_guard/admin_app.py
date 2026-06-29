"""Aplicación Admin — control local en red LAN."""

from __future__ import annotations

from game_guard.local_admin_panel import LocalAdminPanel


def run_admin() -> None:
    app = LocalAdminPanel()
    app.mainloop()

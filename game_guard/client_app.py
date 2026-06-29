"""Cliente: bandeja, bloqueo y servidor local en la red."""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

from game_guard.config_manager import ConfigManager
from game_guard.monitor import ProcessMonitor
from game_guard.network import LocalCommandServer, get_local_ip
from game_guard.ui.theme import apply_theme
from game_guard.ui.widgets import bring_to_front, center_window, primary_button, show_toast

logger = logging.getLogger(__name__)


def _create_icon_image(state: str) -> Image.Image:
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    colors = {
        "active": ((124, 58, 237, 255), (109, 40, 217, 255)),
        "paused": ((168, 85, 247, 255), (124, 58, 237, 255)),
        "allowed": ((16, 185, 129, 255), (5, 150, 105, 255)),
        "disabled": ((82, 82, 91, 255), (24, 24, 27, 255)),
    }
    fill, outline = colors.get(state, colors["active"])
    draw.ellipse((4, 4, size - 4, size - 4), fill=outline)
    draw.ellipse((8, 8, size - 8, size - 8), fill=fill)
    draw.polygon([(32, 14), (48, 22), (48, 36), (32, 50), (16, 36), (16, 22)], fill=(255, 255, 255, 230))
    draw.rectangle((28, 24, 36, 40), fill=fill)
    return image


class ClientApplication:
    def __init__(self) -> None:
        self.config = ConfigManager()
        self.root = tk.Tk()
        self.root.withdraw()
        apply_theme(self.root, self.config.theme)

        self.monitor = ProcessMonitor(self.config, on_block=self._on_block)
        self.monitor_thread = threading.Thread(target=self.monitor.start, daemon=True)
        self._icon: Icon | None = None
        self._info_window: tk.Toplevel | None = None

        self.server = LocalCommandServer(
            self.config,
            self.monitor,
            on_change=lambda: self.root.after(0, self._refresh_tray),
            port=self.config.listen_port,
        )
        self.server.start()
        self._start_monitor()
        self._run_tray()

    def _start_monitor(self) -> None:
        self.monitor.interval = self.config.monitor_interval
        if not self.monitor_thread.is_alive():
            self.monitor_thread = threading.Thread(target=self.monitor.start, daemon=True)
            self.monitor_thread.start()

    def _icon_state(self) -> str:
        if not self.config.is_enabled:
            return "disabled"
        if self.config.is_paused():
            return "paused"
        if self.config.is_play_allowed_now():
            return "allowed"
        return "active"

    def _status_text(self) -> str:
        return self.config._status_label()

    def _on_block(self, exe_name: str) -> None:
        logger.info("Juego cerrado: %s", exe_name)
        self.root.after(
            0,
            lambda: show_toast(self.root, f"Juego cerrado: {exe_name}", kind="warning", duration_ms=4000),
        )

    def _show_info(self, _icon=None, _item=None) -> None:
        def show() -> None:
            if self._info_window and self._info_window.winfo_exists():
                bring_to_front(self._info_window)
                return

            from game_guard.ui.theme import get_theme

            theme = get_theme()
            ip = get_local_ip()
            port = self.config.listen_port
            token = self.config.pairing_token

            win = tk.Toplevel(self.root)
            win.title("Game Guard — Cliente")
            win.resizable(False, False)
            win.configure(bg=theme.bg)
            self._info_window = win

            frame = tk.Frame(win, bg=theme.surface, padx=28, pady=24)
            frame.pack(padx=16, pady=16)

            tk.Label(
                frame,
                text="Datos para conectar (red local)",
                bg=theme.surface,
                fg=theme.text,
                font=(theme.font_family, 13, "bold"),
            ).pack(anchor="w")
            tk.Label(
                frame,
                text="Desde el Admin en tu PC usa estos datos.\nSolo funciona en la misma red Wi‑Fi/LAN.",
                bg=theme.surface,
                fg=theme.text_muted,
                font=(theme.font_family, 10),
                justify="left",
            ).pack(anchor="w", pady=(8, 16))

            for label, value in (
                ("IP del cliente", ip),
                ("Puerto", str(port)),
                ("Clave de enlace", token),
            ):
                tk.Label(frame, text=label, bg=theme.surface, fg=theme.text_muted, font=(theme.font_family, 9)).pack(
                    anchor="w", pady=(4, 0)
                )
                tk.Label(
                    frame,
                    text=value,
                    bg=theme.surface,
                    fg=theme.primary,
                    font=(theme.font_family, 16, "bold"),
                ).pack(anchor="w", pady=(0, 8))

            tk.Label(
                frame,
                text="Sin internet ni servidores externos.",
                bg=theme.surface,
                fg=theme.success,
                font=(theme.font_family, 10),
            ).pack(anchor="w", pady=(8, 16))

            primary_button(win, "Cerrar", win.destroy).pack()
            center_window(win, 420, 380)
            bring_to_front(win)
            win.protocol("WM_DELETE_WINDOW", win.destroy)

        self.root.after(0, show)

    def _exit_app(self, _icon=None, _item=None) -> None:
        def do_exit() -> None:
            if messagebox.askyesno("Salir", "¿Cerrar Game Guard Client?"):
                self.server.stop()
                self.monitor.stop()
                if self._icon:
                    self._icon.stop()
                self.root.after(100, self.root.destroy)

        self.root.after(0, do_exit)

    def _refresh_tray(self) -> None:
        if self._icon:
            self._icon.icon = _create_icon_image(self._icon_state())
            self._icon.title = f"Game Guard — {self._status_text()}"

    def _run_tray(self) -> None:
        menu = Menu(
            MenuItem(lambda _: f"Estado: {self._status_text()}", None, enabled=False),
            MenuItem(lambda _: f"IP: {get_local_ip()}", None, enabled=False),
            MenuItem("Ver datos de conexión", self._show_info),
            Menu.SEPARATOR,
            MenuItem("Salir", self._exit_app),
        )
        self._icon = Icon(
            "Game Guard Client",
            _create_icon_image(self._icon_state()),
            f"Game Guard — {get_local_ip()}",
            menu,
        )
        try:
            self._icon.run_detached()
        except Exception:
            logger.exception("Error al iniciar bandeja")
            messagebox.showerror("Game Guard", "No se pudo mostrar el icono en la bandeja.")

    def run(self) -> None:
        self.root.mainloop()

"""Aplicación de bandeja del sistema."""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

from game_guard.admin_panel import AdminPanel, SetupWizard, require_admin_password
from game_guard.config_manager import ConfigManager
from game_guard.monitor import ProcessMonitor

logger = logging.getLogger(__name__)


def _create_icon_image(active: bool) -> Image.Image:
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    color = (46, 125, 50, 255) if active else (198, 40, 40, 255)
    draw.ellipse((8, 8, size - 8, size - 8), fill=color)
    draw.rectangle((28, 20, 36, 44), fill="white")
    return image


class TrayApplication:
    def __init__(self) -> None:
        self.config = ConfigManager()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Game Guard")

        self.monitor = ProcessMonitor(self.config, on_block=self._on_block)
        self.monitor_thread = threading.Thread(target=self.monitor.start, daemon=True)
        self._icon: Icon | None = None
        self._admin_panel: AdminPanel | None = None

        if not self.config.is_setup_complete:
            SetupWizard(self.root, self.config, on_done=self._after_setup)
        else:
            self._start_services()

    def _after_setup(self) -> None:
        messagebox.showinfo(
            "Game Guard",
            "Configuración lista.\n\n"
            "Ahora puedes agregar juegos, definir horarios y activar/desactivar el bloqueo.",
        )
        self._start_services()

    def _start_services(self) -> None:
        if not self.monitor_thread.is_alive():
            self.monitor_thread = threading.Thread(target=self.monitor.start, daemon=True)
            self.monitor_thread.start()
        self._run_tray()

    def _status_text(self) -> str:
        if not self.config.is_enabled:
            return "Desactivado"
        if self.config.is_play_allowed_now():
            return "Horario permitido"
        return "Bloqueando juegos"

    def _on_block(self, exe_name: str) -> None:
        logger.info("Juego cerrado: %s", exe_name)

    def _open_admin(self, _icon=None, _item=None) -> None:
        def open_panel() -> None:
            if not require_admin_password(self.root, self.config):
                return
            if self._admin_panel and self._admin_panel.winfo_exists():
                self._admin_panel.lift()
                self._admin_panel.focus_force()
                return
            self._admin_panel = AdminPanel(
                self.root,
                self.config,
                on_change=self._refresh_tray,
            )

        self.root.after(0, open_panel)

    def _toggle_enabled(self, _icon=None, _item=None) -> None:
        def toggle() -> None:
            if not require_admin_password(self.root, self.config):
                return
            self.config.set_enabled(not self.config.is_enabled)
            self._refresh_tray()
            state = "activado" if self.config.is_enabled else "desactivado"
            messagebox.showinfo("Game Guard", f"Programa {state}.")

        self.root.after(0, toggle)

    def _exit_app(self, _icon=None, _item=None) -> None:
        def do_exit() -> None:
            if not require_admin_password(self.root, self.config):
                return
            if messagebox.askyesno(
                "Salir",
                "¿Cerrar Game Guard?\nMientras esté cerrado, no habrá bloqueo.",
            ):
                self.monitor.stop()
                if self._icon:
                    self._icon.stop()
                self.root.after(100, self.root.destroy)

        self.root.after(0, do_exit)

    def _refresh_tray(self) -> None:
        if self._icon:
            self._icon.icon = _create_icon_image(self.config.is_enabled)
            self._icon.title = f"Game Guard - {self._status_text()}"

    def _run_tray(self) -> None:
        menu = Menu(
            MenuItem(lambda _: f"Estado: {self._status_text()}", None, enabled=False),
            MenuItem("Panel de administrador", self._open_admin),
            MenuItem("Activar / Desactivar", self._toggle_enabled),
            Menu.SEPARATOR,
            MenuItem("Salir (requiere contraseña)", self._exit_app),
        )

        self._icon = Icon(
            "Game Guard",
            _create_icon_image(self.config.is_enabled),
            f"Game Guard - {self._status_text()}",
            menu,
        )

        threading.Thread(target=self._icon.run, daemon=True).start()

    def run(self) -> None:
        self.root.mainloop()

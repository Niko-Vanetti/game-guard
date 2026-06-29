"""Cliente Program Guard — segundo plano + enlace por código."""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

from program_guard.config_manager import ConfigManager
from program_guard.hub import HubService
from program_guard.monitor import ProcessMonitor
from program_guard.ui.theme import apply_theme, get_theme
from program_guard.ui.widgets import bring_to_front, center_window, ghost_button, primary_button, show_toast
from program_guard.usage_tracker import UsageTracker

logger = logging.getLogger(__name__)


def _icon(state: str) -> Image.Image:
    colors = {
        "active": ((124, 58, 237, 255), (109, 40, 217, 255)),
        "paused": ((168, 85, 247, 255), (124, 58, 237, 255)),
        "allowed": ((16, 185, 129, 255), (5, 150, 105, 255)),
        "disabled": ((82, 82, 91, 255), (24, 24, 27, 255)),
        "waiting": ((113, 113, 122, 255), (63, 63, 70, 255)),
    }
    fill, outline = colors.get(state, colors["active"])
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill=outline)
    d.ellipse((8, 8, 56, 56), fill=fill)
    return img


class ClientApplication:
    def __init__(self) -> None:
        self.config = ConfigManager()
        self.root = tk.Tk()
        self.root.withdraw()
        apply_theme(self.root, self.config.theme)

        self.hub = HubService()

        self.usage = UsageTracker()
        self.monitor = ProcessMonitor(self.config, on_block=self._on_block)
        threading.Thread(target=self.monitor.start, daemon=True).start()

        self._icon: Icon | None = None
        self._link_win: tk.Toplevel | None = None
        self._sync = True
        self._sync_thread_started = False
        self._room_code = self.config.active_room_code

        self._run_tray()
        if self._room_code:
            if self.hub.connect_to_saved(self._room_code):
                self._ensure_sync()
            else:
                self.config.clear_active_room()
                self._room_code = ""
                self.root.after(400, self._show_link_dialog)
        else:
            self.root.after(400, self._show_link_dialog)

    def _ensure_sync(self) -> None:
        if self._sync_thread_started or not self._room_code:
            return
        self._sync_thread_started = True
        threading.Thread(target=self._sync_loop, daemon=True).start()

    def _sync_loop(self) -> None:
        while self._sync and self._room_code:
            try:
                self._sync_once()
            except Exception:
                logger.exception("Sync error")
            threading.Event().wait(5.0)

    def _sync_once(self) -> None:
        room = self.hub.get_room(self._room_code)
        if not room:
            return
        if room.get("disconnect_by_admin"):
            self._room_code = ""
            self._sync_thread_started = False
            self.config.clear_active_room()
            self.root.after(0, self._on_admin_disconnect)
            return

        tagged = set(room.get("config", {}).get("tagged_games") or self.config.tagged_games)
        running = self.usage.scan_running(tagged)
        programs = self.usage.programs_last_7_days(tagged)

        remote_cfg = room.get("config")
        if isinstance(remote_cfg, dict) and remote_cfg != self.config.to_remote_config():
            self.config.apply_remote_config(remote_cfg)
            self.root.after(0, self._refresh_tray)

        cmd = room.get("command")
        if isinstance(cmd, dict) and cmd.get("type"):
            self._handle(cmd)
            self.hub.clear_command(self._room_code)

        self.hub.push_telemetry(
            self._room_code,
            {
                "status": self.config.status_snapshot(),
                "running_now": running,
                "programs_7d": programs,
            },
        )

    def _on_admin_disconnect(self) -> None:
        self._refresh_tray()
        show_toast(self.root, "Admin desconectado", kind="info")

    def _handle(self, cmd: dict) -> None:
        t = cmd.get("type")
        if t == "set_enabled":
            self.config.set_enabled(bool(cmd.get("enabled", True)))
        elif t == "pause":
            self.config.pause_for_minutes(int(cmd.get("minutes", 30)))
        elif t == "clear_pause":
            self.config.clear_pause()
        elif t == "update_config":
            if isinstance(cmd.get("config"), dict):
                self.config.apply_remote_config(cmd["config"])
        elif t == "kill_games":
            self.monitor.kill_blocked_now()
        self.root.after(0, self._refresh_tray)

    def _on_block(self, exe: str) -> None:
        self.root.after(0, lambda: show_toast(self.root, f"Cerrado: {exe}", kind="warning"))

    def _go_background(self, message: str = "") -> None:
        if self._link_win and self._link_win.winfo_exists():
            self._link_win.withdraw()
        self.root.withdraw()
        self._refresh_tray()
        if message:
            show_toast(self.root, message, kind="info")

    def _show_link_dialog(self, _i=None, _m=None) -> None:
        def show() -> None:
            if self._link_win and self._link_win.winfo_exists():
                self._link_win.deiconify()
                bring_to_front(self._link_win)
                return

            theme = get_theme()
            win = tk.Toplevel(self.root)
            win.title("Enlazar con Admin")
            win.configure(bg=theme.bg)
            self._link_win = win
            win.protocol("WM_DELETE_WINDOW", lambda: self._go_background("Program Guard en segundo plano"))

            body = tk.Frame(win, bg=theme.bg, padx=28, pady=24)
            body.pack(fill="both", expand=True)

            tk.Label(body, text="Conectar", bg=theme.bg, fg=theme.text, font=(theme.font_family, 16, "bold")).pack(anchor="w")
            tk.Label(
                body,
                text="Genera un código y díselo al Admin, o ingresa el código que te dio.",
                bg=theme.bg,
                fg=theme.text_muted,
                wraplength=360,
            ).pack(anchor="w", pady=(8, 12))

            tk.Label(
                body,
                text="Después de conectar, la app queda solo en la bandeja ↓",
                bg=theme.bg,
                fg=theme.text_muted,
                font=(theme.font_family, 8),
                wraplength=360,
            ).pack(anchor="w", pady=(0, 16))

            code_var = tk.StringVar(value=self._room_code or "")
            tk.Label(body, textvariable=code_var, bg=theme.bg, fg=theme.primary, font=(theme.font_family, 36, "bold")).pack(pady=(0, 16))

            entry = ttk.Entry(body, width=10, font=(theme.font_family, 20), justify="center")

            def generate() -> None:
                code = self.hub.create_room("client", self.config.device_id, self.config.device_name)
                code_var.set(code)
                self._room_code = code
                self.config.set_active_link(code)
                entry.delete(0, tk.END)
                self._ensure_sync()
                self._go_background(f"Código {code} — en bandeja, esperando Admin")

            def join() -> None:
                code = entry.get().strip()
                if len(code) != 6 or not code.isdigit():
                    messagebox.showerror("Error", "Ingresa un código de 6 dígitos")
                    return
                room = self.hub.join_room(code, "client")
                if not room:
                    messagebox.showerror("Error", "Código no encontrado. Verifica e intenta de nuevo.")
                    return
                self._room_code = code
                self.config.set_active_link(code)
                self._ensure_sync()
                self._go_background("Conectado — Program Guard en segundo plano")

            primary_button(body, "Generar código", generate).pack(anchor="w", pady=(0, 16))
            ttk.Label(body, text="O ingresa el código del Admin:").pack(anchor="w")
            entry.pack(pady=8)
            primary_button(body, "Conectar", join).pack(anchor="w", pady=(4, 0))
            ghost_button(body, "Minimizar a bandeja", lambda: self._go_background("En segundo plano")).pack(anchor="w", pady=(16, 0))
            center_window(win, 400, 380)
            bring_to_front(win)

        self.root.after(0, show)

    def _state(self) -> str:
        if not self._room_code:
            return "waiting"
        if not self.config.is_enabled:
            return "disabled"
        if self.config.is_paused():
            return "paused"
        if self.config.is_play_allowed_now():
            return "allowed"
        return "active"

    def _status(self) -> str:
        if not self._room_code:
            return "Sin enlace"
        return self.config._status_label()

    def _refresh_tray(self) -> None:
        if self._icon:
            self._icon.icon = _icon(self._state())
            self._icon.title = f"Program Guard — {self._status()}"

    def _exit(self, *_a) -> None:
        def go() -> None:
            if messagebox.askyesno("Salir", "¿Cerrar Program Guard?"):
                self._sync = False
                self.monitor.stop()
                self.usage.close()
                if self._icon:
                    self._icon.stop()
                self.root.destroy()

        self.root.after(0, go)

    def _run_tray(self) -> None:
        menu = Menu(
            MenuItem(lambda _: f"Estado: {self._status()}", None, enabled=False),
            MenuItem(lambda _: f"Código: {self._room_code or '—'}", None, enabled=False),
            MenuItem("Conectar / Ver código", self._show_link_dialog),
            Menu.SEPARATOR,
            MenuItem("Salir", self._exit),
        )
        self._icon = Icon("Program Guard", _icon(self._state()), "Program Guard", menu)
        self._icon.run_detached()

    def run(self) -> None:
        self.root.mainloop()

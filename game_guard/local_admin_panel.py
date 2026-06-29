"""Panel Admin — controla clientes en la red local (sin servidor externo)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from game_guard.config_manager import DAYS, SCHEDULE_PRESETS
from game_guard.network.local_client import AdminConnection
from game_guard.network.local_server import DEFAULT_PORT
from game_guard.ui.theme import apply_theme, get_theme
from game_guard.ui.widgets import (
    AppHeader,
    Card,
    ScrollableFrame,
    StatusBadge,
    center_window,
    ghost_button,
    primary_button,
    show_toast,
)


class LocalAdminPanel(tk.Tk):
    PRESET_LABELS = {
        "weekend_only": "Solo fin de semana",
        "evenings": "Tardes (vie–dom)",
        "school_days": "Viernes y sábado",
    }

    def __init__(self) -> None:
        super().__init__()
        self.conn: AdminConnection | None = None
        self.device_data: dict = {}
        self._remote_config: dict = {}
        self._connected = False

        self.title("Game Guard — Admin")
        self.geometry("740x600")
        self.minsize(660, 520)
        apply_theme(self, "dark")
        self._build_connect_screen()
        center_window(self, 740, 600)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        if self.conn:
            self.conn.close()
        self.destroy()

    def _build_connect_screen(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()
        self._connected = False

        theme = get_theme()
        self.configure(bg=theme.bg)
        AppHeader(self, subtitle="Control en red local — sin internet")

        body = tk.Frame(self, bg=theme.bg)
        body.pack(fill="both", expand=True, padx=24, pady=20)

        outer, card = Card.wrap(body, padding=32)
        outer.pack(fill="both", expand=True)

        ttk.Label(card, text="Conectar al Cliente", style="StatusTitle.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text=(
                "En el PC cliente abre «Ver datos de conexión» en la bandeja "
                "y copia IP, puerto y clave. Ambos deben estar en la misma red."
            ),
            style="CardMuted.TLabel",
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(8, 20))

        ttk.Label(card, text="IP del cliente", style="Card.TLabel").pack(anchor="w")
        self.ip_entry = ttk.Entry(card, width=24, font=(theme.font_family, 12))
        self.ip_entry.pack(anchor="w", pady=(4, 12))
        self.ip_entry.insert(0, "192.168.")

        ttk.Label(card, text="Puerto", style="Card.TLabel").pack(anchor="w")
        self.port_entry = ttk.Entry(card, width=10, font=(theme.font_family, 12))
        self.port_entry.pack(anchor="w", pady=(4, 12))
        self.port_entry.insert(0, str(DEFAULT_PORT))

        ttk.Label(card, text="Clave de enlace", style="Card.TLabel").pack(anchor="w")
        self.token_entry = ttk.Entry(card, width=16, font=(theme.font_family, 12))
        self.token_entry.pack(anchor="w", pady=(4, 20))

        primary_button(card, "Conectar", self._connect).pack(anchor="w")

    def _connect(self) -> None:
        host = self.ip_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Puerto inválido.")
            return
        token = self.token_entry.get().strip()
        if not host or not token:
            messagebox.showerror("Error", "Completa IP y clave de enlace.")
            return

        conn = AdminConnection(host, port, token)
        try:
            conn.connect()
        except (ConnectionError, OSError) as exc:
            messagebox.showerror(
                "Sin conexión",
                f"No se pudo conectar a {host}:{port}.\n\n"
                f"Verifica IP, clave, firewall y que el Cliente esté abierto.\n\n{exc}",
            )
            return

        if self.conn:
            self.conn.close()
        self.conn = conn
        self._connected = True
        self._build_dashboard()
        show_toast(self, f"Conectado a {conn.device_name}", kind="success")

    def _safe_command(self, payload: dict) -> dict | None:
        if not self.conn:
            return None
        try:
            return self.conn.command(payload)
        except (ConnectionError, OSError) as exc:
            messagebox.showerror("Conexión perdida", str(exc))
            self._build_connect_screen()
            return None

    def _refresh_device(self) -> bool:
        if not self.conn:
            return False
        try:
            data = self.conn.get_status()
        except (ConnectionError, OSError):
            self._build_connect_screen()
            return False
        if data.get("type") != "status":
            return False
        self.device_data = data
        if isinstance(data.get("config"), dict):
            self._remote_config = dict(data["config"])
        return True

    def _build_dashboard(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()

        name = self.conn.device_name if self.conn else "Cliente"
        AppHeader(self, subtitle=f"Conectado: {name}")

        top = ttk.Frame(self, padding=(16, 8))
        top.pack(fill="x")
        ghost_button(top, "← Desconectar", self._build_connect_screen).pack(side="left")
        primary_button(top, "Actualizar", self._manual_refresh).pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.status_tab = ttk.Frame(notebook, padding=4)
        self.apps_tab = ttk.Frame(notebook, padding=4)
        self.schedule_tab = ttk.Frame(notebook, padding=4)
        notebook.add(self.status_tab, text="  Estado  ")
        notebook.add(self.apps_tab, text="  Juegos  ")
        notebook.add(self.schedule_tab, text="  Horarios  ")

        self._build_status_tab()
        self._build_apps_tab()
        self._build_schedule_tab()
        self._manual_refresh()
        self.after(5000, self._auto_refresh)

    def _manual_refresh(self) -> None:
        if self._refresh_device():
            self._update_status_ui()
            self._refresh_apps_tree()
            if hasattr(self, "schedule_vars"):
                self._load_schedule_from_remote()

    def _auto_refresh(self) -> None:
        if not self.winfo_exists() or not self._connected:
            return
        self._manual_refresh()
        self.after(5000, self._auto_refresh)

    def _build_status_tab(self) -> None:
        outer, card = Card.wrap(self.status_tab, padding=20)
        outer.pack(fill="both", expand=True, pady=4)

        self.status_badge = StatusBadge(card)
        self.status_badge.pack(anchor="w", pady=(0, 8))
        self.detail_label = ttk.Label(card, text="", style="StatusValue.TLabel", wraplength=560)
        self.detail_label.pack(anchor="w", pady=(0, 16))

        ttk.Separator(card, orient="horizontal").pack(fill="x", pady=(0, 16))

        row = ttk.Frame(card, style="Card.TFrame")
        row.pack(fill="x", pady=4)
        primary_button(row, "Activar bloqueo", lambda: self._cmd_set_enabled(True)).pack(side="left", padx=(0, 8))
        ghost_button(row, "Desactivar bloqueo", lambda: self._cmd_set_enabled(False)).pack(side="left", padx=(0, 8))
        primary_button(row, "Cerrar juegos ahora", self._cmd_kill_games).pack(side="left")

        pause_row = ttk.Frame(card, style="Card.TFrame")
        pause_row.pack(fill="x", pady=(16, 0))
        ttk.Label(pause_row, text="Pausa temporal", style="Card.TLabel").pack(anchor="w", pady=(0, 8))
        btn_row = ttk.Frame(pause_row, style="Card.TFrame")
        btn_row.pack(anchor="w")
        for mins, label in ((30, "30 min"), (60, "1 hora"), (120, "2 horas")):
            ghost_button(btn_row, label, lambda m=mins: self._cmd_pause(m)).pack(side="left", padx=(0, 8))
        ghost_button(btn_row, "Cancelar pausa", self._cmd_clear_pause).pack(side="left")

    def _build_apps_tab(self) -> None:
        outer, card = Card.wrap(self.apps_tab, padding=16)
        outer.pack(fill="both", expand=True, pady=4)

        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill="x", pady=(0, 12))
        primary_button(top, "+ Agregar juego", self._add_game).pack(side="left", padx=(0, 8))
        ghost_button(top, "Quitar seleccionados", self._remove_games).pack(side="left")

        ttk.Label(
            card,
            text="Nombre del .exe en el PC cliente (ej: RobloxPlayerBeta.exe).",
            style="CardMuted.TLabel",
            wraplength=560,
        ).pack(anchor="w", pady=(0, 8))

        tree_frame = ttk.Frame(card, style="Card.TFrame")
        tree_frame.pack(fill="both", expand=True)
        self.apps_tree = ttk.Treeview(tree_frame, columns=("name", "exe"), show="headings", height=12)
        self.apps_tree.heading("name", text="Nombre")
        self.apps_tree.heading("exe", text="Ejecutable")
        self.apps_tree.column("name", width=200)
        self.apps_tree.column("exe", width=220)
        self.apps_tree.pack(fill="both", expand=True)

    def _build_schedule_tab(self) -> None:
        preset_outer, preset_card = Card.wrap(self.schedule_tab, padding=12)
        preset_outer.pack(fill="x", pady=(4, 8))
        ttk.Label(preset_card, text="Plantillas", style="StatusTitle.TLabel").pack(anchor="w")
        preset_row = ttk.Frame(preset_card, style="Card.TFrame")
        preset_row.pack(anchor="w", pady=(8, 0))
        for preset_id, label in self.PRESET_LABELS.items():
            ghost_button(preset_row, label, lambda pid=preset_id: self._apply_preset(pid)).pack(
                side="left", padx=(0, 8)
            )

        scroll = ScrollableFrame(self.schedule_tab)
        scroll.pack(fill="both", expand=True, pady=4)
        self.schedule_vars: dict[str, dict[str, tk.Variable]] = {}
        for day_id, day_label in DAYS:
            day_outer, row = Card.wrap(scroll.inner, padding=10)
            day_outer.pack(fill="x", pady=3)
            ttk.Label(row, text=day_label, style="StatusTitle.TLabel").pack(anchor="w", pady=(0, 6))
            controls = ttk.Frame(row, style="Card.TFrame")
            controls.pack(fill="x")
            enabled = tk.BooleanVar()
            all_day = tk.BooleanVar()
            start = tk.StringVar(value="18:00")
            end = tk.StringVar(value="22:00")
            self.schedule_vars[day_id] = {"enabled": enabled, "all_day": all_day, "start": start, "end": end}
            ttk.Checkbutton(controls, text="Permitir jugar", variable=enabled).grid(row=0, column=0, sticky="w")
            ttk.Checkbutton(controls, text="Todo el día", variable=all_day).grid(row=0, column=1, sticky="w", padx=(16, 0))
            ttk.Label(controls, text="Desde").grid(row=1, column=0, sticky="w", pady=(8, 0))
            ttk.Entry(controls, textvariable=start, width=8).grid(row=1, column=1, sticky="w", pady=(8, 0))
            ttk.Label(controls, text="Hasta").grid(row=1, column=2, sticky="w", padx=(12, 0), pady=(8, 0))
            ttk.Entry(controls, textvariable=end, width=8).grid(row=1, column=3, sticky="w", pady=(8, 0))

        save_row = ttk.Frame(self.schedule_tab)
        save_row.pack(fill="x", pady=(8, 4))
        primary_button(save_row, "Guardar horarios", self._save_schedule).pack(side="right")

    def _update_status_ui(self) -> None:
        theme = get_theme()
        status = self.device_data.get("status") or {}
        label = status.get("status_text", "—")
        if status.get("paused"):
            color = theme.primary_hover
        elif status.get("play_allowed"):
            color = theme.success
        elif status.get("enabled"):
            color = theme.primary
        else:
            color = theme.text_muted

        self.status_badge.set_status(label, color)
        name = self.device_data.get("name", "Cliente")
        self.detail_label.configure(
            text=f"{name} · {status.get('blocked_count', 0)} juegos · Red local"
        )

    def _refresh_apps_tree(self) -> None:
        for item in self.apps_tree.get_children():
            self.apps_tree.delete(item)
        for app in self._remote_config.get("blocked_apps", []):
            self.apps_tree.insert("", "end", values=(app.get("name", ""), app.get("exe_name", "")))

    def _load_schedule_from_remote(self) -> None:
        schedule = self._remote_config.get("schedule") or {}
        for day_id, vars_map in self.schedule_vars.items():
            day_cfg = schedule.get(day_id, {})
            vars_map["enabled"].set(day_cfg.get("enabled", False))
            vars_map["all_day"].set(day_cfg.get("all_day", False))
            vars_map["start"].set(day_cfg.get("start", "18:00"))
            vars_map["end"].set(day_cfg.get("end", "22:00"))

    def _push_config(self) -> None:
        resp = self._safe_command({"type": "update_config", "config": self._remote_config})
        if resp and resp.get("type") == "ok":
            show_toast(self, "Configuración enviada", kind="success")

    def _cmd_set_enabled(self, enabled: bool) -> None:
        if self._safe_command({"type": "set_enabled", "enabled": enabled}):
            show_toast(self, "Comando enviado", kind="info")
            self._manual_refresh()

    def _cmd_pause(self, minutes: int) -> None:
        if self._safe_command({"type": "pause", "minutes": minutes}):
            show_toast(self, f"Pausa de {minutes} min", kind="info")
            self._manual_refresh()

    def _cmd_clear_pause(self) -> None:
        if self._safe_command({"type": "clear_pause"}):
            show_toast(self, "Pausa cancelada", kind="info")
            self._manual_refresh()

    def _cmd_kill_games(self) -> None:
        if self._safe_command({"type": "kill_games"}):
            show_toast(self, "Juegos cerrados", kind="warning")

    def _add_game(self) -> None:
        name = simpledialog.askstring("Agregar juego", "Nombre:", parent=self)
        if not name:
            return
        exe = simpledialog.askstring("Agregar juego", "Archivo .exe:", parent=self)
        if not exe:
            return
        exe = exe.strip().lower()
        if not exe.endswith(".exe"):
            exe += ".exe"
        apps = list(self._remote_config.get("blocked_apps", []))
        if any(a.get("exe_name") == exe for a in apps):
            messagebox.showwarning("Aviso", "Ese juego ya está en la lista.")
            return
        apps.append({"name": name.strip(), "exe_name": exe, "exe_path": ""})
        self._remote_config["blocked_apps"] = apps
        self._push_config()
        self._refresh_apps_tree()

    def _remove_games(self) -> None:
        selection = self.apps_tree.selection()
        if not selection:
            return
        exes = {self.apps_tree.item(i, "values")[1] for i in selection}
        apps = [a for a in self._remote_config.get("blocked_apps", []) if a.get("exe_name") not in exes]
        self._remote_config["blocked_apps"] = apps
        self._push_config()
        self._refresh_apps_tree()

    def _apply_preset(self, preset_id: str) -> None:
        preset = SCHEDULE_PRESETS.get(preset_id)
        if not preset:
            return
        self._remote_config["schedule"] = preset
        self._load_schedule_from_remote()
        show_toast(self, "Plantilla aplicada — pulsa Guardar", kind="info")

    def _save_schedule(self) -> None:
        schedule = {}
        for day_id, vars_map in self.schedule_vars.items():
            schedule[day_id] = {
                "enabled": bool(vars_map["enabled"].get()),
                "all_day": bool(vars_map["all_day"].get()),
                "start": vars_map["start"].get().strip(),
                "end": vars_map["end"].get().strip(),
            }
        self._remote_config["schedule"] = schedule
        self._push_config()

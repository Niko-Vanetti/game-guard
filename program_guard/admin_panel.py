"""Admin Program Guard — control remoto por código."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from program_guard.hub import HubService
from program_guard.ui.theme import apply_theme, get_theme
from program_guard.ui.widgets import (
    AppHeader,
    Card,
    StatusBadge,
    center_window,
    ghost_button,
    primary_button,
    show_toast,
)


class AdminPanel(tk.Tk):
    def __init__(self, hub: HubService) -> None:
        super().__init__()
        self.hub = hub
        self.room_code = ""
        self.room: dict = {}
        self._config: dict = {}
        self.title("Program Guard — Admin")
        self.geometry("800x640")
        apply_theme(self, "dark")
        self._connect_screen()
        center_window(self, 800, 640)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        if self.room_code:
            self.hub.disconnect_admin(self.room_code)
        self.destroy()

    def _connect_screen(self) -> None:
        for w in self.winfo_children():
            w.destroy()
        self.room_code = ""
        theme = get_theme()
        AppHeader(self, subtitle="Ingresa el código para conectar")
        body = tk.Frame(self, bg=theme.bg)
        body.pack(fill="both", expand=True, padx=24, pady=16)
        outer, card = Card.wrap(body, padding=28)
        outer.pack(fill="both", expand=True)

        ttk.Label(card, text="Conectar con Cliente", style="StatusTitle.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text="Genera un código o ingresa el que te dio el Cliente. La conexión se hace sola.",
            style="CardMuted.TLabel",
            wraplength=520,
        ).pack(anchor="w", pady=(8, 20))

        self._code_display = tk.StringVar()
        tk.Label(
            card,
            textvariable=self._code_display,
            bg=get_theme().surface,
            fg=get_theme().primary,
            font=("Segoe UI", 36, "bold"),
        ).pack(pady=(0, 20))

        ttk.Label(card, text="Código del Cliente:", style="CardMuted.TLabel").pack(anchor="w")
        self._code_entry = ttk.Entry(card, width=10, font=("Segoe UI", 20), justify="center")
        self._code_entry.pack(pady=8)

        row = ttk.Frame(card, style="Card.TFrame")
        row.pack(anchor="w", pady=12)
        primary_button(row, "Generar código", self._generate).pack(side="left", padx=(0, 8))
        primary_button(row, "Conectar", self._join).pack(side="left")

    def _generate(self) -> None:
        code = self.hub.create_room("admin")
        self._code_display.set(code)
        self.room_code = code
        show_toast(self, f"Código {code} — díselo al Cliente", kind="info")
        self.after(2000, self._wait_client)

    def _wait_client(self) -> None:
        if not self.room_code:
            return
        room = self.hub.get_room(self.room_code)
        if room and room.get("linked") and room.get("client_telemetry"):
            self._open_dashboard()
            return
        self.after(2000, self._wait_client)

    def _join(self) -> None:
        code = self._code_entry.get().strip()
        if len(code) != 6 or not code.isdigit():
            messagebox.showerror("Error", "Ingresa un código de 6 dígitos")
            return
        room = self.hub.join_room(code, "admin")
        if not room:
            messagebox.showerror("Error", "Código no encontrado. Verifica e intenta de nuevo.")
            return
        self.room_code = code
        self._open_dashboard()

    def _open_dashboard(self) -> None:
        for w in self.winfo_children():
            w.destroy()
        AppHeader(self, subtitle=f"Cliente · código {self.room_code}")
        top = ttk.Frame(self, padding=(12, 6))
        top.pack(fill="x")
        ghost_button(top, "← Cambiar conexión", self._connect_screen).pack(side="left")
        primary_button(top, "Actualizar", self._refresh).pack(side="right", padx=(0, 8))
        primary_button(top, "Desconectar Cliente", self._disconnect).pack(side="right")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self._tab_status = ttk.Frame(nb, padding=4)
        self._tab_programs = ttk.Frame(nb, padding=4)
        self._tab_blocked = ttk.Frame(nb, padding=4)
        nb.add(self._tab_status, text="  Estado  ")
        nb.add(self._tab_programs, text="  Programas (7 días)  ")
        nb.add(self._tab_blocked, text="  Bloqueados  ")

        self._build_status()
        self._build_programs()
        self._build_blocked()
        self._refresh()
        self.after(5000, self._auto_refresh)

    def _build_status(self) -> None:
        outer, card = Card.wrap(self._tab_status, padding=16)
        outer.pack(fill="both", expand=True)
        self._badge = StatusBadge(card)
        self._badge.pack(anchor="w")
        self._detail = ttk.Label(card, text="", style="StatusValue.TLabel", wraplength=600)
        self._detail.pack(anchor="w", pady=12)
        ttk.Label(card, text="En ejecución ahora", style="CardMuted.TLabel").pack(anchor="w", pady=(8, 4))
        self._running_tree = ttk.Treeview(card, columns=("tipo", "exe"), show="headings", height=6)
        self._running_tree.heading("tipo", text="Tipo")
        self._running_tree.heading("exe", text="Programa")
        self._running_tree.column("tipo", width=90)
        self._running_tree.column("exe", width=320)
        self._running_tree.pack(fill="x", pady=(0, 12))
        row = ttk.Frame(card, style="Card.TFrame")
        row.pack(anchor="w", pady=8)
        primary_button(row, "Activar bloqueo", lambda: self._cmd({"type": "set_enabled", "enabled": True})).pack(side="left", padx=(0, 8))
        ghost_button(row, "Desactivar", lambda: self._cmd({"type": "set_enabled", "enabled": False})).pack(side="left", padx=(0, 8))
        primary_button(row, "Cerrar programas ahora", lambda: self._cmd({"type": "kill_games"})).pack(side="left")

    def _build_programs(self) -> None:
        outer, card = Card.wrap(self._tab_programs, padding=12)
        outer.pack(fill="both", expand=True)
        ttk.Label(card, text="Uso últimos 7 días", style="CardMuted.TLabel").pack(anchor="w", pady=(0, 8))
        self._prog_tree = ttk.Treeview(card, columns=("cat", "exe", "min", "sess", "freq"), show="headings", height=14)
        for col, txt, w in [("cat", "Tipo", 80), ("exe", "Programa", 220), ("min", "Minutos", 70), ("sess", "Sesiones", 70), ("freq", "Frecuente", 70)]:
            self._prog_tree.heading(col, text=txt)
            self._prog_tree.column(col, width=w)
        self._prog_tree.pack(fill="both", expand=True)
        primary_button(card, "Bloquear seleccionados", self._block_selected).pack(anchor="e", pady=(8, 0))

    def _build_blocked(self) -> None:
        outer, card = Card.wrap(self._tab_blocked, padding=12)
        outer.pack(fill="both", expand=True)
        self._block_tree = ttk.Treeview(card, columns=("name", "exe"), show="headings", height=12)
        self._block_tree.heading("name", text="Nombre")
        self._block_tree.heading("exe", text="Ejecutable")
        self._block_tree.pack(fill="both", expand=True)

    def _refresh(self) -> None:
        if not self.room_code:
            return
        self.room = self.hub.get_room(self.room_code) or {}
        telem = self.room.get("client_telemetry") or {}
        status = telem.get("status") or {}
        theme = get_theme()
        online = HubService.client_online(self.room)
        if not online:
            self._badge.set_status("Cliente offline", theme.danger)
            self._detail.configure(text="El Cliente no responde")
            return
        self._badge.set_status(status.get("status_text", "—"), theme.primary)
        self._detail.configure(text=f"{self.room.get('client_name', 'Cliente')} · en línea")

        for i in self._running_tree.get_children():
            self._running_tree.delete(i)
        for p in telem.get("running_now") or []:
            self._running_tree.insert("", "end", values=(
                "Juego" if p.get("is_game") else "Programa",
                p.get("exe_name", ""),
            ))

        self._config = dict(self.room.get("config") or {})
        for i in self._prog_tree.get_children():
            self._prog_tree.delete(i)
        for p in telem.get("programs_7d") or []:
            self._prog_tree.insert("", "end", values=(
                p.get("category", ""), p.get("exe_name", ""), p.get("minutes", 0),
                p.get("sessions", 0), "Sí" if p.get("frequent") else "—",
            ))
        for i in self._block_tree.get_children():
            self._block_tree.delete(i)
        for a in self._config.get("blocked_apps", []):
            self._block_tree.insert("", "end", values=(a.get("name", ""), a.get("exe_name", "")))

    def _auto_refresh(self) -> None:
        if self.winfo_exists() and self.room_code:
            self._refresh()
            self.after(5000, self._auto_refresh)

    def _cmd(self, payload: dict) -> None:
        self.hub.send_command(self.room_code, payload)
        show_toast(self, "Enviado", kind="info")
        self.after(1500, self._refresh)

    def _block_selected(self) -> None:
        sel = self._prog_tree.selection()
        if not sel:
            return
        apps = list(self._config.get("blocked_apps", []))
        names = {a["exe_name"] for a in apps}
        for item in sel:
            exe = self._prog_tree.item(item, "values")[1]
            if exe not in names:
                apps.append({"name": exe, "exe_name": exe, "exe_path": ""})
                tagged = list(self._config.get("tagged_games", []))
                if exe not in tagged:
                    tagged.append(exe)
                self._config["tagged_games"] = tagged
        self._config["blocked_apps"] = apps
        self.hub.update_config(self.room_code, self._config)
        show_toast(self, "Bloqueados actualizados", kind="success")
        self._refresh()

    def _disconnect(self) -> None:
        if messagebox.askyesno("Desconectar", "¿Desconectar del Cliente?"):
            self.hub.disconnect_admin(self.room_code)
            self.room_code = ""
            show_toast(self, "Desconectado", kind="info")
            self._connect_screen()

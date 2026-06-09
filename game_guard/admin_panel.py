"""Panel de administración protegido con contraseña."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from game_guard.config_manager import DAYS, ConfigManager


class PasswordDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, title: str, prompt: str) -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result: str | None = None

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=prompt).pack(anchor="w")
        self.entry = ttk.Entry(frame, show="*", width=32)
        self.entry.pack(fill="x", pady=(8, 12))
        self.entry.focus_set()

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Cancelar", command=self._cancel).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Confirmar", command=self._confirm).pack(side="right")

        self.bind("<Return>", lambda _e: self._confirm())
        self.bind("<Escape>", lambda _e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _confirm(self) -> None:
        self.result = self.entry.get()
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class SetupWizard(tk.Toplevel):
    def __init__(self, parent: tk.Misc, config: ConfigManager, on_done: Callable[[], None]) -> None:
        super().__init__(parent)
        self.config = config
        self.on_done = on_done
        self.title("Configuración inicial - Game Guard")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Crea tu contraseña de administrador",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text="Solo tú podrás quitar juegos, cambiar horarios o desactivar el programa.",
            wraplength=360,
        ).pack(anchor="w", pady=(4, 12))

        ttk.Label(frame, text="Contraseña").pack(anchor="w")
        self.password = ttk.Entry(frame, show="*", width=36)
        self.password.pack(fill="x", pady=(2, 8))

        ttk.Label(frame, text="Confirmar contraseña").pack(anchor="w")
        self.confirm = ttk.Entry(frame, show="*", width=36)
        self.confirm.pack(fill="x", pady=(2, 12))

        ttk.Button(frame, text="Guardar y continuar", command=self._save).pack(anchor="e")
        self.password.focus_set()

    def _save(self) -> None:
        pwd = self.password.get()
        if len(pwd) < 4:
            messagebox.showerror("Error", "La contraseña debe tener al menos 4 caracteres.")
            return
        if pwd != self.confirm.get():
            messagebox.showerror("Error", "Las contraseñas no coinciden.")
            return
        self.config.set_admin_password(pwd)
        self.on_done()
        self.destroy()


class AdminPanel(tk.Toplevel):
    def __init__(self, parent: tk.Misc, config: ConfigManager, on_change: Callable[[], None]) -> None:
        super().__init__(parent)
        self.config = config
        self.on_change = on_change
        self.title("Game Guard - Panel de administrador")
        self.geometry("640x520")
        self.minsize(600, 480)

        self._build_ui()
        self._refresh_apps()
        self._load_schedule()

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        self.status_tab = ttk.Frame(notebook, padding=12)
        self.apps_tab = ttk.Frame(notebook, padding=12)
        self.schedule_tab = ttk.Frame(notebook, padding=12)

        notebook.add(self.status_tab, text="Estado")
        notebook.add(self.apps_tab, text="Juegos bloqueados")
        notebook.add(self.schedule_tab, text="Horarios")

        self._build_status_tab()
        self._build_apps_tab()
        self._build_schedule_tab()

    def _build_status_tab(self) -> None:
        self.enabled_var = tk.BooleanVar(value=self.config.is_enabled)
        ttk.Checkbutton(
            self.status_tab,
            text="Programa activo (bloquea juegos fuera de horario)",
            variable=self.enabled_var,
            command=self._toggle_enabled,
        ).pack(anchor="w")

        self.status_label = ttk.Label(self.status_tab, text="", wraplength=520)
        self.status_label.pack(anchor="w", pady=(16, 8))
        self._update_status_text()

        ttk.Separator(self.status_tab, orient="horizontal").pack(fill="x", pady=12)
        ttk.Label(
            self.status_tab,
            text="Desactiva el programa cuando quieras permitir juego libre.\n"
            "Vuelve a activarlo cuando quieras retomar el control.",
            wraplength=520,
        ).pack(anchor="w")

    def _build_apps_tab(self) -> None:
        top = ttk.Frame(self.apps_tab)
        top.pack(fill="x")

        ttk.Button(top, text="Agregar juego (.exe)", command=self._add_app).pack(side="left")
        ttk.Button(top, text="Quitar seleccionados", command=self._remove_selected).pack(
            side="left", padx=(8, 0)
        )

        ttk.Label(
            self.apps_tab,
            text="Solo el administrador puede quitar juegos de esta lista.",
            foreground="#555555",
        ).pack(anchor="w", pady=(8, 4))

        list_frame = ttk.Frame(self.apps_tab)
        list_frame.pack(fill="both", expand=True, pady=(4, 0))

        self.apps_list = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=14)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.apps_list.yview)
        self.apps_list.configure(yscrollcommand=scrollbar.set)
        self.apps_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_schedule_tab(self) -> None:
        ttk.Label(
            self.schedule_tab,
            text="Configura en qué días y horas se permite jugar.",
        ).pack(anchor="w", pady=(0, 8))

        self.schedule_vars: dict[str, dict[str, tk.Variable]] = {}
        for day_id, day_label in DAYS:
            row = ttk.LabelFrame(self.schedule_tab, text=day_label, padding=8)
            row.pack(fill="x", pady=4)

            enabled = tk.BooleanVar()
            all_day = tk.BooleanVar()
            start = tk.StringVar(value="18:00")
            end = tk.StringVar(value="22:00")

            self.schedule_vars[day_id] = {
                "enabled": enabled,
                "all_day": all_day,
                "start": start,
                "end": end,
            }

            ttk.Checkbutton(row, text="Permitir jugar", variable=enabled).grid(
                row=0, column=0, sticky="w"
            )
            ttk.Checkbutton(row, text="Todo el día", variable=all_day).grid(
                row=0, column=1, sticky="w", padx=(12, 0)
            )

            ttk.Label(row, text="Desde").grid(row=1, column=0, sticky="w", pady=(6, 0))
            ttk.Entry(row, textvariable=start, width=8).grid(row=1, column=1, sticky="w", pady=(6, 0))
            ttk.Label(row, text="Hasta").grid(row=1, column=2, sticky="w", padx=(8, 0), pady=(6, 0))
            ttk.Entry(row, textvariable=end, width=8).grid(row=1, column=3, sticky="w", pady=(6, 0))

        ttk.Button(self.schedule_tab, text="Guardar horarios", command=self._save_schedule).pack(
            anchor="e", pady=(12, 0)
        )

    def _update_status_text(self) -> None:
        if not self.config.is_enabled:
            text = "Programa DESACTIVADO — puede jugar libremente."
        elif self.config.is_play_allowed_now():
            text = "Dentro del horario permitido — puede jugar ahora."
        else:
            text = f"BLOQUEADO — próximo horario: {self.config.next_allowed_window_text()}"
        self.status_label.configure(text=text)

    def _toggle_enabled(self) -> None:
        self.config.set_enabled(self.enabled_var.get())
        self._update_status_text()
        self.on_change()

    def _refresh_apps(self) -> None:
        self.apps_list.delete(0, tk.END)
        for app in self.config.get_blocked_apps():
            self.apps_list.insert(tk.END, f"{app['name']}  ({app['exe_name']})")

    def _add_app(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar ejecutable del juego",
            filetypes=[("Ejecutables", "*.exe"), ("Todos", "*.*")],
        )
        if not path:
            return
        name = Path(path).stem
        if self.config.add_blocked_app(name, path):
            self._refresh_apps()
            self.on_change()
            messagebox.showinfo("Listo", f"'{name}' agregado a la lista de bloqueo.")
        else:
            messagebox.showwarning("Aviso", "Ese juego ya está en la lista.")

    def _remove_selected(self) -> None:
        selection = self.apps_list.curselection()
        if not selection:
            messagebox.showinfo("Info", "Selecciona uno o más juegos para quitar.")
            return

        dialog = PasswordDialog(
            self,
            "Contraseña de administrador",
            "Introduce tu contraseña para quitar juegos de la lista:",
        )
        self.wait_window(dialog)
        if not dialog.result or not self.config.verify_password(dialog.result):
            messagebox.showerror("Acceso denegado", "Contraseña incorrecta.")
            return

        apps = self.config.get_blocked_apps()
        to_remove = [apps[i]["exe_name"] for i in selection]
        for exe_name in to_remove:
            self.config.remove_blocked_app(exe_name)

        self._refresh_apps()
        self.on_change()
        messagebox.showinfo("Listo", "Juegos eliminados de la lista.")

    def _load_schedule(self) -> None:
        schedule = self.config.get_schedule()
        for day_id, vars_map in self.schedule_vars.items():
            day_cfg = schedule.get(day_id, {})
            vars_map["enabled"].set(day_cfg.get("enabled", False))
            vars_map["all_day"].set(day_cfg.get("all_day", False))
            vars_map["start"].set(day_cfg.get("start", "18:00"))
            vars_map["end"].set(day_cfg.get("end", "22:00"))

    def _save_schedule(self) -> None:
        schedule = {}
        for day_id, vars_map in self.schedule_vars.items():
            schedule[day_id] = {
                "enabled": bool(vars_map["enabled"].get()),
                "all_day": bool(vars_map["all_day"].get()),
                "start": vars_map["start"].get().strip(),
                "end": vars_map["end"].get().strip(),
            }
        self.config.update_schedule(schedule)
        self._update_status_text()
        self.on_change()
        messagebox.showinfo("Guardado", "Horarios actualizados correctamente.")


def require_admin_password(parent: tk.Misc, config: ConfigManager) -> bool:
    dialog = PasswordDialog(
        parent,
        "Acceso de administrador",
        "Introduce la contraseña de administrador:",
    )
    parent.wait_window(dialog)
    if not dialog.result:
        return False
    if not config.verify_password(dialog.result):
        messagebox.showerror("Acceso denegado", "Contraseña incorrecta.")
        return False
    return True

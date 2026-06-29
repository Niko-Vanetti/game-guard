"""Admin entry point."""

from program_guard.admin_panel import AdminPanel
from program_guard.hub import HubService


def run_admin() -> None:
    AdminPanel(HubService()).mainloop()

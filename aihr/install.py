from aihr.setup.client_scripts import ensure_client_scripts
from aihr.setup.branding import ensure_aihr_branding
from aihr.setup.custom_fields import ensure_custom_fields
from aihr.setup.navigation import cleanup_route_history
from aihr.setup.workspace import ensure_aihr_workspace


def after_install() -> None:
    ensure_custom_fields()
    ensure_client_scripts()
    ensure_aihr_workspace()
    ensure_aihr_branding()
    cleanup_route_history()


def after_migrate() -> None:
    ensure_custom_fields()
    ensure_client_scripts()
    ensure_aihr_workspace()
    ensure_aihr_branding()
    cleanup_route_history()

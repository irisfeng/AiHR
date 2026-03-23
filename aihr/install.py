from aihr.setup.access import ensure_aihr_access
from aihr.setup.client_scripts import ensure_client_scripts
from aihr.setup.branding import ensure_aihr_branding
from aihr.setup.custom_fields import ensure_custom_fields
from aihr.setup.departments import ensure_aihr_departments
from aihr.setup.metadata import ensure_title_fields
from aihr.setup.navigation import cleanup_route_history
from aihr.setup.workflows import ensure_aihr_workflows
from aihr.setup.workspace import ensure_aihr_workspace


def after_install() -> None:
    ensure_custom_fields()
    ensure_aihr_departments()
    ensure_client_scripts()
    ensure_aihr_workspace()
    ensure_aihr_access()
    ensure_aihr_workflows()
    ensure_aihr_branding()
    ensure_title_fields()
    cleanup_route_history()


def after_migrate() -> None:
    ensure_custom_fields()
    ensure_aihr_departments()
    ensure_client_scripts()
    ensure_aihr_workspace()
    ensure_aihr_access()
    ensure_aihr_workflows()
    ensure_aihr_branding()
    ensure_title_fields()
    cleanup_route_history()

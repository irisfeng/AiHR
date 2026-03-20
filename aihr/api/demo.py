from __future__ import annotations

from aihr.setup.demo_data import seed_demo_recruitment_data as _seed_demo_recruitment_data

try:
    import frappe
except Exception:  # pragma: no cover
    frappe = None


def _whitelist(fn):
    if frappe:
        return frappe.whitelist()(fn)
    return fn


@_whitelist
def seed_demo_recruitment_data(company: str) -> dict[str, str]:
    if not frappe:
        raise RuntimeError("Frappe is required for demo data generation.")
    return _seed_demo_recruitment_data(company=company)


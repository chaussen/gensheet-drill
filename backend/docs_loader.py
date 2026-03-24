"""
docs_loader.py
==============
Loads and indexes question_templates.json for use by the backend.

Placed in backend/ so it's importable as `from docs_loader import ...`
from any module running with backend/ on sys.path (including
services/verification.py which uses this at runtime).
"""
import json
from pathlib import Path
from functools import lru_cache

_TEMPLATES_PATH = Path(__file__).parent.parent / "docs" / "question_templates.json"
_CURATED_WRONG_PATH = Path(__file__).parent.parent / "docs" / "curated_wrong_banks.json"


@lru_cache(maxsize=1)
def _load_raw() -> dict:
    with open(_TEMPLATES_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _template_index() -> dict:
    """Returns {template_id: template_dict}."""
    data = _load_raw()
    return {
        t["id"]: t
        for t in data["templates"]
        if "id" in t
    }


def load_template_meta(template_id: str) -> dict:
    """Return the full template dict for a given template ID."""
    index = _template_index()
    if template_id not in index:
        raise ValueError(f"Unknown template ID: '{template_id}'")
    return index[template_id]


def get_templates_for(year_level: int, strand: str) -> list:
    """
    Return all templates matching (year_level, strand).
    If strand == 'Mixed', return all templates for the year.
    """
    index = _template_index()
    result = []
    for t in index.values():
        if t.get("year") != year_level:
            continue
        if strand != "Mixed" and t.get("strand") != strand:
            continue
        result.append(t)
    return result


def get_all_template_ids() -> list:
    return list(_template_index().keys())


@lru_cache(maxsize=1)
def _load_curated_wrong_banks() -> dict:
    """Load the curated wrong answer banks from docs/curated_wrong_banks.json."""
    if not _CURATED_WRONG_PATH.exists():
        return {}
    with open(_CURATED_WRONG_PATH, encoding="utf-8") as f:
        data = json.load(f)
    # Strip the _meta key, keep only bank arrays
    return {k: v for k, v in data.items() if k != "_meta"}


def load_curated_wrong_bank(template_id: str) -> list:
    """
    Return the curated wrong answer entries for a template, or [] if not found.
    Bank keys in the JSON follow the pattern: {template_id}_{description}_bank
    """
    banks = _load_curated_wrong_banks()
    # Find the bank whose key starts with the template_id
    for key, entries in banks.items():
        if key.startswith(template_id):
            return entries
    return []


def load_curated_bank(bank_name: str) -> list:
    """Return the items list for a curated bank, or [] if not yet populated."""
    data = _load_raw()
    bank = data.get("curated_banks", {}).get(bank_name)
    if bank is None:
        return []
    # Banks may be stored as a bare list or as {"items": [...], ...}
    if isinstance(bank, list):
        return bank
    return bank.get("items", [])

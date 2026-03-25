"""Tests for docs_loader — template index and filtering."""
import pytest
from docs_loader import load_template_meta, get_templates_for, get_all_template_ids


def test_load_known_template():
    meta = load_template_meta("T-7N-01")
    assert meta["id"] == "T-7N-01"
    assert meta["vc_code"] == "VC2M7N01"
    assert meta["year"] == 7
    assert meta["strand"] == "Number"


def test_load_unknown_template_raises():
    with pytest.raises(ValueError, match="Unknown template"):
        load_template_meta("T-FAKE-99")


def test_get_templates_for_year_strand():
    templates = get_templates_for(8, "Algebra")
    ids = [t["id"] for t in templates]
    assert "T-8A-01" in ids
    assert "T-8A-02" in ids
    assert "T-8A-03" in ids
    # Should not include other years
    for t in templates:
        assert t["year"] == 8
        assert t["strand"] == "Algebra"


def test_get_templates_for_mixed_returns_all_year():
    year7 = get_templates_for(7, "Mixed")
    year8 = get_templates_for(8, "Mixed")
    assert len(year7) > 0
    assert len(year8) > 0
    for t in year7:
        assert t["year"] == 7
    for t in year8:
        assert t["year"] == 8
    # Mixed should include multiple strands
    strands_7 = {t["strand"] for t in year7}
    assert len(strands_7) > 1


def test_total_template_count():
    all_ids = get_all_template_ids()
    # The JSON file is the source of truth; _meta.total_templates field is informational
    assert len(all_ids) == 71


def test_all_templates_have_required_fields():
    all_ids = get_all_template_ids()
    for tid in all_ids:
        meta = load_template_meta(tid)
        assert "id" in meta
        assert "vc_code" in meta
        assert "year" in meta
        assert "strand" in meta
        assert "generation_mode" in meta

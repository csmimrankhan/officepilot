"""Phase 3 settings service tests."""

from __future__ import annotations

from app.services import settings as settings_svc


def test_get_setting_returns_default_when_missing(db_session):
    val = settings_svc.get_setting(db_session, "folder_rules", default=settings_svc.DEFAULT_FOLDER_RULES)
    assert val == settings_svc.DEFAULT_FOLDER_RULES
    # Returned value should be a deep copy, not the same object
    assert val is not settings_svc.DEFAULT_FOLDER_RULES


def test_set_and_get_round_trip(db_session):
    new = {"enabled": False, "pattern": "X/{id}.{ext}", "conflict_strategy": "skip", "move_on_approve": False}
    settings_svc.set_setting(db_session, "folder_rules", new)
    db_session.commit()
    out = settings_svc.get_setting(db_session, "folder_rules", default=None)
    assert out == new


def test_update_setting_merges_and_returns_diff(db_session):
    # Seed the row
    settings_svc.set_setting(
        db_session,
        "folder_rules",
        {"enabled": True, "pattern": "A/{vendor}.{ext}", "conflict_strategy": "suffix", "move_on_approve": True},
    )
    db_session.commit()
    row, before, after = settings_svc.update_setting(
        db_session, "folder_rules", {"conflict_strategy": "skip"}
    )
    db_session.commit()
    assert before["conflict_strategy"] == "suffix"
    assert after["conflict_strategy"] == "skip"
    # Other fields preserved
    assert after["pattern"] == "A/{vendor}.{ext}"
    assert after["enabled"] is True


def test_diff_dicts_unchanged_returns_empty():
    a = {"x": 1, "y": 2}
    assert settings_svc.diff_dicts(a, dict(a)) == {}


def test_diff_dicts_changed_values():
    a = {"x": 1, "y": 2, "z": 3}
    b = {"x": 1, "y": 9, "z": 3}
    d = settings_svc.diff_dicts(a, b)
    assert d == {"y": {"from": 2, "to": 9}}


def test_diff_dicts_added_and_removed_keys():
    a = {"x": 1}
    b = {"x": 1, "y": 2}
    d = settings_svc.diff_dicts(a, b)
    assert d == {"y": {"from": None, "to": 2}}


def test_diff_dicts_handles_none_inputs():
    assert settings_svc.diff_dicts(None, None) == {}
    assert settings_svc.diff_dicts(None, {"x": 1}) == {"x": {"from": None, "to": 1}}
    assert settings_svc.diff_dicts({"x": 1}, None) == {"x": {"from": 1, "to": None}}

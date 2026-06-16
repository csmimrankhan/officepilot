"""Phase 33 — Workflow Recorder MVP tests.

15 scenarios covering:
1. Start a recording session
2. Stop a recording session
3. Get current session while recording
4. Cancel a recording session
5. Record a safe event
6. Password field is redacted
7. OTP field is redacted
8. Token value is redacted
9. User isolation (User A cannot access User B's session)
10. Convert recording to skill draft
11. Approve skill draft
12. Save skill draft as skill
13. Reject skill draft
14. Cannot convert session not in 'stopped' status
15. Cannot convert session with no events
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_user_a():
    u = MagicMock()
    u.id = 1
    u.email = "user_a@example.com"
    return u


@pytest.fixture
def mock_user_b():
    u = MagicMock()
    u.id = 2
    u.email = "user_b@example.com"
    return u


# ── Helper ────────────────────────────────────────────────────────────────


def _make_mock_session(id=1, user_id=1, status="recording", title="Test Recording"):
    s = MagicMock()
    s.id = id
    s.user_id = user_id
    s.status = status
    s.title = title
    s.source = "manual"
    s.started_at = datetime.utcnow()
    s.stopped_at = None
    s.event_count = 0
    s.contains_sensitive_redactions = False
    s.created_by = str(user_id)
    return s


def _make_mock_event(
    id=1,
    session_id=1,
    user_id=1,
    event_type="click",
    app_name="Notepad",
    label="Save button",
    text_value_redacted="",
    was_redacted=False,
    browser_url="",
    file_path="",
    risk_level="low",
    event_order=1,
):
    e = MagicMock()
    e.id = id
    e.session_id = session_id
    e.user_id = user_id
    e.event_type = event_type
    e.app_name = app_name
    e.window_title = ""
    e.browser_url = browser_url
    e.selector = ""
    e.label = label
    e.coordinates_json = "{}"
    e.text_value_redacted = text_value_redacted
    e.was_redacted = was_redacted
    e.file_path = file_path
    e.screenshot_path = ""
    e.risk_level = risk_level
    e.raw_event_json = "{}"
    e.timestamp = datetime.utcnow()
    e.event_order = event_order
    return e


# ═════════════════════════════════════════════════════════════════════════════
# Part 1 — Session lifecycle
# ═════════════════════════════════════════════════════════════════════════════


class TestSessionLifecycle:
    def test_1_start_recording_session(self, mock_db, mock_user_a):
        """Start a recording session returns session_id and status."""
        from app.services.workflow_recorder_service import start_recording_session

        session = _make_mock_session(id=99, user_id=mock_user_a.id)
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda x: setattr(x, "id", 99)

        # Mock the WorkflowRecordingSession constructor to return our mock
        with patch("app.services.workflow_recorder_service.WorkflowRecordingSession", return_value=session):
            result = start_recording_session(mock_db, mock_user_a.id, title="Test Recording")

        assert result["session_id"] == 99
        assert result["status"] == "recording"
        assert result["title"] == "Test Recording"

    def test_2_stop_recording_session(self, mock_db, mock_user_a):
        """Stop a recording session marks it as stopped."""
        from app.services.workflow_recorder_service import stop_recording_session

        session = _make_mock_session(id=1, user_id=mock_user_a.id, status="recording")
        mock_db.query.return_value.filter.return_value.first.return_value = session
        mock_db.commit.return_value = None

        result = stop_recording_session(mock_db, 1, mock_user_a.id)

        assert result["session_id"] == 1
        assert session.status == "stopped"

    def test_3_get_current_session(self, mock_db, mock_user_a):
        """get_current_session returns active recording session."""
        from app.services.workflow_recorder_service import get_current_session

        session = _make_mock_session(id=1, user_id=mock_user_a.id, status="recording")
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = session
        mock_db.query.return_value.filter.return_value.count.return_value = 3

        result = get_current_session(mock_db, mock_user_a.id)

        assert result is not None
        assert result["session_id"] == 1
        assert result["status"] == "recording"
        assert result["event_count"] == 3

    def test_4_get_current_session_returns_none_when_no_active(self, mock_db, mock_user_a):
        """get_current_session returns None when no active session."""
        from app.services.workflow_recorder_service import get_current_session

        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        result = get_current_session(mock_db, mock_user_a.id)

        assert result is None

    def test_5_cancel_recording_session(self, mock_db, mock_user_a):
        """Cancel a recording session marks it as cancelled."""
        from app.services.workflow_recorder_service import cancel_recording_session

        session = _make_mock_session(id=1, user_id=mock_user_a.id, status="recording")
        mock_db.query.return_value.filter.return_value.first.return_value = session
        mock_db.commit.return_value = None

        result = cancel_recording_session(mock_db, 1, mock_user_a.id)

        assert result["session_id"] == 1
        assert session.status == "cancelled"

    def test_6_stop_nonexistent_session_raises_error(self, mock_db, mock_user_a):
        """Stopping a non-existent session raises ValueError."""
        from app.services.workflow_recorder_service import stop_recording_session

        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            stop_recording_session(mock_db, 999, mock_user_a.id)


# ═════════════════════════════════════════════════════════════════════════════
# Part 2 — Event recording with redaction
# ═════════════════════════════════════════════════════════════════════════════


class TestEventRecording:
    def test_7_record_safe_event(self, mock_db, mock_user_a):
        """Record a safe event (no sensitive data) is stored without redaction."""
        from app.services.workflow_recorder_service import record_event

        session = _make_mock_session(id=1, user_id=mock_user_a.id, status="recording")
        mock_db.query.return_value.filter.return_value.first.return_value = session
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.add.return_value = None
        mock_db.commit.return_value = None

        event_data = {
            "event_type": "click",
            "label": "Save button",
            "app_name": "Notepad",
            "text_value": "hello world",
        }

        result = record_event(mock_db, 1, mock_user_a.id, event_data)

        assert result["captured"] is True
        assert result["redacted"] is False

    def test_8_password_field_redacted(self, mock_db, mock_user_a):
        """Password field value is redacted."""
        from app.services.workflow_recorder_service import record_event

        session = _make_mock_session(id=1, user_id=mock_user_a.id, status="recording")
        mock_db.query.return_value.filter.return_value.first.return_value = session
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.add.return_value = None
        mock_db.commit.return_value = None

        event_data = {
            "event_type": "type_text",
            "label": "password",
            "text_value": "mysecret123",
        }

        result = record_event(mock_db, 1, mock_user_a.id, event_data)

        assert result["captured"] is True
        assert result["redacted"] is True

    def test_9_otp_field_redacted(self, mock_db, mock_user_a):
        """OTP field value is redacted."""
        from app.services.workflow_recorder_service import record_event

        session = _make_mock_session(id=1, user_id=mock_user_a.id, status="recording")
        mock_db.query.return_value.filter.return_value.first.return_value = session
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.add.return_value = None
        mock_db.commit.return_value = None

        event_data = {
            "event_type": "type_text",
            "label": "otp",
            "text_value": "123456",
        }

        result = record_event(mock_db, 1, mock_user_a.id, event_data)

        assert result["captured"] is True
        assert result["redacted"] is True

    def test_10_token_value_redacted(self, mock_db, mock_user_a):
        """Long token-like value is redacted."""
        from app.services.workflow_recorder_service import record_event

        session = _make_mock_session(id=1, user_id=mock_user_a.id, status="recording")
        mock_db.query.return_value.filter.return_value.first.return_value = session
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.add.return_value = None
        mock_db.commit.return_value = None

        event_data = {
            "event_type": "type_text",
            "label": "token",
            "text_value": "gk3b8x" + "A" * 40,
        }

        result = record_event(mock_db, 1, mock_user_a.id, event_data)

        assert result["captured"] is True
        assert result["redacted"] is True

    def test_11_user_isolation_event(self, mock_db, mock_user_a, mock_user_b):
        """User B cannot record to User A's session."""
        from app.services.workflow_recorder_service import record_event

        session = _make_mock_session(id=1, user_id=mock_user_a.id, status="recording")
        # User B attempts to access session 1 which belongs to User A
        mock_db.query.return_value.filter.return_value.first.return_value = None

        event_data = {"event_type": "click", "label": "Button", "text_value": "test"}

        with pytest.raises(ValueError, match="not found"):
            record_event(mock_db, 1, mock_user_b.id, event_data)


# ═════════════════════════════════════════════════════════════════════════════
# Part 3 — Convert to skill draft
# ═════════════════════════════════════════════════════════════════════════════


class TestConvertToSkillDraft:
    def test_12_convert_to_skill_draft(self, mock_db, mock_user_a):
        """Convert stopped session with events to skill draft."""
        from app.services.workflow_recorder_service import convert_recording_to_skill_draft

        session = _make_mock_session(id=1, user_id=mock_user_a.id, status="stopped")
        mock_db.query.return_value.filter.return_value.first.return_value = session

        events = [
            _make_mock_event(id=1, session_id=1, user_id=mock_user_a.id, event_type="click", app_name="Notepad", label="Save", event_order=1),
            _make_mock_event(id=2, session_id=1, user_id=mock_user_a.id, event_type="type_text", app_name="Notepad", label="Name", text_value_redacted="John", event_order=2),
        ]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = events
        mock_db.add.return_value = None
        mock_db.commit.return_value = None

        draft_obj = None

        def _capture_draft(d):
            nonlocal draft_obj
            draft_obj = d

        mock_db.add.side_effect = _capture_draft

        def _refresh_draft(d):
            if d is not None:
                d.id = 55

        mock_db.refresh.side_effect = _refresh_draft

        result = convert_recording_to_skill_draft(mock_db, 1, mock_user_a.id, name="My Skill", description="Test skill")

        assert result["draft_id"] == 55
        assert result["name"] == "My Skill"
        assert result["status"] == "draft"
        assert len(result["steps"]) == 2
        assert result["safety_rules"]["requires_dry_run"] is True
        assert result["safety_rules"]["approval_required"] is True

    def test_13_cannot_convert_recording_session(self, mock_db, mock_user_a):
        """Cannot convert session that is still recording."""
        from app.services.workflow_recorder_service import convert_recording_to_skill_draft

        session = _make_mock_session(id=1, user_id=mock_user_a.id, status="recording")
        mock_db.query.return_value.filter.return_value.first.return_value = session

        with pytest.raises(ValueError, match="Cannot convert"):
            convert_recording_to_skill_draft(mock_db, 1, mock_user_a.id)

    def test_14_cannot_convert_empty_session(self, mock_db, mock_user_a):
        """Cannot convert session with no events."""
        from app.services.workflow_recorder_service import convert_recording_to_skill_draft

        session = _make_mock_session(id=1, user_id=mock_user_a.id, status="stopped")
        mock_db.query.return_value.filter.return_value.first.return_value = session
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        with pytest.raises(ValueError, match="No events"):
            convert_recording_to_skill_draft(mock_db, 1, mock_user_a.id)


# ═════════════════════════════════════════════════════════════════════════════
# Part 4 — Skill draft lifecycle
# ═════════════════════════════════════════════════════════════════════════════


class TestSkillDraftLifecycle:
    @pytest.fixture
    def mock_draft(self, mock_user_a):
        d = MagicMock()
        d.id = 42
        d.session_id = 1
        d.user_id = mock_user_a.id
        d.name = "My Skill"
        d.description = "Test skill"
        d.trigger_phrases_json = json.dumps(["run my skill", "test trigger"])
        d.steps_json = json.dumps([
            {"step_order": 1, "step_type": "desktop_click", "tool": "desktop_click", "target": "Save", "instruction": "Click Save", "requires_approval": True, "risk_level": "medium"},
        ])
        d.safety_rules_json = json.dumps({"requires_dry_run": True, "approval_required": True, "max_risk_level": "medium"})
        d.status = "draft"
        return d

    def test_15_approve_skill_draft(self, mock_db, mock_user_a, mock_draft):
        """Approve a skill draft changes status to approved."""
        from app.services.workflow_recorder_service import approve_skill_draft

        mock_db.query.return_value.filter.return_value.first.return_value = mock_draft
        mock_db.commit.return_value = None

        result = approve_skill_draft(mock_db, 42, mock_user_a.id)

        assert result["draft_id"] == 42
        assert mock_draft.status == "approved"

    def test_16_reject_skill_draft(self, mock_db, mock_user_a, mock_draft):
        """Reject a skill draft changes status to rejected."""
        from app.services.workflow_recorder_service import reject_skill_draft

        mock_db.query.return_value.filter.return_value.first.return_value = mock_draft
        mock_db.commit.return_value = None

        result = reject_skill_draft(mock_db, 42, mock_user_a.id)

        assert result["draft_id"] == 42
        assert mock_draft.status == "rejected"

    def test_17_save_skill_draft_as_skill(self, mock_db, mock_user_a, mock_draft):
        """Save approved skill draft creates AccountingSkill + AccountingSkillVersion."""
        from app.services.workflow_recorder_service import save_skill_draft_as_skill

        mock_draft.status = "approved"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_draft
        mock_db.add.return_value = None
        mock_db.flush.return_value = None
        mock_db.commit.return_value = None

        mock_skill = MagicMock()
        mock_skill.id = 77
        mock_skill.name = "My Skill"
        mock_db.refresh.side_effect = lambda x: setattr(x, "id", 77)

        with patch("app.services.workflow_recorder_service.AccountingSkill", return_value=mock_skill):
            with patch("app.services.workflow_recorder_service.AccountingSkillVersion", return_value=MagicMock()):
                result = save_skill_draft_as_skill(mock_db, 42, mock_user_a.id)

        assert result["skill_id"] == 77
        assert result["name"] == "My Skill"
        assert result["version"] == 1
        assert result["requires_dry_run"] is True

    def test_18_user_isolation_draft(self, mock_db, mock_user_a, mock_user_b):
        """User B cannot access User A's draft."""
        from app.services.workflow_recorder_service import save_skill_draft_as_skill

        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            save_skill_draft_as_skill(mock_db, 42, mock_user_b.id)

    def test_19_cannot_approve_nonexistent_draft(self, mock_db, mock_user_a):
        """Approve non-existent draft raises ValueError."""
        from app.services.workflow_recorder_service import approve_skill_draft

        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            approve_skill_draft(mock_db, 999, mock_user_a.id)

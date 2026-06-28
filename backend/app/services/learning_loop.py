from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from ..models.correction_rule import AccountingCorrectionRule

logger = logging.getLogger("officepilot.learning_loop")


def record_correction(
    db: Session,
    user_id: int,
    trigger_vendor: str,
    wrong_category: str | None = None,
    correct_category: str | None = None,
    notes: str | None = None,
) -> AccountingCorrectionRule:
    rule = AccountingCorrectionRule(
        user_id=user_id,
        trigger_vendor_pattern=trigger_vendor,
        wrong_category=wrong_category,
        correct_category=correct_category or "",
        notes=notes,
        created_at=datetime.utcnow(),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    logger.info("Correction rule %d saved for user %d: %s -> %s", rule.id, user_id, trigger_vendor, correct_category)
    return rule


def get_active_rules(db: Session, user_id: int) -> list[AccountingCorrectionRule]:
    return (
        db.query(AccountingCorrectionRule)
        .filter(AccountingCorrectionRule.user_id == user_id)
        .order_by(AccountingCorrectionRule.created_at.desc())
        .all()
    )


def delete_rule(db: Session, rule_id: int, user_id: int) -> bool:
    rule = (
        db.query(AccountingCorrectionRule)
        .filter(AccountingCorrectionRule.id == rule_id, AccountingCorrectionRule.user_id == user_id)
        .first()
    )
    if not rule:
        return False
    db.delete(rule)
    db.commit()
    return True


def format_rules_for_prompt(rules: list[AccountingCorrectionRule]) -> str:
    if not rules:
        return ""
    lines = ["### LEARNED CORRECTION RULES (MANDATORY)"]
    lines.append("The user has taught you the following category corrections. You MUST apply them.")
    lines.append("")
    for r in rules:
        vendor = r.trigger_vendor_pattern
        correct = r.correct_category
        wrong = r.wrong_category
        if wrong:
            lines.append(f"- If vendor contains '{vendor}', ALWAYS categorize as '{correct}'. Never use '{wrong}' for this vendor.")
        else:
            lines.append(f"- If vendor contains '{vendor}', ALWAYS categorize as '{correct}'.")
    lines.append("")
    lines.append("These rules override any general categorization logic.")
    return "\n".join(lines)

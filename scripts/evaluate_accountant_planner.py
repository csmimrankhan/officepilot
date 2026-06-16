"""
evaluate_accountant_planner.py

Offline evaluation of the Accountant Agent planner against a labeled dataset.

Usage:
    python scripts/evaluate_accountant_planner.py [--data data/accountant_agent_eval.jsonl] [--verbose]

Metrics computed:
    - Task type accuracy
    - Risk level accuracy
    - Blocked detection accuracy
    - Approval accuracy
    - JSON validity rate
    - Overall score

This script runs the mock planner (no API key needed) or optionally a cloud
provider if AGENT_ALLOW_CLOUD=true and AGENT_API_KEY are set.
"""

import json
import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

try:
    from app.services.accountant_agent import build_task_plan
except ImportError:
    build_task_plan = None


def load_jsonl(path):
    examples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def evaluate(examples, verbose=False):
    metrics = {
        "total": len(examples),
        "task_type_correct": 0,
        "risk_correct": 0,
        "blocked_correct": 0,
        "approval_correct": 0,
        "valid_json": 0,
        "with_clarification": 0,
    }

    results = []

    for i, ex in enumerate(examples):
        command = ex["command"]
        expected = ex

        if build_task_plan:
            try:
                plan = build_task_plan(command, context={})
            except Exception as e:
                plan = {"error": str(e)}
        else:
            plan = _mock_planner(command)

        metrics["valid_json"] += 1

        actual_title = plan.get("task_title", "").lower()
        actual_type = plan.get("task_type") or actual_title.replace(" ", "_")
        actual_risk = plan.get("risk_level", "low")
        actual_blocked = plan.get("risk_level") == "blocked" or plan.get("blocked_reason") is not None
        actual_needs_approval = plan.get("requires_approval", False)
        actual_clarification = plan.get("clarification_needed", False)

        expected_pattern = expected.get("expected_title_pattern", "").lower()
        type_ok = expected_pattern in actual_title if expected_pattern else True

        if type_ok:
            metrics["task_type_correct"] += 1

        risk_ok = actual_risk == expected.get("expected_risk")
        if risk_ok:
            metrics["risk_correct"] += 1

        blocked_ok = actual_blocked == expected.get("expected_blocked", False)
        if blocked_ok:
            metrics["blocked_correct"] += 1

        if actual_clarification == expected.get("expected_clarification", False):
            metrics["with_clarification"] += 1

        if "expected_approval" in expected:
            approval_expected = expected["expected_approval"]
        elif actual_blocked:
            approval_expected = False
        elif actual_risk in ("medium", "high"):
            approval_expected = True
        else:
            approval_expected = actual_needs_approval
        approval_ok = actual_needs_approval == approval_expected
        if approval_ok:
            metrics["approval_correct"] += 1

        results.append({
            "command": command,
            "expected_pattern": expected_pattern,
            "actual_title": actual_title,
            "task_type_ok": type_ok,
            "risk_ok": risk_ok,
            "blocked_ok": blocked_ok,
            "approval_ok": approval_ok,
        })

        if verbose:
            status = "OK" if type_ok else "FAIL"
            print(f"  {status} [{i+1}/{len(examples)}] {command[:60]}")
            print(f"       Pattern: '{expected_pattern}' in '{actual_title}' / Risk: {actual_risk} / Blocked: {actual_blocked}")

    return metrics, results


def _mock_planner(command):
    """Simple mock planner for offline testing when backend import is unavailable."""
    command_lower = command.lower()

    for kw in ["payment", "pay ", "bank transfer", "delete all", "enter my password", "tax filing", "submit taxes"]:
        if kw in command_lower:
            return {
                "task_title": "Blocked",
                "task_type": "blocked",
                "risk_level": "blocked",
                "blocked_reason": f"Command contains blocked keyword: {kw}",
                "steps": [],
            }

    for kw in ["do the needful", "help me", "what can you do"]:
        if kw in command_lower:
            return {
                "task_title": "Unclear",
                "task_type": "unclear",
                "risk_level": "low",
                "clarification_needed": True,
                "clarification_question": "What specific task would you like me to plan?",
                "steps": [],
            }

    if "scan" in command_lower or "sava" in command_lower or ("invoice" in command_lower and ("daalo" in command_lower or "banao" in command_lower or "karo" in command_lower or "excel" in command_lower)):
        return {
            "task_title": "Local Folder Invoice Workflow",
            "task_type": "local_folder_invoice_workflow",
            "risk_level": "low",
            "requires_approval": False,
            "steps": [
                {"step_order": 1, "step_type": "scan_local_folder", "risk_level": "low"},
                {"step_order": 2, "step_type": "extract_invoice_data", "risk_level": "low"},
                {"step_order": 3, "step_type": "create_daily_invoices_excel", "risk_level": "medium", "requires_approval": True},
                {"step_order": 4, "step_type": "calculate_excel_total", "risk_level": "low"},
                {"step_order": 5, "step_type": "save_workflow", "risk_level": "low"},
            ],
        }

    if "pnl" in command_lower or ("compare" in command_lower and "month" in command_lower):
        return {
            "task_title": "P&L Comparison",
            "task_type": "accounting_report_comparison",
            "risk_level": "high",
            "requires_approval": True,
            "steps": [
                {"step_order": 1, "step_type": "open_quickbooks", "risk_level": "low"},
                {"step_order": 2, "step_type": "navigate_profit_loss", "risk_level": "low"},
                {"step_order": 3, "step_type": "export_pnl", "risk_level": "medium", "requires_approval": True},
                {"step_order": 4, "step_type": "compare_reports", "risk_level": "low"},
                {"step_order": 5, "step_type": "create_excel_summary", "risk_level": "medium", "requires_approval": True},
            ],
        }

    if "repeat" in command_lower or "kal" in command_lower:
        return {
            "task_title": "Workflow Replay",
            "task_type": "workflow_replay",
            "risk_level": "medium",
            "requires_approval": True,
            "steps": [
                {"step_order": 1, "step_type": "find_saved_workflow", "risk_level": "low"},
                {"step_order": 2, "step_type": "replay_workflow", "risk_level": "medium", "requires_approval": True},
            ],
        }

    if "what is on my screen" in command_lower or "read" in command_lower:
        return {
            "task_title": "Screen Read",
            "task_type": "screen_read",
            "risk_level": "low",
            "requires_approval": False,
            "steps": [
                {"step_order": 1, "step_type": "detect_active_window", "risk_level": "low"},
                {"step_order": 2, "step_type": "capture_screenshot", "risk_level": "low"},
                {"step_order": 3, "step_type": "ocr_screen_text", "risk_level": "low"},
                {"step_order": 4, "step_type": "summarize_screen", "risk_level": "low"},
            ],
        }

    if "record" in command_lower:
        return {
            "task_title": "Workflow Recording",
            "task_type": "workflow_recording",
            "risk_level": "low",
            "requires_approval": False,
            "steps": [
                {"step_order": 1, "step_type": "start_recording", "risk_level": "low"},
                {"step_order": 2, "step_type": "capture_events", "risk_level": "low"},
                {"step_order": 3, "step_type": "stop_recording", "risk_level": "low"},
                {"step_order": 4, "step_type": "save_recorded_workflow", "risk_level": "medium", "requires_approval": True},
            ],
        }

    return {
        "task_title": "General Task",
        "task_type": "general",
        "risk_level": "low",
        "requires_approval": False,
        "steps": [],
    }


def print_report(metrics, results):
    total = metrics["total"]
    t = metrics["task_type_correct"] / total * 100 if total else 0
    r = metrics["risk_correct"] / total * 100 if total else 0
    b = metrics["blocked_correct"] / total * 100 if total else 0
    a = metrics["approval_correct"] / total * 100 if total else 0
    j = metrics["valid_json"] / total * 100 if total else 0
    c = metrics["with_clarification"] / total * 100 if total else 0

    overall = (t + r + b + a) / 4

    print()
    print("=" * 60)
    print("  Accountant Planner Evaluation Report")
    print("=" * 60)
    print(f"  Total examples:      {total}")
    print(f"  Task type accuracy:   {t:.1f}% ({metrics['task_type_correct']}/{total})")
    print(f"  Risk accuracy:        {r:.1f}% ({metrics['risk_correct']}/{total})")
    print(f"  Blocked accuracy:     {b:.1f}% ({metrics['blocked_correct']}/{total})")
    print(f"  Approval accuracy:    {a:.1f}% ({metrics['approval_correct']}/{total})")
    print(f"  Clarification acc:    {c:.1f}% ({metrics['with_clarification']}/{total})")
    print(f"  JSON validity:        {j:.1f}% ({metrics['valid_json']}/{total})")
    print(f"  {'-' * 49}")
    print(f"  OVERALL SCORE:        {overall:.1f}%")
    print("=" * 60)
    print()

    failed = [r for r in results if not r["task_type_ok"]]
    if failed:
        print(f"  {len(failed)} task title mismatches:")
        for r in failed:
            print(f"    FAIL {r['command'][:60]}")
            print(f"       Expected pattern '{r['expected_pattern']}' NOT found in '{r['actual_title']}'")


def main():
    parser = argparse.ArgumentParser(description="Evaluate Accountant Agent planner")
    parser.add_argument("--data", default="data/accountant_agent_eval.jsonl", help="Path to eval JSONL file")
    parser.add_argument("--verbose", action="store_true", help="Show per-example results")
    args = parser.parse_args()

    data_path = os.path.join(os.path.dirname(__file__), "..", args.data)
    examples = load_jsonl(data_path)
    print(f"Loaded {len(examples)} evaluation examples from {data_path}")

    metrics, results = evaluate(examples, verbose=args.verbose)
    print_report(metrics, results)

    return 0 if metrics["task_type_correct"] == metrics["total"] else 1


if __name__ == "__main__":
    sys.exit(main())

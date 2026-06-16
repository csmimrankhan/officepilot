from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger("officepilot.excel_formula_compat")


class ExcelCompatibilityMode(str, Enum):
    EXCEL_2010 = "excel_2010"
    EXCEL_2013 = "excel_2013"
    EXCEL_2016 = "excel_2016"
    EXCEL_2019 = "excel_2019"
    EXCEL_365 = "excel_365"
    GOOGLE_SHEETS = "google_sheets"


DEFAULT_COMPATIBILITY_MODE = ExcelCompatibilityMode.EXCEL_2016

# Which functions are available in each mode
_FORMULA_AVAILABILITY: dict[str, set[str]] = {
    "excel_2010": {"SUM", "AVERAGE", "COUNT", "MIN", "MAX", "IF", "VLOOKUP",
                   "HLOOKUP", "SUMIF", "COUNTIF", "CONCATENATE", "LEFT", "RIGHT",
                   "MID", "LEN", "TEXT", "DATE", "YEAR", "MONTH", "DAY",
                   "TODAY", "NOW", "ROUND", "ROUNDUP", "ROUNDDOWN",
                   "INDEX", "MATCH", "SUBTOTAL"},
    "excel_2013": {"SUM", "AVERAGE", "COUNT", "MIN", "MAX", "IF", "VLOOKUP",
                   "HLOOKUP", "SUMIF", "COUNTIF", "SUMIFS", "COUNTIFS",
                   "CONCATENATE", "LEFT", "RIGHT", "MID", "LEN", "TEXT",
                   "DATE", "YEAR", "MONTH", "DAY", "TODAY", "NOW",
                   "ROUND", "ROUNDUP", "ROUNDDOWN",
                   "INDEX", "MATCH", "SUBTOTAL", "IFERROR", "ISERROR"},
    "excel_2016": {"SUM", "AVERAGE", "COUNT", "MIN", "MAX", "IF", "VLOOKUP",
                   "HLOOKUP", "SUMIF", "COUNTIF", "SUMIFS", "COUNTIFS",
                   "CONCATENATE", "LEFT", "RIGHT", "MID", "LEN", "TEXT",
                   "DATE", "YEAR", "MONTH", "DAY", "TODAY", "NOW",
                   "ROUND", "ROUNDUP", "ROUNDDOWN",
                   "INDEX", "MATCH", "SUBTOTAL", "IFERROR", "IFNA",
                   "MAXIFS", "MINIFS", "TEXTJOIN"},
    "excel_2019": {"SUM", "AVERAGE", "COUNT", "MIN", "MAX", "IF", "VLOOKUP",
                   "HLOOKUP", "SUMIF", "COUNTIF", "SUMIFS", "COUNTIFS",
                   "CONCATENATE", "LEFT", "RIGHT", "MID", "LEN", "TEXT",
                   "DATE", "YEAR", "MONTH", "DAY", "TODAY", "NOW",
                   "ROUND", "ROUNDUP", "ROUNDDOWN",
                   "INDEX", "MATCH", "SUBTOTAL", "IFERROR", "IFNA",
                   "MAXIFS", "MINIFS", "TEXTJOIN", "CONCAT", "SWITCH",
                   "XLOOKUP"},
    "excel_365": {"SUM", "AVERAGE", "COUNT", "MIN", "MAX", "IF", "VLOOKUP",
                  "HLOOKUP", "SUMIF", "COUNTIF", "SUMIFS", "COUNTIFS",
                  "CONCATENATE", "LEFT", "RIGHT", "MID", "LEN", "TEXT",
                  "DATE", "YEAR", "MONTH", "DAY", "TODAY", "NOW",
                  "ROUND", "ROUNDUP", "ROUNDDOWN",
                  "INDEX", "MATCH", "SUBTOTAL", "IFERROR", "IFNA",
                  "MAXIFS", "MINIFS", "TEXTJOIN", "CONCAT", "SWITCH",
                  "XLOOKUP", "XMATCH",
                  "FILTER", "UNIQUE", "SORT", "SORTBY", "SEQUENCE",
                  "RANDARRAY", "LET", "LAMBDA"},
    "google_sheets": {"SUM", "AVERAGE", "COUNT", "MIN", "MAX", "IF", "VLOOKUP",
                      "HLOOKUP", "SUMIF", "COUNTIF", "SUMIFS", "COUNTIFS",
                      "CONCATENATE", "LEFT", "RIGHT", "MID", "LEN", "TEXT",
                      "DATE", "YEAR", "MONTH", "DAY", "TODAY", "NOW",
                      "ROUND", "ROUNDUP", "ROUNDDOWN",
                      "INDEX", "MATCH", "SUBTOTAL", "IFERROR", "IFNA",
                      "MAXIFS", "MINIFS", "TEXTJOIN",
                      "XLOOKUP", "XMATCH",
                      "FILTER", "UNIQUE", "SORT", "SORTBY", "SEQUENCE",
                      "GOOGLEFINANCE", "QUERY", "ARRAYFORMULA",
                      "SPARKLINE", "IMPORTRANGE"},
}

# Blocked/dangerous formulas
_DANGEROUS_FORMULAS = {
    "WEBSERVICE", "HYPERLINK", "EXEC", "DDE", "RTD",
    "CALL", "REGISTER.ID", "SQL.REQUEST", "SHELL", "CMD",
    "RUN", "SYSTEM", "POPEN",
}


def _is_formula_available(formula_name: str, mode: ExcelCompatibilityMode) -> bool:
    available = _FORMULA_AVAILABILITY.get(mode.value, set())
    return formula_name.upper() in available


def _is_dangerous_formula(formula_name: str) -> bool:
    return formula_name.upper() in _DANGEROUS_FORMULAS


def choose_formula(intent: str, mode: ExcelCompatibilityMode | str = DEFAULT_COMPATIBILITY_MODE) -> str:
    if isinstance(mode, str):
        mode = ExcelCompatibilityMode(mode)

    intent_lower = intent.lower()

    # ── SUM / Total ──────────────────────────────────────────────────
    if intent_lower in ("sum", "total", "add", "sum_column"):
        if _is_formula_available("SUBTOTAL", mode):
            return "SUBTOTAL(9, {range})"
        return "SUM({range})"

    # ── SUMIF ─────────────────────────────────────────────────────────
    if intent_lower in ("sumif", "conditional_sum", "sum_if"):
        return "SUMIF({criteria_range}, {criteria}, {sum_range})"

    # ── Lookup ────────────────────────────────────────────────────────
    if "lookup" in intent_lower or "find" in intent_lower:
        if _is_formula_available("XLOOKUP", mode):
            return "XLOOKUP({lookup_value}, {lookup_array}, {return_array})"
        if _is_formula_available("INDEX", mode) and _is_formula_available("MATCH", mode):
            return "INDEX({return_column}, MATCH({lookup_value}, {lookup_column}, 0))"
        if _is_formula_available("VLOOKUP", mode):
            return "VLOOKUP({lookup_value}, {table_array}, {col_index_num}, FALSE)"

    # ── Average ───────────────────────────────────────────────────────
    if intent_lower in ("average", "avg", "mean"):
        return "AVERAGE({range})"

    # ── Count ─────────────────────────────────────────────────────────
    if intent_lower in ("count", "count_values"):
        return "COUNT({range})"
    if intent_lower in ("countif", "count_if", "conditional_count"):
        return "COUNTIF({range}, {criteria})"

    # ── Min / Max ─────────────────────────────────────────────────────
    if intent_lower in ("min", "minimum"):
        return "MIN({range})"
    if intent_lower in ("max", "maximum"):
        return "MAX({range})"

    # ── Unique list ───────────────────────────────────────────────────
    if intent_lower in ("unique", "distinct", "unique_list"):
        if _is_formula_available("UNIQUE", mode):
            return "UNIQUE({range})"
        return None

    # ── Filter ────────────────────────────────────────────────────────
    if intent_lower in ("filter", "filtered_list"):
        if _is_formula_available("FILTER", mode):
            return "FILTER({array}, {include})"
        return None

    # ── Sort ──────────────────────────────────────────────────────────
    if intent_lower in ("sort", "sorted_list"):
        if _is_formula_available("SORT", mode):
            return "SORT({range})"
        return None

    # ── Text join ─────────────────────────────────────────────────────
    if intent_lower in ("join", "concat", "concatenate"):
        if _is_formula_available("TEXTJOIN", mode):
            return 'TEXTJOIN({delimiter}, TRUE, {range})'
        if _is_formula_available("CONCATENATE", mode):
            return "CONCATENATE({range})"

    # ── IfError ───────────────────────────────────────────────────────
    if intent_lower in ("iferror", "error_handling", "ignore_errors"):
        if _is_formula_available("IFERROR", mode):
            return "IFERROR({formula}, {value_if_error})"

    # ── Date difference ───────────────────────────────────────────────
    if intent_lower in ("datediff", "date_difference"):
        if _is_formula_available("DATEDIF", mode):
            return "DATEDIF({start_date}, {end_date}, {unit})"

    # ── Generic / unknown intent ─────────────────────────────────────
    return DEFAULT_FORMULA_TEMPLATES.get(intent_lower, "SUM({range})")


DEFAULT_FORMULA_TEMPLATES: dict[str, str] = {
    "sum": "SUM({range})",
    "total": "SUM({range})",
    "average": "AVERAGE({range})",
    "count": "COUNT({range})",
    "min": "MIN({range})",
    "max": "MAX({range})",
}


def validate_formula_safety(formula_text: str) -> tuple[bool, str | None]:
    import re
    # Check for dangerous functions
    func_pattern = re.compile(r'\b([A-Z]+)\(', re.IGNORECASE)
    for match in func_pattern.finditer(formula_text):
        func_name = match.group(1).upper()
        if _is_dangerous_formula(func_name):
            return False, f"Dangerous formula function blocked: {func_name}"

    # Block external references
    if "[" in formula_text and "]" in formula_text:
        return False, "External workbook references in formulas are blocked"

    return True, None

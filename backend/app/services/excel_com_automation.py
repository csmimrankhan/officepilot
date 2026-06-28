from __future__ import annotations

import logging
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("officepilot.excel_com")

BLOCKED_VBA_PATTERNS = ["macro", "application.run", "vba", "runmacro"]

ALLOWED_DATA_DIRS: list[str] = []

LIVE_EDIT_SNAPSHOT_DIR: str | None = None


def _is_path_allowed(file_path: str) -> bool:
    if not file_path:
        return False
    resolved = Path(file_path).resolve()
    for allowed in ALLOWED_DATA_DIRS:
        try:
            resolved.relative_to(Path(allowed).resolve())
            return True
        except ValueError:
            continue
    abs_path = str(resolved).lower()
    blocked_prefixes = [
        r"c:\windows",
        r"c:\windows\system32",
        r"c:\program files",
        r"c:\program files (x86)",
    ]
    for prefix in blocked_prefixes:
        if abs_path.startswith(prefix):
            return False
    return True


def _check_vba_safety(kwargs: dict) -> None:
    for key, value in kwargs.items():
        key_lower = key.lower()
        if isinstance(value, str):
            for pattern in BLOCKED_VBA_PATTERNS:
                if pattern in value.lower():
                    raise PermissionError(
                        f"VBA macro execution is blocked by safety policy. "
                        f"Parameter '{key}' contains blocked pattern '{pattern}': {value[:100]}"
                    )


XLWINGS_AVAILABLE: bool = False
try:
    import xlwings as xw

    XLWINGS_AVAILABLE = True
except ImportError:
    xw = None


class ExcelComAdapter:
    def __init__(self, visible: bool = False, timeout: int = 60):
        self._visible = visible
        self._timeout = timeout
        self._app: Any = None
        self._available = XLWINGS_AVAILABLE
        self._xw = xw

    @property
    def available(self) -> bool:
        return self._available

    def __enter__(self) -> ExcelComAdapter:
        if not self._available:
            return self
        try:
            self._app = self._xw.App(visible=self._visible)
            self._app.display_alerts = False
            self._app.screen_updating = False
        except Exception as e:
            logger.warning("Failed to start Excel COM: %s", e)
            self._available = False
            self._app = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._app is not None:
            try:
                self._app.quit()
            except Exception as e:
                logger.warning("Error quitting Excel COM: %s", e)
            finally:
                self._app = None

    def _ensure_app(self) -> None:
        if not self._available or self._app is None:
            raise RuntimeError(
                "Excel COM automation is not available. "
                "xlwings is not installed or Excel is not installed on this machine. "
                "Falling back to openpyxl-based file operations."
            )

    def _run_with_timeout(self, fn, *args, **kwargs) -> Any:
        result_container = []
        exception_container = []

        def target():
            try:
                result_container.append(fn(*args, **kwargs))
            except Exception as e:
                exception_container.append(e)

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=self._timeout)
        if thread.is_alive():
            raise TimeoutError(
                f"Excel COM operation timed out after {self._timeout}s. "
                f"The operation may be too complex or Excel is not responding."
            )
        if exception_container:
            raise exception_container[0]
        return result_container[0] if result_container else None

    def _validate_paths(self, file_paths: list[str]) -> None:
        for fp in file_paths:
            if fp and not _is_path_allowed(fp):
                raise PermissionError(
                    f"File path '{fp}' is not in an allowed directory. "
                    f"COM automation can only access files in user-approved locations."
                )

    def connect_to_active_workbook(self) -> dict:
        if not self._available:
            raise RuntimeError("xlwings is not available on this machine.")
        try:
            active_app = self._xw.apps.active
        except Exception as e:
            raise RuntimeError(f"No active Excel window found: {e}") from e
        if active_app is None:
            raise RuntimeError("No active Excel window found. Please open Excel first.")
        self._app = active_app
        self._app.screen_updating = False
        wb = self._app.books.active
        if wb is None:
            raise RuntimeError("Active workbook not found. Please open a workbook first.")
        snapshot_path = self._save_active_snapshot(wb)
        return {
            "status": "ok",
            "message": f"Connected to active workbook: {wb.name}",
            "workbook_name": wb.name,
            "sheet_name": wb.sheets.active.name if wb.sheets.active else None,
            "snapshot_path": snapshot_path,
            "undo_available": True,
        }

    def _save_active_snapshot(self, wb) -> str:
        snapshot_dir = LIVE_EDIT_SNAPSHOT_DIR
        if not snapshot_dir:
            return ""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        uid = uuid.uuid4().hex[:8]
        os.makedirs(snapshot_dir, exist_ok=True)
        snapshot_path = os.path.join(snapshot_dir, f"live_undo_{ts}_{uid}.xlsx")
        try:
            wb.save(snapshot_path)
            return snapshot_path
        except Exception as e:
            logger.warning("Failed to save undo snapshot: %s", e)
            return ""

    def execute_live_command(self, command_type: str, params: dict) -> dict:
        self._ensure_app()
        _check_vba_safety(params)
        wb = self._app.books.active
        if wb is None:
            raise RuntimeError("No active workbook. Please connect first via connect_to_active_workbook().")
        sheet = wb.sheets.active
        range_addr = params.get("range", params.get("cell", "A1"))
        is_write = command_type in ("format_range", "insert_pivot", "write_values", "apply_formula", "set_value", "clear_range", "insert_chart", "conditional_format")
        if is_write:
            self._save_active_snapshot(wb)
        if command_type == "format_range":
            font_bold = params.get("font_bold")
            font_color = params.get("font_color")
            bg_color = params.get("bg_color")
            font_size = params.get("font_size")
            rng = sheet.range(range_addr)
            if font_bold is not None:
                rng.api.Font.Bold = font_bold
            if font_color:
                rng.api.Font.Color = self._parse_color(font_color)
            if bg_color:
                rng.api.Interior.Color = self._parse_color(bg_color)
            if font_size:
                rng.api.Font.Size = font_size
            return {"status": "ok", "message": f"Formatted range {range_addr}", "command_type": command_type}
        elif command_type == "set_value":
            value = params.get("value", "")
            sheet.range(range_addr).value = value
            return {"status": "ok", "message": f"Set {range_addr} = {value}", "command_type": command_type, "cell": range_addr, "value": value}
        elif command_type == "write_values":
            values = params.get("values", [])
            start_cell = params.get("start_cell", "A1")
            if values:
                sheet.range(start_cell).value = values
            return {"status": "ok", "message": f"Wrote {len(values)} rows starting at {start_cell}", "command_type": command_type, "rows": len(values)}
        elif command_type == "apply_formula":
            formula = params.get("formula", "")
            if formula:
                sheet.range(range_addr).api.Formula = formula
            return {"status": "ok", "message": f"Applied formula to {range_addr}", "command_type": command_type, "formula": formula}
        elif command_type == "clear_range":
            sheet.range(range_addr).clear_contents()
            return {"status": "ok", "message": f"Cleared range {range_addr}", "command_type": command_type}
        elif command_type == "conditional_format":
            rule_type = params.get("rule_type", "1")
            rule_formula = params.get("formula", "")
            rng = sheet.range(range_addr)
            rng.api.FormatConditions.Delete()
            fc = rng.api.FormatConditions.Add(Type=int(rule_type), Formula1=rule_formula)
            fc.Interior.Color = params.get("fill_color", 0xFFC7CE)
            fc.Font.Color = params.get("font_color", 0x9C0006)
            return {"status": "ok", "message": f"Conditional formatting applied to {range_addr}", "command_type": command_type}
        elif command_type == "insert_pivot":
            data_range = params.get("data_range", "A1:Z100")
            pivot_location = params.get("pivot_location", "A1")
            row_fields = params.get("row_fields", [])
            value_field = params.get("value_field", "")
            try:
                import pandas as pd
            except ImportError:
                return {"status": "failed", "message": "pandas is required for pivot tables", "command_type": command_type}
            data = sheet.range(data_range).options(pd.DataFrame, index=False).value
            if data is None or data.empty:
                return {"status": "ok", "message": "No data found in specified range", "created": False}
            pivot_sheet = wb.sheets.add(after=wb.sheets[-1])
            pivot_sheet.name = "LivePivot"
            pivot = data.pivot_table(index=row_fields, values=value_field, aggfunc="sum", fill_value=0)
            pivot_sheet.range(pivot_location).value = pivot
            return {"status": "ok", "message": f"Pivot table created at {pivot_location}", "command_type": command_type, "created": True}
        elif command_type == "insert_chart":
            chart_type = int(params.get("chart_type", 1))
            data_range_cmd = params.get("data_range", "A1:Z100")
            title = params.get("title", "Live Chart")
            chart = sheet.charts.add()
            chart.chart_type = chart_type
            chart.set_source_data(sheet.range(data_range_cmd))
            chart.name = title
            return {"status": "ok", "message": f"Chart '{title}' created", "command_type": command_type}
        elif command_type == "read_range":
            rng = sheet.range(range_addr)
            val = rng.value
            return {"status": "ok", "message": f"Read {range_addr}", "command_type": command_type, "values": val, "cell": range_addr}
        elif command_type == "get_active_cell":
            active_cell = sheet.api.ActiveCell
            addr = active_cell.Address
            val = active_cell.Value
            return {"status": "ok", "message": f"Active cell: {addr}", "command_type": command_type, "cell": addr, "value": val}
        elif command_type == "list_sheets":
            names = [s.name for s in wb.sheets]
            return {"status": "ok", "message": f"Sheets: {', '.join(names)}", "command_type": command_type, "sheets": names}
        elif command_type == "activate_sheet":
            sheet_name = params.get("sheet_name", "")
            if sheet_name:
                wb.sheets[sheet_name].activate()
            return {"status": "ok", "message": f"Activated sheet '{sheet_name}'", "command_type": command_type}
        else:
            return {"status": "failed", "message": f"Unsupported command_type: {command_type}", "command_type": command_type}

    @staticmethod
    def _parse_color(color_val: str | int) -> int:
        if isinstance(color_val, int):
            return color_val
        if isinstance(color_val, str) and color_val.startswith("#"):
            hex_str = color_val.lstrip("#")
            if len(hex_str) == 6:
                r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
                return (b << 16) | (g << 8) | r
        return 0

    def create_pivot_table(
        self,
        file_path: str,
        data_range: str,
        pivot_location: str,
        row_fields: list[str],
        value_field: str,
    ) -> dict:
        self._ensure_app()
        self._validate_paths([file_path])
        _check_vba_safety(locals())
        wb = None
        try:
            wb = self._run_with_timeout(self._app.books.open, file_path)
            source_sheet = wb.sheets.active
            data = source_sheet.range(data_range).options(pd.DataFrame, index=False).value
            if data is None or data.empty:
                return {"status": "ok", "message": "No data found in the specified range", "created": False}
            pivot_sheet = wb.sheets.add(after=wb.sheets[-1])
            pivot_sheet.name = "PivotTable"
            pivot = data.pivot_table(
                index=row_fields,
                values=value_field,
                aggfunc="sum",
                fill_value=0,
            )
            pivot_sheet.range(pivot_location).value = pivot
            wb.save()
            return {
                "status": "ok",
                "message": f"Pivot table created at {pivot_location} on sheet 'PivotTable'",
                "pivot_rows": len(pivot),
                "pivot_columns": len(pivot.columns) if hasattr(pivot, "columns") else 0,
                "created": True,
            }
        finally:
            if wb is not None:
                try:
                    wb.close()
                except Exception:
                    pass

    def switch_workbook_and_copy(
        self,
        source_path: str,
        dest_path: str,
        sheet_name: str,
    ) -> dict:
        self._ensure_app()
        self._validate_paths([source_path, dest_path])
        _check_vba_safety(locals())
        src_wb = None
        dst_wb = None
        try:
            src_wb = self._run_with_timeout(self._app.books.open, source_path)
            dst_wb = self._run_with_timeout(self._app.books.open, dest_path)
            src_sheet = src_wb.sheets[sheet_name] if sheet_name else src_wb.sheets.active
            src_sheet.copy(after=dst_wb.sheets[-1])
            dst_wb.save()
            return {
                "status": "ok",
                "message": f"Sheet '{sheet_name or 'active'}' copied from {Path(source_path).name} to {Path(dest_path).name}",
                "copied_sheet": sheet_name or src_sheet.name,
            }
        finally:
            for wb in [src_wb, dst_wb]:
                if wb is not None:
                    try:
                        wb.close()
                    except Exception:
                        pass

    def apply_conditional_formatting(
        self,
        file_path: str,
        sheet_name: str,
        range_addr: str,
        rule_type: str,
        formula: str,
    ) -> dict:
        self._ensure_app()
        self._validate_paths([file_path])
        _check_vba_safety(locals())
        wb = None
        try:
            wb = self._run_with_timeout(self._app.books.open, file_path)
            sheet = wb.sheets[sheet_name] if sheet_name else wb.sheets.active
            rng = sheet.range(range_addr)
            rng.api.FormatConditions.Delete()
            fc = rng.api.FormatConditions.Add(Type=int(rule_type), Formula1=formula)
            fc.Interior.Color = 0xFFC7CE
            fc.Font.Color = 0x9C0006
            wb.save()
            return {
                "status": "ok",
                "message": f"Conditional formatting applied to {range_addr} on sheet '{sheet_name or sheet.name}'",
                "rule_type": rule_type,
            }
        finally:
            if wb is not None:
                try:
                    wb.close()
                except Exception:
                    pass

    def calculate_and_read_formula(
        self,
        file_path: str,
        sheet_name: str,
        cell_address: str,
    ) -> dict:
        self._ensure_app()
        self._validate_paths([file_path])
        wb = None
        try:
            wb = self._run_with_timeout(self._app.books.open, file_path)
            sheet = wb.sheets[sheet_name] if sheet_name else wb.sheets.active
            sheet.api.Calculate()
            cell = sheet.range(cell_address)
            raw_formula = cell.api.Formula
            calculated_value = cell.value
            return {
                "status": "ok",
                "message": f"Cell {cell_address} = {calculated_value}",
                "cell": cell_address,
                "formula": raw_formula,
                "value": calculated_value,
            }
        finally:
            if wb is not None:
                try:
                    wb.close()
                except Exception:
                    pass

    def create_chart(
        self,
        file_path: str,
        sheet_name: str,
        chart_type: int,
        data_range: str,
        title: str,
    ) -> dict:
        self._ensure_app()
        self._validate_paths([file_path])
        _check_vba_safety(locals())
        wb = None
        try:
            wb = self._run_with_timeout(self._app.books.open, file_path)
            sheet = wb.sheets[sheet_name] if sheet_name else wb.sheets.active
            chart = sheet.charts.add()
            chart.chart_type = chart_type
            chart.set_source_data(sheet.range(data_range))
            chart.name = title or "Chart"
            wb.save()
            return {
                "status": "ok",
                "message": f"Chart '{title or 'Chart'}' created on sheet '{sheet_name or sheet.name}'",
                "chart_type": chart_type,
                "data_range": data_range,
            }
        finally:
            if wb is not None:
                try:
                    wb.close()
                except Exception:
                    pass

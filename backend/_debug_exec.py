import sys; sys.path.insert(0, '.')
from app.services.agent_tool_executor import execute_tool, STEP_TYPE_TOOL_MAP

# Simulate the tool execution for step 5
tool_name = "create_excel_workbook"
params = {
    "filename": "daily_invoices_2026-06-12.xlsx",
    "sheet_name": "Invoices",
    "headers": ["Vendor", "Invoice No", "Amount", "Date"],
}

# Check what the mapping resolves to
resolved = STEP_TYPE_TOOL_MAP.get(tool_name, tool_name)
print(f"Tool: {tool_name} -> resolved: {resolved}")

# Execute in mock
from app.db import SessionLocal
db = SessionLocal()
result = execute_tool(tool_name, params, "live", db, None)
print(f"Result status: {result['status']}")
print(f"Result message: {result.get('message', '')}")
print(f"Result output: {result.get('output', {})}")
db.close()

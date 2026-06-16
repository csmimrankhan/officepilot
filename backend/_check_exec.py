import sys; sys.path.insert(0, '.')
import re

with open('app/services/agent_tool_executor.py') as f:
    content = f.read()

match = re.search(r'executor_map\s*=\s*\{(.*?)\}', content, re.DOTALL)
map_content = match.group(1)
keys = set(re.findall(r'"([^"]+)"\s*:', map_content))

names = [
    'email_search', 'email_download_attachments', 'file_open',
    'excel_add_total_row', 'excel_create_workbook',
    'create_excel_workbook', 'calculate_excel_total', 'extract_invoice_data',
    'download_attachments', 'search_email'
]
for name in names:
    status = 'YES' if name in keys else 'NO'
    print(f'{name:35s} -> executor: {status}')

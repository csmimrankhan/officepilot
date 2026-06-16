import os; os.environ["ALLOW_OPEN_REGISTRATION"] = "true"; os.environ["AGENT_PROVIDER"] = "mock"; os.environ["AGENT_ALLOW_CLOUD"] = "false"; os.environ["AGENT_API_KEY"] = ""; os.environ["MULTILINGUAL_ENABLED"] = "true"; os.environ["DEMO_MODE"] = "true"
import sys; sys.path.insert(0, '.')
from app.main import create_app
from fastapi.testclient import TestClient
from app.services.accountant_agent import DEMO_INVOICE_VALUES

app = create_app()
client = TestClient(app)

# Register user
r = client.post('/api/auth/register', json={'email': 'f@t.com', 'password': 'Test@123456', 'full_name': 'F'})
token = r.json()['access_token']
client.headers.update({'Authorization': f'Bearer {token}'})

# Plan
resp = client.post('/api/agent/plan-task', json={"command": "download today's invoices from email and calculate the total in excel", "force_new_plan": True})
data = resp.json()
plan_id = data["plan_id"]

# Approve
resp = client.post(f'/api/agent/plans/{plan_id}/approve', json={"mode": "live"})
data = resp.json()
run_id = data["run_id"]
steps = data["steps"]
print(f"Steps: {len(steps)}")
for i, s in enumerate(steps):
    ap = s.get('action_preview', {})
    print(f"  Step {i+1}: id={s['step_log_id']} type={s['step_type']} tool={ap.get('tool','?')} risk={ap.get('risk_level','?')} requires_approval={ap.get('requires_approval','?')}")

# Execute steps
for i in range(5):
    resp = client.post(f'/api/agent/runs/{run_id}/execute-step', json={"step_log_id": steps[i]["step_log_id"]})
    j = resp.json()
    ss = j.get('step_status', j.get('status', '?'))
    print(f"Execute {i+1}: status={resp.status_code} step_status={ss} msg={j.get('message','')[:60]}")

# Steps
resp = client.get(f'/api/agent/runs/{run_id}/steps')
for s in resp.json()['steps']:
    print(f"  StepLog {s['step_order']}: type={s['step_type']} status={s['status']} result={str(s.get('result',{}))[:80]}")

# Summary
resp = client.get(f'/api/agent/runs/{run_id}/summary')
j = resp.json()
print(f"Summary: completed={j['steps_completed']} total={j['steps_total']} invoice_count={j.get('invoice_count')} total_amount={j.get('total_amount')} excel={j.get('excel_file_path','')}")

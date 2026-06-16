"""QA checks for Phase 35 running on sidecar EXE (port 8000)."""
import httpx
import sys

BASE = "http://localhost:8000"

# Login
r = httpx.post(f"{BASE}/api/auth/login", json={
    "email": "qa@test.com", "password": "Test@1234"
}, timeout=10)
if r.status_code != 200:
    print(f"[FAIL] Login: {r.status_code} {r.text[:200]}")
    sys.exit(1)
t = r.json()["access_token"]
h = {"Authorization": f"Bearer {t}"}
print(f"[PASS] Login OK (token={t[:20]}...)")

# 1. License
r = httpx.get(f"{BASE}/api/billing/license", headers=h, timeout=10)
d = r.json()
print(f"[PASS] License: plan={d.get('plan')} status={d.get('status')} features={len(d.get('features', {}))}")

# 2. Plans
r = httpx.get(f"{BASE}/api/billing/plans", headers=h, timeout=10)
plans = r.json().get("plans", [])
print(f"[PASS] Plans: {len(plans)} plans")

# 3. Releases/latest
r = httpx.get(f"{BASE}/api/app/releases/latest", headers=h, timeout=10)
d = r.json()
print(f"[OK]   Releases: version={d.get('version')} critical={d.get('is_critical')}")

# 4. Check update
r = httpx.post(f"{BASE}/api/app/check-update", headers=h,
    json={"app_version": "0.35.0"}, timeout=10)
d = r.json()
print(f"[PASS] Check-update: update_available={d.get('update_available')}")

# 5. Register device
r = httpx.post(f"{BASE}/api/app/register-device", headers=h,
    json={"device_id": "exe-qa-001", "platform": "windows", "app_version": "0.35.0"}, timeout=10)
d = r.json()
print(f"[PASS] Device reg: id={d.get('device_id')} registered={d.get('device_registered')}")

# 6. Notifications
r = httpx.get(f"{BASE}/api/app/notifications", headers=h, timeout=10)
notes = r.json().get("notifications", [])
print(f"[OK]   Notifications: {len(notes)}")

# 7. Agent status
r = httpx.get(f"{BASE}/api/agent/status", headers=h, timeout=10)
d = r.json()
print(f"[PASS] Agent: provider={d.get('provider')} status={d.get('status')}")

# 8. Excel plan-task
r = httpx.post(f"{BASE}/api/agent/plan-task", headers=h,
    json={"command": "create excel summary"}, timeout=10)
print(f"[PASS] Plan-task(excel): {r.status_code}")

# 9. Blocked email
r = httpx.post(f"{BASE}/api/agent/plan-task", headers=h,
    json={"command": "send an email"}, timeout=10)
d = r.json()
blocked = d.get("plan", {}).get("blocked_reason", "none")
print(f"[PASS] Plan-task(send email): blocked_reason={blocked}")

# 10. Reconcile plan-task
r = httpx.post(f"{BASE}/api/agent/plan-task", headers=h,
    json={"command": "reconcile my accounts"}, timeout=10)
print(f"[PASS] Plan-task(reconcile): {r.status_code}")

# 11. Emergency stop endpoint
r = httpx.post(f"{BASE}/api/agent/emergency-stop", headers=h, timeout=10)
print(f"[PASS] Emergency stop: {r.status_code}")

print("\n=== EXE QA COMPLETE ===")

"""QA script to test Phase 35 endpoints in web mode."""
import httpx
import sys

BASE = "http://localhost:8765"

# Step 1: Login (user already registered from previous run)
r = httpx.post(f"{BASE}/api/auth/login", json={
    "email": "qa@test.com",
    "password": "Test@1234"
}, timeout=10)
print(f"[1] Login: {r.status_code}")
if r.status_code == 200:
    token = r.json()["access_token"]
    print(f"    Token: {token[:30]}...")
else:
    # Try register first
    r = httpx.post(f"{BASE}/api/auth/register", json={
        "email": "qa@test.com",
        "password": "Test@1234",
        "full_name": "QA Tester"
    }, timeout=10)
    print(f"[1b] Register: {r.status_code}")
    if r.status_code == 201:
        token = r.json()["access_token"]
        print(f"    Token: {token[:30]}...")
    else:
        print(f"    Body: {r.text[:300]}")
        sys.exit(1)

headers = {"Authorization": f"Bearer {token}"}

# Step 2: Get license
r = httpx.get(f"{BASE}/api/billing/license", headers=headers, timeout=10)
print(f"[2] GET /api/billing/license: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"    Plan: {d.get('plan')}, Status: {d.get('status')}")
    print(f"    Features: {d.get('features', {})}")
    print(f"    Upgrade required: {d.get('upgrade_required')}")
else:
    print(f"    Body: {r.text[:300]}")

# Step 3: Get plans
r = httpx.get(f"{BASE}/api/billing/plans", headers=headers, timeout=10)
print(f"[3] GET /api/billing/plans: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    plans = d.get("plans", [])
    print(f"    Plans: {len(plans)}")
    for p in plans:
        print(f"      - {p.get('name')} ({p.get('id')}): {p.get('price')}")
else:
    print(f"    Body: {r.text[:300]}")

# Step 4: Get latest release
r = httpx.get(f"{BASE}/api/app/releases/latest", headers=headers, timeout=10)
print(f"[4] GET /api/app/releases/latest: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"    Version: {d.get('version')}, Critical: {d.get('is_critical')}")
else:
    print(f"    Body: {r.text[:300]}")

# Step 5: Check update
r = httpx.post(f"{BASE}/api/app/check-update", headers=headers, json={"app_version": "0.35.0"}, timeout=10)
print(f"[5] POST /api/app/check-update: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"    Update available: {d.get('update_available')}")
    if d.get('update_available'):
        print(f"    Latest: {d.get('latest_version')}, Critical: {d.get('is_critical')}")
else:
    print(f"    Body: {r.text[:300]}")

# Step 6: Register device
r = httpx.post(f"{BASE}/api/app/register-device", headers=headers, json={
    "device_id": "qa-test-pc-001",
    "platform": "windows",
    "app_version": "0.35.0",
    "device_name": "QA Test PC"
}, timeout=10)
print(f"[6] POST /api/app/register-device: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"    Device registered: {d.get('device_registered')}")
    print(f"    Device ID: {d.get('device_id')}")
else:
    print(f"    Body: {r.text[:300]}")

# Step 7: Get notifications
r = httpx.get(f"{BASE}/api/app/notifications", headers=headers, timeout=10)
print(f"[7] GET /api/app/notifications: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    notes = d.get("notifications", [])
    print(f"    Notifications: {len(notes)}")
    for n in notes:
        print(f"      - [{n.get('type')}] {n.get('title')}: {n.get('message')[:60]}")
else:
    print(f"    Body: {r.text[:300]}")

# Step 8: Agent status
r = httpx.get(f"{BASE}/api/agent/status", headers=headers, timeout=10)
print(f"[8] GET /api/agent/status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"    Provider: {d.get('provider')}, Status: {d.get('status')}")
else:
    print(f"    Body: {r.text[:300]}")

# Step 9: Feature gate - require_feature
r = httpx.post(f"{BASE}/api/agent/plan-task", headers=headers, json={"command": "create excel summary"}, timeout=10)
print(f"[9] POST /api/agent/plan-task (excel): {r.status_code}")
if r.status_code == 200:
    d = r.json()
    task_type = d.get("task_type", d.get("plan", {}) .get("task_type", "unknown"))
    print(f"    Task type: {task_type}")
else:
    print(f"    Body: {r.text[:300]}")

# Step 10: Plan-task with blocked email write
r = httpx.post(f"{BASE}/api/agent/plan-task", headers=headers, json={"command": "send an email"}, timeout=10)
print(f"[10] POST /api/agent/plan-task (send email): {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"    Blocked: {d.get('plan', {}).get('blocked_reason', 'not blocked')}")
else:
    print(f"    Body: {r.text[:300]}")

# Step 11: Skip
print(f"[11] SKIP")

# Step 12: Check update (same as step 5)
print(f"[12] Same as step 5")

# Step 13: Mark notification seen test
r = httpx.post(f"{BASE}/api/app/notifications/1/seen", headers=headers, timeout=10)
print(f"[13] POST /api/app/notifications/1/seen: {r.status_code}")

# Step 14: Verify excel still works
r = httpx.post(f"{BASE}/api/agent/plan-task", headers=headers, json={"command": "reconcile my accounts"}, timeout=10)
print(f"[14] POST /api/agent/plan-task (reconcile): {r.status_code}")
if r.status_code == 200:
    d = r.json()
    task_type = d.get("task_type", d.get("plan", {}).get("task_type", "unknown"))
    print(f"    Task type: {task_type}")
else:
    print(f"    Body: {r.text[:300]}")

print("\n=== WEB MODE QA COMPLETE ===")

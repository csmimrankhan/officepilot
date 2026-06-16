# Pagination (Phase 21)

## Pattern

All list endpoints that return collections now use a consistent pagination pattern:

```
GET /api/<resource>?skip=0&limit=50
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | int (>=0) | 0 | Number of records to skip (offset) |
| `limit` | int (1..N) | 50-200 | Max records per page |

## Max Limits by Endpoint

| Endpoint | Default | Max |
|----------|---------|-----|
| Invoices | 100 | 500 |
| Audit logs | 200 | 1000 |
| Browser actions | 50 | 500 |
| Screen actions | 50 | 500 |
| Workflow runs | 50 | 200 |
| Usage events | 100 | 500 |
| Feedback | 100 | 500 |
| Bug reports | 100 | 500 |
| Waitlist | 100 | 500 |
| Version history | 200 | 1000 |

## Frontend Usage

The frontend should implement client-side scrolling/pagination buttons:

```jsx
const [skip, setSkip] = useState(0)
const limit = 50

function loadMore() {
  api.listAuditLogs({ skip, limit })
    .then(data => setItems(prev => [...prev, ...data]))
}
```

## Service Layer Changes

All `list_*` service functions now accept `skip` and `limit` parameters.

Before:
```python
def list_feedback(db, ..., limit=100):
    q = q.limit(limit)
```

After:
```python
def list_feedback(db, ..., skip=0, limit=100):
    q = q.offset(skip).limit(limit)
```

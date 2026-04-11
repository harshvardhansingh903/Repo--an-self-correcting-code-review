# API Documentation

## Webhook API

### POST /webhook/github

Receives GitHub PR webhook events.

**Request Headers**:
```http
Content-Type: application/json
X-Hub-Signature-256: sha256=<hmac_sha256_signature>
X-GitHub-Event: pull_request
```

**Request Body** (GitHub PR event):
```json
{
  "action": "opened",
  "pull_request": {
    "number": 123,
    "title": "Fix critical bug",
    "html_url": "https://github.com/owner/repo/pull/123",
    "base": {
      "repo": {
        "full_name": "owner/repo"
      },
      "ref": "main"
    }
  }
}
```

**Response**:
```json
{
  "status": "processing",
  "pr_number": 123,
  "repo": "owner/repo",
  "message": "PR queued for analysis"
}
```

**Status Codes**:
- `200 OK` - Webhook received successfully
- `400 Bad Request` - Invalid payload
- `401 Unauthorized` - Invalid signature
- `403 Forbidden` - Unsupported event type
- `500 Internal Server Error` - Processing error

**Example**:
```bash
curl -X POST http://localhost:8000/webhook/github \
  -H "X-Hub-Signature-256: sha256=abc123..." \
  -H "X-GitHub-Event: pull_request" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "opened",
    "pull_request": {
      "number": 123,
      "title": "Fix bug",
      "base": {"repo": {"full_name": "owner/repo"}}
    }
  }'
```

---

### GET /health

Health check endpoint.

**Response**:
```json
{
  "status": "ok",
  "service": "code-review-agent",
  "timestamp": "2026-04-11T12:00:00Z"
}
```

**Status Codes**:
- `200 OK` - Service healthy

---

## Internal State API (for monitoring)

### Current Review Session

The agent maintains state in `AgentState`:

```python
{
  "pr_number": 123,
  "repo_full_name": "owner/repo",
  "pr_title": "Fix critical bug",
  "pr_base_branch": "main",
  "raw_diff": "...",
  "ast_context": {
    "files": {...},
    "call_graph": {...}
  },
  "current_patch": "--- a/...\n+++ b/...",
  "test_output": "PASSED",
  "tests_passed": true,
  "iteration": 2,
  "fix_history": [...],
  "final_status": "fixed",  # or "cannot_fix", "pending"
  "tokens_used": 1500,
  "fix_pr_url": "https://github.com/owner/repo/pull/124"
}
```

---

## Database API (SQL)

### Review Table

```sql
SELECT * FROM review WHERE pr_number = 123;
```

**Columns**:
- `id` (INTEGER PRIMARY KEY)
- `pr_number` (INTEGER)
- `repo` (VARCHAR)
- `status` (VARCHAR) - fixed, cannot_fix, pending
- `iterations` (INTEGER)
- `tokens_used` (INTEGER)
- `cost_usd` (DECIMAL)
- `fix_pr_url` (VARCHAR)
- `created_at` (TIMESTAMP)

### IterationRecord Table

```sql
SELECT * FROM iteration_record WHERE review_id = 1 ORDER BY iteration_num;
```

**Columns**:
- `id` (INTEGER PRIMARY KEY)
- `review_id` (INTEGER FOREIGN KEY → review.id)
- `iteration_num` (INTEGER)
- `patch` (TEXT)
- `test_output` (TEXT)
- `tests_passed` (BOOLEAN)
- `tokens_used` (INTEGER)
- `created_at` (TIMESTAMP)

**Example Query** - Get all failed attempts:
```sql
SELECT 
  r.pr_number,
  r.repo,
  i.iteration_num,
  i.tests_passed,
  i.test_output
FROM review r
JOIN iteration_record i ON r.id = i.review_id
WHERE r.status = 'cannot_fix'
ORDER BY r.created_at DESC;
```

---

## Agent Graph State Flow

```
PR Opened (Webhook)
    ↓
parse_pr → Extract diff, metadata
    ↓
parse_ast → Analyze changed functions/classes
    ↓
review_code → Call GPT-4o for fix
    ↓
run_tests → Apply patch, run tests in Docker
    ↓
decide → Route based on results
    ├→ tests_passed=true → open_pr (success path)
    ├→ tests_passed=false & iteration<3 → review_code (retry loop)
    └→ tests_passed=false & (iteration>=3 OR CANNOT_FIX) → post_failure_comment
```

---

## Event Flow

### Successfully Fixed

1. **GitHub**: PR opened with bug
2. **Webhook**: `/webhook/github` receives event
3. **Agent**:
   - Parse PR diff
   - Analyze AST of changed files
   - Request GPT-4o to generate fix
   - Apply patch & run tests (Docker)
   - Tests pass → create fix PR
4. **Database**: Review logged with status=fixed
5. **GitHub**: Comment posted on original PR with link to fix

### Cannot Fix

1. Same as above, but
2. **Agent**: Tests fail 3 times or GPT-4o returns CANNOT_FIX
3. **Database**: Review logged with status=cannot_fix
4. **GitHub**: Comment posted with failure details & suggestions

---

## Configuration Examples

### GitHub Token Scopes

```
repo (full control)
  └─ repo:status
  └─ repo_deployment
  └─ public_repo
  └─ repo:invite
```

### Webhook Events Subscribed

- `pull_request` (actions: opened, synchronize)

### Environment Variables

```bash
# Development
DATABASE_URL=sqlite:///./test.db
LOG_LEVEL=DEBUG

# Production
DATABASE_URL=postgresql://user:pass@db.example.com/code_review
LOG_LEVEL=INFO
DOCKER_HOST=unix:///var/run/docker.sock
```

---

## Error Handling

### Webhook Signature Validation

```python
def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Validates GitHub webhook signature using HMAC-SHA256.
    
    Returns: True if valid, False otherwise
    """
```

**Protection against**:
- Forged requests
- Man-in-the-middle attacks
- Replay attacks (checked by GitHub event ID)

### LLM Error Handling

- **Rate limit**: Retry with exponential backoff
- **API error**: Log to database, post comment
- **Invalid response**: Fallback to "CANNOT_FIX"

### Docker Error Handling

- **Container creation failed**: Log error, return to decide node
- **Test timeout**: Kill container after 30s
- **Out of memory**: Container killed, logged as test failure

---

## Monitoring Hooks

### Logging Points

```python
# Events logged (searchable in logs)
logger.info(f"Processing PR #{pr_number} in {repo}")
logger.info(f"Iteration {iteration}: {status}")
logger.warning(f"Test failed: {test_output}")
logger.error(f"API error: {error}")
```

### Metrics Exported

```python
# Available for monitoring systems (Prometheus, DataDog, etc.)
metrics = {
    "pr_processed": counter,
    "pr_fixed": counter,
    "tokens_used": gauge,
    "avg_cost": gauge,
    "fix_rate_percent": gauge,
    "avg_iterations": gauge,
    "latency_seconds": histogram,
}
```

---

## Rate Limits

- **GitHub API**: 5,000 requests/hour (per token)
- **OpenAI API**: Varies by model (GPT-4o Turbo: tokens/minute)
- **Agent Processing**: 1 PR at a time (queue for more)

---

## Example Integration

### Programmatic PR Processing

```python
from src.agent.graph import build_agent_graph
from src.agent.state import create_initial_state

# Build agent
agent = build_agent_graph()

# Create state for PR
state = create_initial_state(
    pr_number=123,
    repo_full_name="owner/repo",
    pr_title="Fix bug",
    pr_base_branch="main",
    raw_diff="...",
)

# Run agent
final_state = agent.invoke(state)

# Access results
print(f"Status: {final_state['final_status']}")
print(f"Fix PR: {final_state['fix_pr_url']}")
print(f"Cost: ${final_state['cost_usd']:.2f}")
```

---

## Troubleshooting

### Webhook not being received

**Check**:
1. Webhook URL is publicly accessible (not localhost)
2. Port 8000 is open
3. Firewall allows inbound HTTPS (443→8000)
4. GitHub webhook settings show successful deliveries

### GPT-4o calls failing

**Check**:
1. `OPENAI_API_KEY` is correct
2. Account has sufficient credits
3. Rate limit not exceeded (check in OpenAI dashboard)
4. API is not down (check status.openai.com)

### Tests not running in Docker

**Check**:
1. Docker daemon is running (`docker ps`)
2. `/var/run/docker.sock` is accessible
3. Repository has test files (pytest discovers them)
4. Test requirements are in requirements.txt

### Database errors

**Check**:
1. `DATABASE_URL` is correct
2. PostgreSQL is running (if used)
3. Credentials are correct
4. Network can reach database server


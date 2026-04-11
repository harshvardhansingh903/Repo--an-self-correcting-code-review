# Deployment Guide

## Quick Start

### Prerequisites
- Docker & Docker Compose (Dockerfile + full stack)
- Python 3.11+ (local development)
- PostgreSQL 14+ (production)
- GitHub personal access token
- OpenAI API key

### Configuration

1. **Create `.env` file**:
```bash
cp .env.example .env
```

2. **Configure credentials**:
```bash
# .env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
GITHUB_WEBHOOK_SECRET=your_webhook_secret
DATABASE_URL=postgresql://user:pass@localhost/code_review
DB_PASSWORD=your_db_password
```

### Local Development

**Option 1: Direct Python (SQLite)**
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from src.db.models import init_database; import asyncio; asyncio.run(init_database())"

# Run webhook server
python -m uvicorn src.webhook.handler:app --reload

# Server runs on http://localhost:8000
```

**Option 2: Docker (PostgreSQL)**
```bash
# Start full stack
docker-compose up -d

# Logs
docker-compose logs -f agent

# Stop
docker-compose down
```

---

## Production Deployment

### Using Deployment Script

```bash
# Make executable (Linux/macOS)
chmod +x deploy.sh

# Check prerequisites
./deploy.sh check

# Build images
./deploy.sh build

# Start in production
./deploy.sh start

# View status
./deploy.sh status

# Restart
./deploy.sh restart

# Stop all services
./deploy.sh stop
```

### Manual Docker Deployment

```bash
# Build image
docker build -t code-review-agent:latest .

# Run with environment
docker run -d \
  -p 8000:8000 \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e GITHUB_WEBHOOK_SECRET=$GITHUB_WEBHOOK_SECRET \
  -e DATABASE_URL=postgresql://user:pass@db:5432/code_review \
  -v /var/run/docker.sock:/var/run/docker.sock \
  code-review-agent:latest
```

### Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: code-review-agent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: code-review-agent
  template:
    metadata:
      labels:
        app: code-review-agent
    spec:
      containers:
      - name: agent
        image: code-review-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: code-review-secrets
              key: github-token
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: code-review-secrets
              key: openai-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: code-review-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: code-review-agent
spec:
  type: ClusterIP
  selector:
    app: code-review-agent
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
```

Deploy: `kubectl apply -f deployment.yaml`

---

## GitHub Webhook Setup

1. **Go to repository Settings → Webhooks**

2. **Add webhook**:
   - Payload URL: `https://your-domain.com/webhook/github`
   - Content type: `application/json`
   - Secret: (same as `GITHUB_WEBHOOK_SECRET`)
   - Events: `Pull requests` (only)
   - Active: ✓

3. **Webhook will trigger on**:
   - PR opened
   - PR synchronize (new commits)

---

## Monitoring & Logging

### View agent logs
```bash
docker-compose logs -f agent
```

### Logs include:
- Webhook received events
- PR processing status
- AST analysis details
- LLM API calls & costs
- Test execution results
- Database operations

### Health check
```bash
curl http://localhost:8000/health
# { "status": "ok", "service": "code-review-agent" }
```

### Database monitoring
```bash
# Connect to PostgreSQL
psql postgresql://reviewer:password@localhost/code_review

# Check reviews
SELECT * FROM review;

# Check iterations
SELECT * FROM iteration_record ORDER BY id DESC LIMIT 10;
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub personal access token (repo scope) |
| `OPENAI_API_KEY` | Yes | OpenAI API key (GPT-4o) |
| `GITHUB_WEBHOOK_SECRET` | Yes | Webhook signature secret |
| `DATABASE_URL` | Yes | Database connection string (defaults to SQLite) |
| `SERVER_HOST` | No | Bind address (default: 0.0.0.0) |
| `SERVER_PORT` | No | Port (default: 8000) |
| `LOG_LEVEL` | No | LOG_LEVEL (default: INFO) |
| `DOCKER_HOST` | No | Docker socket path (Unix: /var/run/docker.sock) |

---

## Resource Requirements

| Component | Min | Recommended |
|-----------|-----|-------------|
| CPU | 1 core | 2 cores |
| RAM | 512MB | 2GB |
| Storage | 500MB | 10GB |
| Network | 1 Mbps | 10 Mbps |

**Storage breakdown**:
- Application: 200MB
- PostgreSQL: 500MB (grows with reviews)
- Docker cache: 5GB per Python version tested

---

## Troubleshooting

### Agent won't start
```bash
# Check logs
docker-compose logs agent

# Common issues:
# - Missing OPENAI_API_KEY → add to .env
# - Database connection refused → check postgres is running
# - Docker socket permission denied → check docker group
```

### Webhook not triggering
```bash
# Check webhook history in GitHub repo settings
# Look for delivery failures → likely auth issue

# Test webhook signature:
python -c "
from src.utils.github_webhook import verify_webhook_signature
import json

payload = 'test'
signature = 'sha256=...'
secret = 'your_secret'

result = verify_webhook_signature(payload, signature, secret)
print(f'Valid: {result}')
"
```

### Database errors
```bash
# Reset database (development only!)
docker-compose exec agent python -c "
from src.db.models import Base, engine
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
"
```

### Tests failing
```bash
# Run tests
docker-compose exec agent pytest -v

# With coverage
docker-compose exec agent pytest --cov=src
```

---

## Performance Tuning

### Database Connection Pool
```python
# src/db/models.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,          # connections to keep alive
    max_overflow=10,       # extra connections allowed
    pool_recycle=3600,     # recycle every hour
)
```

### LLM API Rate Limiting
```python
# Rate limit to prevent quota exhaustion
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def call_gpt4o_for_review(state: AgentState):
    # ...
```

### Docker Optimization
```yaml
# docker-compose.yml
agent:
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 1G
      reservations:
        cpus: '0.5'
        memory: 512M
```

---

## Security Best Practices

✓ **Enabled**:
- HMAC-SHA256 webhook signature validation
- Secrets in environment variables (not in code)
- SQLAlchemy parameterized queries (SQL injection protection)
- Docker network isolation (no external network for tests)
- GitHub token scope restriction (repo access only)

✓ **Recommended**:
- Use GitHub Deploy Keys instead of Personal Token (repo-level access)
- Enable GitHub branch protection rules
- Run agent in separate container with limited privileges
- Rotate webhook secret quarterly
- Monitor API usage (OpenAI quota alerts)
- Use VPN/private network for production
- Enable HTTPS for webhook URL

---

## Cost Estimation

Costs per 1000 bugs analyzed:

| Component | Units | Cost |
|-----------|-------|------|
| OpenAI (GPT-4o) | ~500K tokens | $50-100 |
| AWS EC2 (t3.medium) | 30 days | $30 |
| RDS PostgreSQL | 30 days | $30 |
| GitHub API | Unlimited | $0 |
| **Total** | | **$110-160** |

---

## Backups & Recovery

### Database backup
```bash
# PostgreSQL
pg_dump -U reviewer -h localhost code_review > backup.sql

# Restore
psql -U reviewer -h localhost code_review < backup.sql
```

### Docker volume backup
```bash
docker-compose exec postgres pg_dump -U reviewer code_review | gzip > backup.sql.gz
```

---

## Scaling

### Horizontal scaling
```yaml
# docker-compose.yml (with reverse proxy)
services:
  agent-1: ...
  agent-2: ...
  agent-3: ...
  nginx:
    image: nginx:alpine
    ports: ["80:80"]
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
```

### Rate limiting with queue
```python
# Use Celery/RQ for job queue
import redis
from rq import Queue

redis_conn = redis.Redis()
q = Queue(connection=redis_conn)

# Queue jobs instead of processing immediately
job = q.enqueue(process_pr, pr_number, repo_name)
```

---

## Maintenance

### Regular tasks
- ✓ Monitor API usage (daily)
- ✓ Check logs (weekly)
- ✓ Backup database (weekly)
- ✓ Update dependencies (monthly)
- ✓ Review webhook failures (weekly)
- ✓ Rotate secrets (quarterly)

### Updates
```bash
# Update dependencies
pip install -r requirements.txt --upgrade

# Rebuild containers
docker-compose build --no-cache

# Restart
docker-compose restart
```


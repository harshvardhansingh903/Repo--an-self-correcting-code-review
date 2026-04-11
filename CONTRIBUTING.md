# Contributing Guide

## Setup for Development

### Prerequisites
- Python 3.11+
- Docker (for testing)
- PostgreSQL 14+ (recommended for production)

### Getting Started

```bash
# Clone repository
git clone https://github.com/yourusername/code-review-agent.git
cd code-review-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# GITHUB_TOKEN - create in GitHub Settings → Personal access tokens
# OPENAI_API_KEY - get from OpenAI platform
# GITHUB_WEBHOOK_SECRET - any random string, use in GitHub settings
```

### Running Tests

```bash
# All tests
pytest tests_*.py -v

# Specific component
pytest tests_graph.py -v

# With coverage
pytest tests_* --cov=src --cov-report=html
```

### Local Development

```bash
# Start webhook server
python -m uvicorn src.webhook.handler:app --reload

# Server runs on http://localhost:8000
# Health check: curl http://localhost:8000/health
```

### Docker Development

```bash
# Start full stack (agent + PostgreSQL)
docker-compose up -d

# View logs
docker-compose logs -f agent

# Stop everything
docker-compose down
```

## Development Workflow

### 1. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
git checkout -b fix/your-bug-fix
```

### 2. Make Changes
- Add tests first (TDD)
- Implement feature
- Keep commits atomic and descriptive

### 3. Run Tests
```bash
# Must pass all tests
pytest tests_*.py -v

# Check coverage
pytest --cov=src
```

### 4. Update Documentation
- Update README.md if adding features
- Update API.md if changing endpoints
- Add code comments for complex logic

### 5. Create Pull Request
- Clear description of changes
- Reference issues if applicable
- Ensure CI/CD passes

## Code Style

### Python
- Follow PEP 8
- Use type hints everywhere
- Docstrings for all public methods
- Max line length: 100 characters (soft limit)

### Example
```python
def process_pr(pr_number: int, repo_name: str) -> dict:
    """
    Process a GitHub PR.
    
    Args:
        pr_number: GitHub PR number
        repo_name: Repository full name (owner/repo)
    
    Returns:
        Dict with processing results
    """
    # Implementation
    pass
```

### Testing
- Write tests for new code
- Mock external APIs (don't call real ones)
- Aim for >90% coverage
- Use descriptive test names

## Project Structure

```
src/
├── agent/           # LangGraph agent
├── nodes/           # Individual workflow nodes
├── utils/           # Utilities (AST, Docker, LLM, GitHub)
├── db/              # Database models and operations
└── webhook/         # FastAPI server

tests/
├── tests_*.py       # Component tests

benchmark/
└── benchmark.py     # BugsInPy simulation

docs/
├── README.md        # Getting started
├── API.md           # API reference
├── DEPLOYMENT.md    # Production setup
└── DEVELOPMENT_NOTES.md  # Development journey
```

## Architecture Decisions

### Why LangGraph?
- Cleaner than manual state machines
- Built for agent workflows
- Type-safe state management

### Why TypedDict for State?
- Better IDE autocomplete
- Cleaner type hints
- More Pythonic than dataclasses for this use case

### Why Docker for Tests?
- Safety: untrusted code can't escape
- Isolation: no environment pollution
- Confidence: tests run identically on all machines

### Why SQLAlchemy ORM?
- Type hints support
- Migration friendly
- Query simplicity

## Common Issues

### Docker daemon not running
```bash
# Check if Docker is running
docker ps

# Start Docker Desktop or daemon
```

### GITHUB_TOKEN not set
```bash
# .env file not found or incomplete
# Make sure .env exists and has GITHUB_TOKEN
cat .env | grep GITHUB_TOKEN
```

### Tests hanging
```bash
# Some test might be waiting for API response
# Press Ctrl+C and check the logs
# All external APIs should be mocked
```

### Database errors
```bash
# Reset SQLite database
rm test.db
pytest tests_database.py -v

# For PostgreSQL, drop and recreate database
```

## Performance Profiling

```bash
# Profile test execution
pytest tests_graph.py --durations=10

# Profile specific function
python -m cProfile -s cumtime src/agent/graph.py
```

## Debugging

### Print debugging
```python
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Variable value: {value}")
```

### VS Code debugging
Add `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal"
        }
    ]
}
```

## Release Process

1. Update version in setup.py
2. Update CHANGELOG
3. Merge to main branch
4. Create GitHub release with tag
5. Deploy to production

## Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

## Questions?

Check existing issues or create a new one with:
- Description of feature/bug
- Steps to reproduce (if bug)
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)

## Code Review Checklist

Before submitting PR, check:
- [ ] Tests pass locally
- [ ] New code has tests
- [ ] No hardcoded secrets
- [ ] Type hints added
- [ ] Docstrings added
- [ ] No unused imports
- [ ] Follows code style
- [ ] README updated if needed
- [ ] No breaking changes documented

---

**Thanks for contributing! Every PR makes this better.** 🚀

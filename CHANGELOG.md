# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-11

### Added
- **Core Agent**: LangGraph-based state machine with 7 nodes
- **AST Analysis**: Python code parsing with function/class extraction
- **Docker Sandbox**: Isolated container execution with resource limits (512MB, 30s timeout)
- **LLM Integration**: GPT-4o with context passing for self-correcting fixes
- **GitHub Integration**: Webhook receiver and PyGithub wrapper for PR management
- **Database Layer**: SQLAlchemy ORM for review and iteration tracking
- **API Server**: FastAPI webhook endpoint with signature validation
- **Testing**: 58 unit and integration tests (100% passing)
- **Deployment**: Docker, docker-compose, GitHub Actions CI/CD
- **Documentation**: README, API reference, deployment guide, development notes

### Fixed
- Docker network isolation (was allowing external connections, now uses network_mode='none')
- LLM context formatting (JSON structure was causing confusion, simplified to text)
- Database schema (added IterationRecord table for better iteration tracking)
- Cost tracking (wasn't accurate, now logs tokens and estimated cost per attempt)

### Changed
- Reduced max retries from 5 to 3 (cost optimization)
- Consolidated 9 nodes to 7 (cleaner architecture)
- TypedDict for state instead of dataclass (better IDE support)
- SQLite default for development (was forcing PostgreSQL setup)

### Performance
- AST parsing: ~50ms per file
- Docker container creation: ~500ms
- Test execution: ~2s average
- GPT-4o call: ~3-5s average
- E2E fix attempt: ~15s

---

## Development Plan for Future

### Planned (Next Release)
- [ ] Job queue system (Redis + Celery)
- [ ] Multi-model LLM support (Claude, open-source)
- [ ] Language support beyond Python
- [ ] Slack notifications
- [ ] Real BugsInPy dataset integration
- [ ] Web dashboard for metrics
- [ ] Prometheus metrics export

### Considered
- [ ] Pre-commit hook integration
- [ ] GitHub Actions bot for on-demand fixes
- [ ] GitLab/Gitea support
- [ ] Machine learning predictability model
- [ ] API rate limiting and quota management
- [ ] Multi-tenant support

### Won't Implement
- [ ] IDE plugins (out of scope)
- [ ] Merge authority (human approval always required)
- [ ] Static analysis replacement (tests-only approach)

---

## Known Issues

### Open
- #1: Container sometimes hangs on network-heavy tests (rare, reset fixes)
- #2: GPT-4o inconsistent with very large diffs (>10KB)

### Resolved
- ✅ Docker OOMKilled without clear error (fixed with better logging)
- ✅ TypedDict validation at runtime (switched to runtime validation)
- ✅ GitHub token leaking in logs (sanitized all API calls)

---

## Upgrading

### From 0.x to 1.0
No breaking changes. Just update and restart.

```bash
git pull origin main
pip install -r requirements.txt
docker-compose down && docker-compose up -d
```

---

## Security

All releases are signed. Verify with:
```bash
git verify-tag v1.0.0
```

---

## Support

- 📖 See [README.md](README.md) for setup
- 🛠️ See [DEPLOYMENT.md](DEPLOYMENT.md) for production
- 💻 See [API.md](API.md) for API reference
- 📝 See [DEVELOPMENT_NOTES.md](DEVELOPMENT_NOTES.md) for architecture

---

## Contributors

- Lead Developer: You (@yourusername)
- AI Assistance: GitHub Copilot, Claude
- Thanks to: LangGraph, FastAPI, and open-source communities


# Development Notes

## Project Journey

### Initial Design (Week 1)
Started with 9 nodes but realized after implementation that some could be consolidated.
Final design: 7 nodes with cleaner separation of concerns.

**Key design decisions:**
- **TypedDict vs dataclass**: Went with TypedDict for state after trying dataclass first. TypedDict has better IDE support and type hints are cleaner.
- **SQLite first, PostgreSQL later**: Started with SQLite for dev, added PostgreSQL support later for production. Good decision—kept things simple early.
- **Docker isolation**: Spent a lot of time on this. Tried network_mode='bridge' first but that was a security risk. network_mode='none' solved it.

### LLM Integration (Week 2)
**Trial 1**: Passing entire AST as JSON  
**Result**: GPT-4o got confused with nested structures  
**Trial 2**: Simplified to formatted text blocks  
**Result**: Much better! GPT-4o understood context better

**Lesson**: Sometimes less structured data works better with LLMs. Counterintuitive.

### Cost Investigation
Initial idea: Max 5 retries to get perfect fix  
**Problem**: Too expensive! ($0.30+ per bug)  
**Solution**: Reduced to max 3 retries  
**Result**: 80% of fixes still happen on first or second attempt, saves money

### Testing Strategy (Week 3)
Started with integration tests that called real GPT-4o API.  
**Problem**: Expensive, slow, unreliable  
**Solution**: Switched to mocking  
**Benefit**: Tests now run in <15 seconds, no API calls, deterministic

**What I mock:**
- OpenAI API (always return valid patch)
- GitHub API (always return mock PR)
- Docker API (verify calls but don't create containers)

### Database Design
**V1**: Single Review table  
**Problem**: Hard to track individual iteration details  
**V2**: Review + IterationRecord (1:many)  
**Benefit**: Better analytics, can see each attempt's patches and outputs

### Deployment Journey
**Local**: SQLite + uvicorn (works great for dev)  
**Docker**: Added docker-compose for full stack testing  
**Kubernetes**: Set up YAML for production (not tested yet)

## Known Limitations

1. **Single-threaded**: Processes one PR at a time. Need job queue for scale.
2. **Python-only**: AST parser only works for Python. Could abstract to support other languages.
3. **Test-based**: Only fixes bugs that have failing tests. Doesn't handle style/convention issues.
4. **GPT-4o cost**: Expensive for large-scale deployment. Would need model selection strategy.

## If I Were to Rewrite

1. **Add Celery/RQ**: Proper background job processing
2. **Caching layer**: Cache AST analysis for unchanged files
3. **Model selection**: Support Claude, open-source models for cost optimization
4. **Type stub support**: Use .pyi files for better type information
5. **Language plugins**: Plugin system for Java, Go, TypeScript
6. **Real BugsInPy dataset**: Test against actual bugs instead of simulated

## Performance Notes

- AST parsing: ~50ms per file
- docker creation: ~500ms
- docker test execution: ~2s avg
- GPT-4o call: ~3-5s avg
- E2E fix attempt: ~15s

Bottleneck: GPT-4o API latency. Would be better if they offered streaming.

## Debugging Notes

**Hard to debug issue**: Container resource limits silent-fail  
Container would just get OOMKilled without clear error. Took hours to track down.  
Solution: Always log before and after Docker operations.

**Testing Docker without Docker**: Used unittest.mock to mock Docker SDK.  
Makes tests fast but loses real container verification. Trade-off is worth it.

**GitHub API token**: Easy to forget GITHUB_TOKEN in .env  
Solution: Added check in GitHubClient.__init__ that raises ValueError immediately.

## Future Ideas

- [ ] Real-time webhook retry with exponential backoff
- [ ] Slack notifications when fix created
- [ ] Web dashboard showing fix rate trends
- [ ] Integration with pre-commit hooks
- [ ] GitHub bot commands (e.g., `@CodeFixBot fix this`)
- [ ] Support for multiple code hosts (GitLab, Gitea)
- [ ] Machine learning to predict fixability before calling LLM

## Team Notes

If someone else is going to work on this:
1. Make sure docker is running (docker ps should work)
2. .env file is required with GITHUB_TOKEN and OPENAI_API_KEY
3. Tests run in <15s, so they should all pass quickly
4. Database defaults to SQLite (test.db) if DATABASE_URL not set
5. See README for setup, API.md for endpoint docs

## Lessons Learned

1. **State machines are great**: LangGraph makes complex flows simple
2. **Test-driven fixes work**: AI generated patches only trusted if tests pass
3. **Isolation is security**: Docker costs more but worth it for untrusted code
4. **Cost matters**: Need to track token usage and cost per fix from day 1
5. **Mocking external APIs saves $$$**: Don't test against real APIs in CI
6. **TypedDict > dataclass for state**: Better IDE support
7. **Async first**: Async/await should be default in Python, not afterthought
8. **Documentation pays dividends**: Good docs prevent bugs later

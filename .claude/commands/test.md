---
name: test
description: Run tests with coverage verification
---

# Test Command

Run tests for a module or the entire project with coverage requirements.

## Usage

```
/test [module-name]
```

## What This Does

1. **Run tests** for specified module or all modules
2. **Check coverage** (minimum 80%)
3. **Report failures** with actionable feedback
4. **Verify mocks** for external APIs (asyncpg, litellm, httpx)

## Implementation

### Single Module

```bash
# Run routing tests
pytest bsgateway/tests/test_hook.py --cov=bsgateway.routing --cov-report=term-missing

# Run collector tests
pytest bsgateway/tests/test_collector.py --cov=bsgateway.routing.collector --cov-report=term-missing

# Run classifier tests
pytest bsgateway/tests/test_classifiers.py --cov=bsgateway.routing.classifiers --cov-report=term-missing
```

### All Modules

```bash
# Run all tests with coverage
pytest bsgateway/tests/ --cov=bsgateway --cov-report=term-missing --cov-fail-under=80
```

### With Lint

```bash
# Code quality + tests
ruff check bsgateway/ && pytest bsgateway/tests/ --cov=bsgateway --cov-fail-under=80
```

## Coverage Requirements

- **All modules**: >= 80%
- **Core modules** (config, logging): >= 90%
- **Routing** (hook, classifiers, collector, models): >= 80%

## Mock Verification

Ensure all external APIs are mocked:

```bash
# Check for unmocked API calls (should be empty in test code)
grep -r "asyncpg\.create_pool\b" bsgateway/ | grep -v "test\|collector.py"
grep -r "litellm\.acompletion\b" bsgateway/ | grep -v "test\|llm.py"
```

## Output

The command should report:
- Tests passed/failed
- Coverage percentage per module
- Uncovered lines
- Missing mocks (if any real API calls found)

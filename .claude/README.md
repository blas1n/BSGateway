# Claude Code Configuration

BSGateway Claude Code setup for development workflow.

## Structure

```
.claude/
├── README.md           # This file
├── rules/              # Always-enforced guidelines
│   ├── architecture.md # Core architectural decisions
│   ├── testing.md      # Test requirements (80%+ coverage)
│   └── security.md     # Credential and data security
└── commands/           # Slash commands
    └── test.md         # /test - run tests with coverage
```

## Rules

Always-enforced guidelines checked before every implementation:

- **architecture.md**: Python 3.11+, uv, pydantic-settings, structlog, async, dataclasses
- **testing.md**: All code must have tests (>= 80% coverage), mock all external APIs
- **security.md**: No hardcoded credentials, no secrets in logs

## Commands

- `/test [module]`: Run tests with coverage verification

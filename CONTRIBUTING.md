# Contributing to OfficePilot AI

We welcome contributions from the community! Here's how to get started.

## Code of Conduct

This project adheres to our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold it.

## How to Contribute

### 1. Report Bugs

Open a [GitHub Issue](https://github.com/csmimrankhan/officepilot/issues/new?template=bug_report.md) with:
- A clear title and description
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable
- Environment details (OS, app version)

### 2. Suggest Features

Open a [Feature Request](https://github.com/csmimrankhan/officepilot/issues/new?template=feature_request.md) with:
- The problem you're solving
- Your proposed solution
- Any alternatives you've considered

### 3. Submit Code

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes** following our conventions
4. **Run tests**: `cd backend && python -m pytest -q` and `cd frontend && npm test -- --run`
5. **Commit**: Use clear commit messages
6. **Push**: `git push origin feature/your-feature-name`
7. **Open a Pull Request**

## Development Setup

See [BUILD.md](BUILD.md) for detailed setup instructions.

Quick start:
```bash
cd backend && pip install -r requirements.txt && python -m uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

## Coding Conventions

- **Python**: Follow PEP 8. Use type hints. FastAPI + SQLAlchemy conventions.
- **JavaScript/JSX**: Follow the existing React pattern (functional components, hooks).
- **Rust**: Follow Tauri 2 conventions and Rust idioms.
- **No emojis in code or UI** unless user explicitly requests them.
- **No inline comments** explaining "what" the code does (use them only for "why").
- **Security-first**: Never log or expose secrets. Use the audit logger for state changes.
- **Sensitive values** (passwords, tokens, OTP, CVV, PIN, SSN) must be redacted in all output.
- **All mutating operations** must create audit log entries.

## Pull Request Process

1. Ensure all tests pass.
2. Update documentation if needed.
3. Add tests for new functionality.
4. PRs require at least one review.
5. Maintain linear history (rebase before merge).

## Questions?

Open a [Discussion](https://github.com/csmimrankhan/officepilot/discussions) or reach out via GitHub Issues.

Thank you for contributing!

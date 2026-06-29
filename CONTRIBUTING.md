# Contributing to NoPush

Thank you for your interest in contributing to NoPush! This guide will help you
get started.

## Development Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/saransh-kaushik/nopush.git
   cd nopush
   ```

2. **Create a virtual environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # .venv\Scripts\activate   # Windows
   ```

3. **Install in development mode:**

   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks:**

   ```bash
   pre-commit install
   ```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=nopush --cov-report=term-missing

# Run a specific test file
pytest tests/test_git/test_diff_parser.py

# Skip slow/integration tests
pytest -m "not slow and not integration"
```

## Code Quality

We use the following tools to maintain code quality:

- **[Ruff](https://docs.astral.sh/ruff/)** for linting and formatting
- **[Mypy](https://mypy-lang.org/)** for static type checking
- **[Pytest](https://docs.pytest.org/)** for testing

```bash
# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Type check
mypy src/nopush/
```

## Code Style

- Use type annotations on all public functions and methods.
- Write docstrings for all public classes, methods, and functions (Google style).
- Keep functions focused — prefer small, single-purpose functions.
- Use `from __future__ import annotations` in every module.
- Prefer composition over inheritance.

## Adding a New LLM Provider

1. Create a new file in `src/nopush/providers/` (e.g. `my_provider.py`).
2. Subclass `LLMProvider` and implement the `complete()` method.
3. Register your provider in `src/nopush/providers/registry.py`.
4. Add tests in `tests/test_providers/`.
5. Update `src/nopush/config/constants.py` with the provider name.

## Pull Request Guidelines

- **One feature per PR.** Keep changes focused and reviewable.
- **Write tests.** All new functionality should have corresponding tests.
- **Update documentation.** If your change affects the user-facing API or CLI,
  update the README or relevant docs.
- **Follow conventional commits.** Use prefixes like `feat:`, `fix:`, `docs:`,
  `test:`, `refactor:`, `chore:`.
- **Ensure CI passes.** All checks (lint, type, test) must be green.

## Reporting Issues

When filing a bug report, please include:

- NoPush version (`nopush --version`)
- Python version (`python --version`)
- Operating system
- Steps to reproduce
- Expected vs actual behaviour
- Relevant error output or logs

## License

By contributing, you agree that your contributions will be licensed under the
MIT License.

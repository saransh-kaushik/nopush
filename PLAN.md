# NoPush — Phase 1 Implementation Plan

> This document breaks down each step of the Phase 1 roadmap into concrete
> implementation tasks with files, purpose, and architectural rationale.

---

## Technology Decisions

| Concern              | Choice                | Rationale                                                                 |
| -------------------- | --------------------- | ------------------------------------------------------------------------- |
| Python version       | ≥ 3.10                | Broad compatibility while using modern syntax (`match`, `\|` unions)      |
| Package layout       | `src/` layout         | Prevents accidental imports from the working directory during development |
| Build system         | `hatchling`           | Modern, PEP 621-compliant, zero-config for most cases                    |
| CLI framework        | `typer`               | Type-hint-driven, auto-generated help, built on Click                    |
| Terminal rendering   | `rich`                | Beautiful tables, panels, syntax highlighting, spinners                  |
| Data models          | `pydantic` v2         | Validation, serialization, structured LLM output parsing                 |
| Configuration        | `pyyaml`              | Human-readable config files (`nopush.yaml`)                              |
| HTTP client          | `httpx`               | Modern async/sync HTTP, timeout support, streaming                       |
| Git operations       | `subprocess` (stdlib) | Zero dependency, full control, no GitPython bloat                        |
| Testing              | `pytest`              | Industry standard, rich plugin ecosystem                                 |
| Linting / Formatting | `ruff`                | Fast, replaces flake8 + isort + black in one tool                        |
| Type checking        | `mypy`                | Static type safety for a public API                                      |

---

## Project Structure (Final)

```
nopush-ai/
├── .github/
│   └── workflows/
│       └── ci.yml                      # CI: lint, type-check, test
├── src/
│   └── nopush/
│       ├── __init__.py                 # Package version + public API
│       ├── __main__.py                 # `python -m nopush` entry point
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── app.py                  # Typer app, top-level CLI wiring
│       │   ├── commands/
│       │   │   ├── __init__.py
│       │   │   ├── init_cmd.py         # `nopush init` command
│       │   │   └── review_cmd.py       # `nopush review` command
│       │   └── renderer.py            # Rich-based terminal output
│       ├── config/
│       │   ├── __init__.py
│       │   ├── constants.py            # Default values, paths, env vars
│       │   ├── manager.py              # Load / save / merge config
│       │   └── schema.py              # Pydantic models for configuration
│       ├── git/
│       │   ├── __init__.py
│       │   ├── diff_parser.py          # Parse `git diff` output
│       │   └── models.py              # FileDiff, HunkChange data models
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py                 # Abstract LLMProvider interface
│       │   ├── registry.py             # Provider discovery & instantiation
│       │   ├── openai.py               # OpenAI / Azure OpenAI provider
│       │   ├── anthropic.py            # Anthropic Claude provider (stub)
│       │   └── gemini.py               # Google Gemini provider (stub)
│       ├── prompts/
│       │   ├── __init__.py
│       │   ├── builder.py              # Assemble final prompt from parts
│       │   └── templates.py            # System & user prompt templates
│       ├── review/
│       │   ├── __init__.py
│       │   ├── engine.py               # Orchestrates the full review flow
│       │   └── models.py              # ReviewComment, ReviewResult models
│       └── github/
│           ├── __init__.py
│           └── commenter.py            # Post comments to GitHub PRs
├── tests/
│   ├── __init__.py
│   ├── conftest.py                     # Shared fixtures
│   ├── test_cli/
│   │   ├── __init__.py
│   │   └── test_commands.py
│   ├── test_config/
│   │   ├── __init__.py
│   │   └── test_manager.py
│   ├── test_git/
│   │   ├── __init__.py
│   │   └── test_diff_parser.py
│   ├── test_providers/
│   │   ├── __init__.py
│   │   └── test_openai.py
│   ├── test_prompts/
│   │   ├── __init__.py
│   │   └── test_builder.py
│   └── test_review/
│       ├── __init__.py
│       └── test_engine.py
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml                      # Build config, dependencies, scripts
├── LICENSE
├── README.md
├── PHASE1.md
├── PLAN.md
├── CONTRIBUTING.md
└── CHANGELOG.md
```

---

## Step-by-Step Breakdown

---

### Step 1 — CLI Setup

> Create the `nopush` CLI with commands like `nopush init` and `nopush review`.

**Files created:**

| File                                    | Purpose                                                       |
| --------------------------------------- | ------------------------------------------------------------- |
| `pyproject.toml`                        | Declares the `nopush` console script entry point and metadata |
| `src/nopush/__init__.py`                | Package root — exposes `__version__`                          |
| `src/nopush/__main__.py`                | Enables `python -m nopush` invocation                         |
| `src/nopush/cli/__init__.py`            | CLI subpackage init                                           |
| `src/nopush/cli/app.py`                | Creates the Typer application and registers sub-commands      |
| `src/nopush/cli/commands/__init__.py`   | Commands subpackage init                                      |
| `src/nopush/cli/commands/init_cmd.py`   | Placeholder for `nopush init` — prints "coming soon"          |
| `src/nopush/cli/commands/review_cmd.py` | Placeholder for `nopush review` — prints "coming soon"        |

**Key decisions:**

- Use `typer` for the CLI. It generates help text from type hints and docstrings automatically, which means excellent `--help` output with zero extra work.
- The entry point is declared in `pyproject.toml` under `[project.scripts]`, so after `pip install .` the `nopush` command is available system-wide.
- File is named `init_cmd.py` (not `init.py`) to avoid shadowing Python's built-in.

**Dependencies introduced:** `typer[all]` (includes `rich` and `shellingham`)

**Acceptance criteria:**

- `pip install -e .` succeeds
- `nopush --help` shows the available commands
- `nopush init` and `nopush review` execute without error

---

### Step 2 — BYOK (Bring Your Own Key) Support

> Allow users to configure their own API keys and preferred AI model locally.

**Files created:**

| File                             | Purpose                                                              |
| -------------------------------- | -------------------------------------------------------------------- |
| `src/nopush/config/__init__.py`  | Config subpackage init                                               |
| `src/nopush/config/constants.py` | Default paths (`~/.nopush/`), env var names, default model settings |
| `src/nopush/config/schema.py`   | Pydantic models: `NoPushConfig`, `ProviderConfig`                    |
| `src/nopush/config/manager.py`  | `ConfigManager` class — load, save, merge config from YAML + env     |

**Files modified:**

| File                                    | Change                                                     |
| --------------------------------------- | ---------------------------------------------------------- |
| `src/nopush/cli/commands/init_cmd.py`   | Interactive prompts to collect provider, API key, and model |

**Key decisions:**

- API keys are stored in `~/.nopush/credentials.yaml` (user-level), separate from project config (`nopush.yaml`). This prevents accidental commits.
- Config resolution order: CLI flags → environment variables → project `nopush.yaml` → user `~/.nopush/config.yaml` → defaults. Later sources are overridden by earlier ones.
- Pydantic v2 validators ensure keys are non-empty, models are in known lists, etc.

**Dependencies introduced:** `pydantic` v2, `pyyaml`

**Acceptance criteria:**

- `nopush init` walks the user through setup interactively
- Credentials are saved to `~/.nopush/credentials.yaml`
- Config is loadable and validated on next run

---

### Step 3 — Git Diff Parser

> Read staged changes, a Git diff, or specific files to review.

**Files created:**

| File                             | Purpose                                                          |
| -------------------------------- | ---------------------------------------------------------------- |
| `src/nopush/git/__init__.py`     | Git subpackage init                                              |
| `src/nopush/git/models.py`      | Data models: `FileDiff`, `Hunk`, `HunkLine`                     |
| `src/nopush/git/diff_parser.py` | Functions to run `git diff --staged`, parse unified diff output  |

**Key decisions:**

- Use `subprocess.run(["git", "diff", ...])` — no dependency on GitPython.
- Parse the standard unified diff format. Each `FileDiff` contains file paths and a list of `Hunk` objects. Each `Hunk` contains line-level changes with context.
- Support three modes: staged changes (default), arbitrary diff between commits, and explicit file paths.
- Respect `.gitignore` and the user's `ignore` list from config.

**Dependencies introduced:** None (stdlib only)

**Acceptance criteria:**

- Parses staged changes from a real git repo
- Returns structured `FileDiff` objects
- Handles renames, new files, deleted files, and binary files gracefully

---

### Step 4 — Prompt Builder

> Convert code changes into a structured prompt for the LLM.

**Files created:**

| File                              | Purpose                                                    |
| --------------------------------- | ---------------------------------------------------------- |
| `src/nopush/prompts/__init__.py`  | Prompts subpackage init                                    |
| `src/nopush/prompts/templates.py` | System prompt and user prompt templates as string constants |
| `src/nopush/prompts/builder.py`   | `PromptBuilder` — assembles messages from diffs + config   |

**Key decisions:**

- The system prompt instructs the LLM to act as a senior code reviewer and return structured JSON output matching our `ReviewComment` schema.
- Each `FileDiff` is formatted into a clearly delimited block in the user message, with file path, language (inferred from extension), and the diff content.
- Large diffs are chunked to stay within context window limits. The builder tracks token estimates and splits if needed.
- The prompt explicitly asks for: severity (critical / warning / suggestion / nitpick), file, line number, explanation, and suggested fix.

**Dependencies introduced:** None

**Acceptance criteria:**

- Produces well-structured messages from a list of `FileDiff` objects
- Handles empty diffs gracefully
- Truncates/chunks oversized diffs with clear boundaries

---

### Step 5 — LLM Provider Layer

> Implement a common interface for AI providers (OpenAI first, others later).

**Files created:**

| File                                | Purpose                                                    |
| ----------------------------------- | ---------------------------------------------------------- |
| `src/nopush/providers/__init__.py`  | Providers subpackage init                                  |
| `src/nopush/providers/base.py`     | `LLMProvider` abstract base class with `complete()` method  |
| `src/nopush/providers/registry.py` | `ProviderRegistry` — maps provider names to classes         |
| `src/nopush/providers/openai.py`   | `OpenAIProvider` — full implementation using httpx          |
| `src/nopush/providers/anthropic.py`| `AnthropicProvider` — stub for Phase 1                      |
| `src/nopush/providers/gemini.py`   | `GeminiProvider` — stub for Phase 1                         |

**Key decisions:**

- The abstract interface defines `complete(messages: list[Message]) -> str` — simple and provider-agnostic.
- OpenAI implementation uses `httpx` directly (not the `openai` SDK) to minimize dependencies and give us full control over retries, timeouts, and error handling.
- Providers are registered by name in a registry dict. Adding a new provider is just: write a class, register it.
- Error handling includes: rate limiting (retry with backoff), auth failures (clear message), network errors, and malformed responses.

**Dependencies introduced:** `httpx`

**Acceptance criteria:**

- `OpenAIProvider` can send a prompt and receive a completion
- Provider is instantiated from config automatically
- Clear error messages for invalid API keys, network issues, etc.

---

### Step 6 — Review Engine

> Generate structured review comments with severity, file, line number, explanation, and suggestion.

**Files created:**

| File                             | Purpose                                                     |
| -------------------------------- | ----------------------------------------------------------- |
| `src/nopush/review/__init__.py`  | Review subpackage init                                      |
| `src/nopush/review/models.py`   | `ReviewComment`, `ReviewResult`, `Severity` enum             |
| `src/nopush/review/engine.py`   | `ReviewEngine` — orchestrates diff → prompt → LLM → parse   |

**Key decisions:**

- `ReviewEngine` is the main orchestrator. It:
  1. Gets diffs from the git parser
  2. Builds prompts via the prompt builder
  3. Sends prompts to the LLM provider
  4. Parses the JSON response into `ReviewComment` objects
- Response parsing is fault-tolerant: if the LLM returns slightly malformed JSON, we attempt repair (strip markdown fences, fix trailing commas) before failing.
- Each `ReviewComment` contains: `severity`, `file_path`, `line_number`, `title`, `explanation`, `suggestion` (optional code block).
- The engine validates that referenced files and line numbers actually exist in the diff, discarding hallucinated references.

**Dependencies introduced:** None (uses existing packages)

**Acceptance criteria:**

- End-to-end: staged changes → structured review comments
- Handles LLM response parsing errors gracefully
- Returns an empty review (not an error) when there are no issues

---

### Step 7 — Terminal Output

> Display clean, colorized review results directly in the terminal.

**Files created:**

| File                          | Purpose                                              |
| ----------------------------- | ---------------------------------------------------- |
| `src/nopush/cli/renderer.py` | `ReviewRenderer` — formats and prints review output   |

**Files modified:**

| File                                      | Change                                        |
| ----------------------------------------- | --------------------------------------------- |
| `src/nopush/cli/commands/review_cmd.py`   | Wires up the full review pipeline + renderer  |

**Key decisions:**

- Use `rich` for all terminal output: `Panel`, `Table`, `Syntax`, `Console`.
- Severity levels are color-coded: 🔴 critical (red), 🟡 warning (yellow), 🔵 suggestion (blue), ⚪ nitpick (dim).
- Code suggestions are rendered with syntax highlighting using `rich.syntax.Syntax`.
- A summary header shows total issues by severity.
- A spinner (`rich.status`) is displayed while waiting for the LLM response.
- If no issues are found, display a congratulatory message.

**Dependencies introduced:** None (`rich` already included via `typer[all]`)

**Acceptance criteria:**

- Review output is readable, colorized, and well-structured
- Severity levels are visually distinct
- Code suggestions have syntax highlighting
- Works correctly in terminals with and without color support

---

### Step 8 — GitHub PR Comments _(Optional)_

> Post generated review comments to GitHub pull requests.

**Files created:**

| File                              | Purpose                                              |
| --------------------------------- | ---------------------------------------------------- |
| `src/nopush/github/__init__.py`   | GitHub subpackage init                               |
| `src/nopush/github/commenter.py` | `PRCommenter` — posts review comments via GitHub API  |

**Files modified:**

| File                                      | Change                                            |
| ----------------------------------------- | ------------------------------------------------- |
| `src/nopush/cli/commands/review_cmd.py`   | Add `--pr` flag to optionally post to a GitHub PR |
| `src/nopush/config/schema.py`             | Add GitHub token field to config                  |

**Key decisions:**

- Uses the GitHub REST API v3 — no dependency on PyGitHub.
- Creates PR review comments (not issue comments) so they appear inline on the diff.
- Requires a `GITHUB_TOKEN` env var or config entry.
- This step is optional and can be skipped in Phase 1 if time is tight.

**Dependencies introduced:** None (`httpx` already present)

**Acceptance criteria:**

- `nopush review --pr <url>` posts comments to the PR
- Comments appear as inline review comments on the correct lines
- Works with GitHub personal access tokens

---

### Step 9 — Configuration System

> Support project configuration (`nopush.yaml`).

**Files modified:**

| File                             | Change                                                            |
| -------------------------------- | ----------------------------------------------------------------- |
| `src/nopush/config/schema.py`   | Add fields: `ignore`, `review_depth`, `max_files`, custom rules   |
| `src/nopush/config/manager.py`  | Add project-level config discovery (walk up to find `nopush.yaml`)|
| `src/nopush/git/diff_parser.py` | Respect `ignore` patterns from config                             |
| `src/nopush/prompts/builder.py` | Adjust prompt detail based on `review_depth`                      |

**Key decisions:**

- Config discovery walks up from CWD to find the nearest `nopush.yaml`, similar to how `.gitignore` works.
- Three review depths: `minimal` (only critical issues), `standard` (default), `thorough` (deep review with style suggestions).
- Ignore patterns use gitignore-style glob syntax via `pathlib.PurePath.match()`.
- The full resolved config can be dumped with `nopush config show` for debugging.

**Dependencies introduced:** None

**Acceptance criteria:**

- `nopush.yaml` in the project root is auto-discovered and loaded
- Ignore patterns correctly exclude files from review
- Review depth affects the prompt and output

---

### Step 10 — Packaging & Publishing

> Publish the project as a Python package (`pip install nopush`).

**Files created / modified:**

| File                        | Purpose                                                |
| --------------------------- | ------------------------------------------------------ |
| `pyproject.toml`            | Final metadata: classifiers, URLs, license, readme     |
| `.github/workflows/ci.yml` | CI pipeline: lint, type-check, test on multiple Pythons|
| `.pre-commit-config.yaml`  | Pre-commit hooks: ruff, mypy                           |
| `CONTRIBUTING.md`           | Contribution guidelines for the open-source community  |
| `CHANGELOG.md`              | Version history following Keep a Changelog format      |

**Key decisions:**

- Publish to PyPI under the name `nopush`.
- CI runs on Python 3.10, 3.11, 3.12, and 3.13.
- Ruff is configured in `pyproject.toml` for linting and formatting rules.
- The `CONTRIBUTING.md` covers: setting up a dev environment, running tests, code style, and PR guidelines.

**Dependencies introduced:** Dev dependencies — `pytest`, `pytest-cov`, `ruff`, `mypy`

**Acceptance criteria:**

- `pip install nopush` works from PyPI
- CI passes on all supported Python versions
- Contributing guide is clear and complete

---

## Implementation Order

The steps are designed to be implemented sequentially. Each step builds on the previous:

```
Step 1 (CLI) → Step 2 (Config/BYOK) → Step 3 (Git) → Step 4 (Prompts)
    → Step 5 (Providers) → Step 6 (Review Engine) → Step 7 (Terminal Output)
    → Step 8 (GitHub PR, optional) → Step 9 (Config refinement) → Step 10 (Packaging)
```

After each step, the project should remain installable and runnable — no step should
leave the project in a broken state.

---

## Dependency Summary

### Runtime

| Package    | Version  | Purpose                  |
| ---------- | -------- | ------------------------ |
| `typer`    | ≥ 0.15.0 | CLI framework            |
| `rich`     | ≥ 13.0.0 | Terminal formatting      |
| `pydantic` | ≥ 2.0.0  | Data validation & models |
| `pyyaml`   | ≥ 6.0.0  | YAML config parsing      |
| `httpx`    | ≥ 0.27.0 | HTTP client for LLM APIs |

### Development

| Package      | Version  | Purpose              |
| ------------ | -------- | -------------------- |
| `pytest`     | ≥ 8.0.0  | Testing              |
| `pytest-cov` | ≥ 5.0.0  | Coverage reporting   |
| `ruff`       | ≥ 0.8.0  | Linting & formatting |
| `mypy`       | ≥ 1.13.0 | Static type checking |

## NoPush — File-by-File Breakdown

### Core Package (`src/nopush/`)

| File          | What & Why                                                             |
| ------------- | ---------------------------------------------------------------------- |
| `__init__.py` | Exposes `__version__`. Single source of truth for the package version. |
| `__main__.py` | Enables `python -m nopush`. Just calls the CLI app.                    |

### CLI (`cli/`)

| File                     | What & Why                                                                                                                                                                          |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app.py`                 | Wires the Typer CLI app — registers `init` and `review` commands, handles `--version` flag. This is the entry point.                                                                |
| `commands/init_cmd.py`   | `nopush init` — walks users through API key + model setup interactively. Saves credentials to `~/.nopush/credentials.yaml`.                                                        |
| `commands/review_cmd.py` | `nopush review` — orchestrates the full review pipeline: config → diffs → prompts → LLM → parse → render. Supports `--depth`, `--provider`, `--model`, `--max-files` CLI options. |
| `renderer.py`            | Takes a `ReviewResult` and renders it beautifully in the terminal using Rich (panels, colors, syntax highlighting, severity emojis, summary header).                                |

### Config (`config/`)

| File           | What & Why                                                                                                                                         |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `constants.py` | All magic values in one place — file paths (`~/.nopush/`), env var names, defaults, supported providers.                                           |
| `schema.py`    | Pydantic models defining the shape of config (`NoPushConfig`) and credentials (`ProviderCredentials`). Validates everything.                       |
| `manager.py`   | Loads and merges config from 5 layers: CLI flags > env vars > project YAML > user YAML > defaults. Also saves credentials with `0600` permissions. |

### Git (`git/`)

| File             | What & Why                                                                                                                                                           |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `models.py`      | Data models — `FileDiff` (one file's changes), `Hunk` (a block of changes), `HunkLine` (a single line). Gives structure to raw diffs.                                |
| `diff_parser.py` | Runs `git diff --staged` via subprocess, parses the unified diff format into those models. Also handles language detection from file extensions and ignore patterns. |

### Providers (`providers/`)

| File           | What & Why                                                                                                                                                                             |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `base.py`      | Abstract `LLMProvider` interface — just one method: `complete(messages) → str`. Also defines the exception hierarchy (`ProviderError`, `ProviderAuthError`, `ProviderRateLimitError`). |
| `registry.py`  | Maps provider names (`"openai"`, `"gemini"`) to their classes. Lazy-imports them so unused providers don't load.                                                                       |
| `openai.py`    | Full OpenAI implementation — sends chat completions via `httpx`, handles auth errors, rate limits with exponential backoff, and timeouts.                                              |
| `gemini.py`    | Full Google Gemini implementation — uses `httpx` to call the Gemini REST API (`generateContent`). Handles system instructions, rate limits, and response extraction.                   |
| `anthropic.py` | Stub — raises "not implemented yet" with a helpful message. Planned for a future phase.                                                                                                |

### Prompts (`prompts/`)

| File           | What & Why                                                                                                                                                                         |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `templates.py` | The actual prompt text — system prompt (tells the LLM to act as a code reviewer and output JSON), depth modifiers (minimal/standard/thorough), and file diff formatting templates. |
| `builder.py`   | Takes `FileDiff` objects → assembles them into LLM message lists. Handles chunking if diffs exceed token limits.                                                                   |

### Review (`review/`)

| File        | What & Why                                                                                                                                                                                                       |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `models.py` | `ReviewComment` (severity, file, line, explanation, suggestion) and `ReviewResult` (list of comments + metadata). These are what the user ultimately sees.                                                       |
| `engine.py` | **The brain** — orchestrates: diffs → prompt builder → LLM provider → parse JSON response → validate comments against actual files. Fault-tolerant: handles markdown fences, trailing commas, malformed entries. |

### GitHub (`github/`)

| File           | What & Why                                                                               |
| -------------- | ---------------------------------------------------------------------------------------- |
| `commenter.py` | Stub for posting review comments to GitHub PRs via REST API. Optional feature for later. |

### Project Meta

| File                       | What & Why                                                                                             |
| -------------------------- | ------------------------------------------------------------------------------------------------------ |
| `pyproject.toml`           | Build config, dependencies, CLI entry point (`nopush` command), and tool configs (ruff, mypy, pytest). |
| `.github/workflows/ci.yml` | CI: lint + type-check + test on Python 3.10–3.13.                                                      |
| `.pre-commit-config.yaml`  | Auto-runs ruff formatting and file hygiene checks on every commit.                                     |
| `CONTRIBUTING.md`          | How to set up dev env, run tests, add providers, and submit PRs.                                       |
| `CHANGELOG.md`             | Version history in Keep a Changelog format.                                                            |
| `tests/conftest.py`        | Shared fixtures — sample configs, diffs, and review results reused across all test files.              |

### Data Flow (TL;DR)

```
nopush review
  → config/manager.py        (load & merge configuration)
  → git/diff_parser.py       (get staged diff → FileDiff objects)
  → prompts/builder.py       (FileDiffs → LLM messages, with chunking)
  → providers/openai.py      (messages → raw JSON string)
  → review/engine.py         (parse JSON → validate → ReviewComment objects)
  → cli/renderer.py          (render to terminal with Rich)
```

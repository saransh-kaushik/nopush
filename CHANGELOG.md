# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Project scaffolding with `src/` layout
- CLI with `nopush init` (interactive setup) and `nopush review` (full pipeline)
- Configuration system with layered resolution (CLI > env > project > user > defaults)
- Git diff parser for staged changes, refs, and file paths
- Prompt builder with review depth support (minimal / standard / thorough)
- Token-based chunking for large diffs
- LLM provider abstraction with OpenAI and Google Gemini implementations
- Anthropic provider stub for future implementation
- Provider registry with lazy imports and case-insensitive name resolution
- Review engine with fault-tolerant JSON response parsing
- Hallucinated file path validation (discards references to non-existent files)
- Rich-based terminal renderer with severity-coded panels and syntax-highlighted suggestions
- Review summary with issue counts by severity (🔴 critical, 🟡 warning, 🔵 suggestion, ⚪ nitpick)
- CLI flags: `--depth`, `--provider`, `--model`, `--max-files`
- Graceful error handling for auth failures, network issues, git errors, and empty diffs
- Spinner feedback during LLM API calls
- GitHub PR commenter stub (optional, for future implementation)
- Comprehensive test suite (177 tests) covering all modules
- CI pipeline (GitHub Actions) with lint, type check, and multi-Python tests
- Pre-commit hooks (ruff, file hygiene)
- CONTRIBUTING.md with development guidelines

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Project scaffolding with `src/` layout
- CLI skeleton with `nopush init` and `nopush review` commands
- Configuration system with layered resolution (CLI > env > project > user > defaults)
- Git diff parser for staged changes, refs, and file paths
- Prompt builder with review depth support (minimal / standard / thorough)
- LLM provider abstraction with OpenAI implementation
- Review engine with fault-tolerant JSON response parsing
- Test suite with fixtures and initial coverage
- CI pipeline (GitHub Actions) with lint, type check, and multi-Python tests
- Pre-commit hooks (ruff, file hygiene)
- CONTRIBUTING.md with development guidelines

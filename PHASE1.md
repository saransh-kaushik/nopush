# Phase 1 Roadmap - NoPush

## Goal

Build the smallest version of **NoPush** that provides immediate value as an AI-powered local code reviewer.

---

## Features

| Step | Feature                         | Description                                                                                                          |
| ---- | ------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| 1    | CLI Setup                       | Create the `nopush` CLI with commands like `nopush init` and `nopush review`.                                        |
| 2    | BYOK Support                    | Allow users to configure their own API keys and preferred AI model locally.                                          |
| 3    | Git Diff Parser                 | Read staged changes, a Git diff, or specific files to review.                                                        |
| 4    | Prompt Builder                  | Convert code changes into a structured prompt for the LLM.                                                           |
| 5    | LLM Provider Layer              | Implement a common interface for AI providers (OpenAI first, others later).                                          |
| 6    | Review Engine                   | Generate structured review comments with severity, file, line number, explanation, and suggestion.                   |
| 7    | Terminal Output                 | Display clean, colorized review results directly in the terminal.                                                    |
| 8    | GitHub PR Comments _(Optional)_ | Post generated review comments to GitHub pull requests.                                                              |
| 9    | Configuration System            | Support project configuration (`nopush.yaml`) for model selection, ignored files, review depth, and custom settings. |
| 10   | Packaging                       | Publish the project as a Python package (`pip install nopush`).                                                      |

---

## Phase 1 Deliverable

A developer should be able to install and use NoPush in under two minutes.

```bash
pip install nopush

nopush init      # Configure API key and model
nopush review    # Review staged Git changes
```

The tool should analyze the code changes and display AI-powered review suggestions directly in the terminal.

---

## Out of Scope (Later Phases)

The following features are intentionally excluded from Phase 1:

- Memory and learning from previous reviews
- Custom review rules
- Multi-agent workflows
- MCP integrations
- CI/CD integrations
- Team collaboration
- Cloud dashboard
- Review history and analytics

---

## Success Criteria

- ✅ Installable via `pip`
- ✅ Easy configuration with BYOK
- ✅ Reviews staged Git changes
- ✅ Supports at least one LLM provider
- ✅ Produces structured, high-quality review feedback
- ✅ Clean CLI experience

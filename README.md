# NoPush

NoPush is a local-first, AI-powered code review assistant and a lightweight alternative to CodeRabbit. It helps developers review staged changes, Git diffs, or pull request updates using their own API keys and preferred LLM provider.

## Why NoPush?

NoPush is designed to make AI code review fast, private, and easy to use from the terminal. Instead of sending your workflow into a hosted platform, NoPush keeps the experience local and developer-friendly while still giving you high-quality review feedback.

## Core Features

- **CLI-first workflow** for fast reviews from the terminal
- **Bring Your Own Key (BYOK)** support for OpenAI, Anthropic, Gemini, and more
- **Git diff parsing** for staged changes, diffs, or specific files
- **Prompt builder** that turns code changes into structured LLM input
- **Provider abstraction layer** for multiple AI models
- **Structured review output** with severity, file, line number, explanation, and suggestion
- **Clean terminal rendering** with readable, colorized feedback
- **Optional GitHub PR comments** for posting review results back to pull requests
- **Project configuration** through `nopush.yaml`
- **Python packaging** for easy installation with `pip`

## Quick Start

```bash
nopush init      # Configure API key and model
nopush review    # Review staged Git changes
```

## Configuration

NoPush uses a local configuration file, `nopush.yaml`, to store project preferences such as:

- Preferred model
- API provider
- Ignored files or directories
- Review depth
- Custom review settings

Example:

```yaml
provider: openai
model: gpt-4.1
review_depth: standard
ignore:
  - node_modules/
  - dist/
  - .git/
```

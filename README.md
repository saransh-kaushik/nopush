# 🚀 NoPush

[![PyPI version](https://img.shields.io/pypi/v/nopush.svg)](https://pypi.org/project/nopush/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**NoPush** is a local-first, AI-powered code review assistant. It helps developers review staged changes, Git diffs, or pull request updates directly from the terminal using their own API keys and preferred LLM provider.

## ✨ Why NoPush?

NoPush is designed to make AI code review fast, private, and easy to use from your local environment. Instead of sending your code to a hosted third-party platform, NoPush keeps the experience local and developer-friendly, while still delivering high-quality, structured review feedback.

## 📦 Features

- **CLI-First Workflow**: Fast and seamless reviews directly from your terminal.
- **Bring Your Own Key (BYOK)**: Full support for top-tier providers like OpenAI, Anthropic, Gemini, and more.
- **Git Diff Parsing**: Intelligently analyzes staged changes, uncommitted diffs, or specific files.
- **Smart Prompt Builder**: Automatically chunks and structures your code changes for optimal LLM context.
- **Provider Abstraction Layer**: Easily switch between different AI models and providers.
- **Structured Feedback**: Get actionable insights with severity levels, file paths, line numbers, explanations, and concrete suggestions.
- **Clean Terminal UI**: Highly readable, colorized feedback rendered beautifully in your console.
- **Configurable**: Easily adapt to your project needs via `nopush.yaml`.

## 🛠️ Installation

You can easily install NoPush via `pip`:

```bash
pip install nopush
```

## 🚀 Quick Start

Initialize NoPush in your project and configure your provider and API key:

```bash
nopush init
```

Review your currently staged Git changes:

```bash
nopush review
```

## ⚙️ Configuration

NoPush uses a local configuration file named `nopush.yaml` in your project root to store your preferences. 

Example `nopush.yaml`:

```yaml
provider: openai
model: gpt-4o
review_depth: standard
ignore:
  - node_modules/
  - dist/
  - .git/
  - __pycache__/
```

**Available configuration options:**
- `provider`: The LLM provider to use (e.g., `openai`, `anthropic`, `gemini`).
- `model`: The specific model to use for the review.
- `review_depth`: How deep the review should be (`light`, `standard`, `deep`).
- `ignore`: A list of directories or files to ignore during the review process.

## 🤝 Contributing

Contributions are welcome! If you'd like to improve NoPush, please check out our [Contributing Guidelines](CONTRIBUTING.md) and feel free to open an issue or submit a pull request on the [GitHub repository](https://github.com/saransh-kaushik/nopush).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

# Email Agent

A CLI tool for triaging, categorizing, and summarizing high-volume inboxes using multi-agent AI orchestration.

## Features

- **Multi-connector support**: Gmail, Outlook, IMAP
- **Intelligent categorization**: Rule-based and ML-powered email sorting
- **Daily brief generation**: AI-powered summaries with action items
- **Rich CLI interface**: Built with Typer and Textual
- **Multi-agent orchestration**: Powered by Crew-AI
- **Privacy-first**: Local storage with optional encryption

## Quick Start

1. **Install Email Agent**:
   ```bash
   pip install -e .
   ```

2. **Initialize the system**:
   ```bash
   email-agent init setup
   ```

3. **Add a Gmail connector**:
   ```bash
   email-agent config add-connector gmail
   ```

4. **Pull your first emails**:
   ```bash
   email-agent pull --since yesterday
   ```

5. **Generate a daily brief**:
   ```bash
   email-agent brief generate --today
   ```

## Commands

### Initialization
- `email-agent init setup` - Interactive setup wizard
- `email-agent init check` - Verify configuration
- `email-agent init reset` - Reset all data (careful!)

### Email Management
- `email-agent pull sync` - Sync emails from connectors
- `email-agent pull status` - Check sync status
- `email-agent pull test <connector>` - Test connector

### Daily Briefs
- `email-agent brief generate` - Generate daily brief
- `email-agent brief show` - Show existing brief
- `email-agent brief list` - List recent briefs

### Configuration
- `email-agent config show` - Show configuration
- `email-agent config add-connector` - Add email connector
- `email-agent dashboard` - Launch interactive TUI

### Utilities
- `email-agent stats` - Show email statistics
- `email-agent sync` - Full sync: pull + categorize + brief
- `email-agent version` - Show version

## Configuration

Email Agent uses environment variables for configuration. Copy `.env.example` to `.env` and customize:

```bash
# OpenAI API for summaries
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4

# Gmail API
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Database
DATABASE_URL=sqlite:///~/.email_agent/data.db

# Briefs
BRIEF_OUTPUT_DIR=~/Briefs
```

## Gmail Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Add credentials to your `.env` file

## Architecture

```
┌────────────┐      ┌──────────────┐
│ CLI (Typer)│──RPC▶│   Crew Core  │──spawn▶ Agents
└────────────┘      └──────────────┘
       │                       │
       ▼                       ▼
 ┌───────────┐        ┌────────────────┐
 │  Storage  │        │  LLM Gateway   │
 │SQLite+SQL │        │ OpenAI / Local │
 └───────────┘        └────────────────┘
       │
       ▼
┌────────────┐
│Connectors  │
│Gmail/Graph │
└────────────┘
```

## Agents

- **Collector Agent**: Fetches emails from connectors
- **Categorizer Agent**: Applies rules and ML categorization  
- **Summarizer Agent**: Generates briefs and summaries

## Development

1. Clone the repository
2. Install in development mode:
   ```bash
   pip install -e ".[dev]"
   ```
3. Run tests:
   ```bash
   pytest
   ```
4. Format code:
   ```bash
   black src/
   isort src/
   ```

## License

MIT License - see LICENSE file for details.
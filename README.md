# Email Agent 🤖📧

A comprehensive CLI Email Agent with AI-powered multi-agent orchestration for intelligent email management, triage, and automation.

## 🚀 Features

### 🧠 AI-Powered Multi-Agent System
- **Crew-AI Orchestration**: Multi-agent system with specialized roles
- **Smart Categorization**: Automatic email categorization using ML
- **Intelligent Prioritization**: AI-driven priority scoring and triage
- **Action Extraction**: Extracts actionable items, commitments, and deadlines
- **Thread Summarization**: AI-powered thread analysis with insights
- **Learning System**: Learns from user feedback to improve decisions

### 🏢 CEO Intelligence System
- **Enhanced Labeling**: Advanced spam filtering with sender reputation scoring
- **Relationship Intelligence**: Strategic contact profiling (board, investors, customers)
- **Thread Continuity**: Conversation tracking with context-aware labeling
- **Auto-Escalation**: VIP contact priority handling with smart routing
- **Strategic Analysis**: Board member and investor communication prioritization

### 📧 Email Connectors
- **Gmail Integration**: Full Gmail API support with OAuth2
- **IMAP Support**: Universal IMAP connector for any email provider
- **Outlook Support**: Microsoft Graph API integration

### 🏷️ Advanced Gmail SDK Features
- **Smart Labels**: Automatic Gmail label creation and application
- **Calendar Integration**: Auto-creates calendar events from meeting requests
- **Smart Replies**: AI-generated reply suggestions
- **Bulk Operations**: Efficient batch processing of emails

### 📊 Intelligence & Analytics
- **Daily Briefs**: AI-generated summaries with actionable insights
- **Commitment Tracking**: Track commitments, deadlines, and follow-ups
- **Thread Analysis**: Comprehensive thread summarization with business insights
- **Performance Metrics**: Email processing statistics and effectiveness scores

### 🖥️ Interface Options
- **Rich CLI**: Feature-rich command-line interface with Typer
- **Interactive TUI**: Beautiful terminal UI with Textual
- **Docker Support**: Containerized deployment with persistence

### 🔒 Privacy-First Design
- **Local Storage**: SQLite database with no cloud dependencies
- **Secure OAuth**: Industry-standard authentication flows
- **Credential Protection**: Secure credential management

## 📦 Installation

### Prerequisites
- Python 3.11+
- Git
- Docker (optional)

### Quick Install
```bash
git clone https://github.com/haasonsaas/email-agent.git
cd email-agent
pip install -e .
```

### Docker Install
```bash
git clone https://github.com/haasonsaas/email-agent.git
cd email-agent
docker-compose up --build -d
```

## 🚀 Quick Start

### 1. Initialize the Agent
```bash
email-agent init
```

### 2. Add Gmail Connector
```bash
email-agent config add-connector gmail
```

### 3. Sync Emails
```bash
email-agent sync --since yesterday
```

### 4. View Daily Brief
```bash
email-agent brief --today
```

### 5. Smart Action Processing
```bash
email-agent smart-actions --apply-labels --replies
```

## 🛠️ Commands Overview

### Core Operations
```bash
# Full sync with AI processing
email-agent sync --since "1 week ago" --brief

# View system status and statistics
email-agent status

# Generate daily brief
email-agent brief --today --detailed

# Launch interactive dashboard
email-agent dashboard
```

### AI-Powered Features
```bash
# Extract actions from emails with Gmail integration
email-agent smart-actions --apply-labels --replies --events

# Intelligent email handling
email-agent auto-handle --verbose

# Summarize email threads
email-agent thread-summary --insights --overview

# View smart inbox with AI triage
email-agent smart-inbox --limit 50
```

### 🏢 CEO Intelligence Commands
```bash
# Setup CEO label system in Gmail
email-agent ceo setup

# Apply basic CEO labeling
email-agent ceo label --limit 200

# Enhanced intelligence with relationship analysis
email-agent ceo intelligence --limit 100 --dry-run

# Analyze strategic relationships
email-agent ceo relationships --limit 1000

# Thread continuity analysis
email-agent ceo threads --limit 500

# View CEO email insights
email-agent ceo analyze
```

### Commitment & Task Management
```bash
# View commitments and deadlines
email-agent commitments --report

# View overdue items
email-agent commitments --overdue

# Mark commitment as completed
email-agent mark-complete 123 --notes "Completed successfully"
```

### Learning & Feedback
```bash
# Provide feedback on AI decisions
email-agent feedback email-123 --feedback "Category should be work" --correct "work"

# View learning statistics
email-agent learning-stats

# Export learning data
email-agent export-learning learning-backup.json
```

### Configuration & Management
```bash
# Add email connectors
email-agent config add-connector gmail
email-agent config add-connector imap

# Manage categorization rules
email-agent rule add "sender:github.com" work high

# View categories and statistics
email-agent cat list
email-agent stats
```

## 🔧 Configuration

### Environment Variables
```bash
# Required
OPENAI_API_KEY=your-openai-key
GOOGLE_CLIENT_ID=your-gmail-client-id
GOOGLE_CLIENT_SECRET=your-gmail-client-secret

# Optional
DATABASE_URL=sqlite:///data/email_agent.db
LOG_LEVEL=INFO
BRIEF_OUTPUT_DIR=./briefs
```

### Gmail Setup
1. Create a Google Cloud Project
2. Enable Gmail API
3. Create OAuth 2.0 credentials
4. Add credentials to the agent configuration

## 🏗️ Architecture

### Multi-Agent System
```
EmailAgentCrew
├── CollectorAgent      # Email synchronization
├── CategorizerAgent    # AI-powered categorization
├── SummarizerAgent     # Content summarization
├── ActionExtractor     # Action item extraction
├── ThreadSummarizer    # Thread analysis
├── LearningSystem      # Feedback processing
└── CommitmentTracker   # Task management
```

### Data Flow
```
Email Sources → Collectors → Categorizers → Action Extractors → Database
                    ↓              ↓              ↓
              AI Processing → Smart Labels → Commitment Tracking
                    ↓              ↓              ↓
              Daily Briefs → Thread Summaries → Learning System
```

## 🎯 Use Cases

### 📈 Executive/Manager
- **Daily Brief**: Start each day with AI-generated email summaries
- **Priority Inbox**: Focus on high-importance emails first
- **Commitment Tracking**: Never miss deadlines or commitments
- **Thread Summaries**: Quickly understand long email conversations

### 👩‍💻 Developer/Knowledge Worker
- **Smart Categorization**: Automatically organize technical emails
- **Action Extraction**: Convert emails to actionable tasks
- **Smart Labels**: Organize Gmail with intelligent labeling
- **Learning System**: Improve AI decisions over time

### 🏢 Teams & Organizations
- **Bulk Processing**: Handle high email volumes efficiently
- **Standardized Workflows**: Consistent email handling across team
- **Analytics**: Understand email patterns and effectiveness
- **Docker Deployment**: Easy containerized deployment

## 📊 Example Outputs

### Daily Brief
```
# Daily Email Brief - 2025-08-01

## 📊 Statistics
- Total Emails: 47
- Unread: 23
- High Priority: 8
- Action Items: 12

## 🔴 Urgent Actions
1. Review budget proposal from Finance (Due: Today)
2. Approve design mockups for client (Due: Tomorrow)
3. Follow up on server migration status

## 📅 Meetings & Events  
- Team standup moved to 2 PM
- Client presentation scheduled for Friday

## 💡 Key Insights
- 40% increase in support emails this week
- 3 potential sales opportunities identified
- Security alert requires immediate attention
```

### Smart Actions Output
```
🔍 Smart Action Extraction Starting...
Found 15 emails to analyze for actions

📧 Budget Q4 Planning Meeting Request
   From: finance@company.com
   📢 Needs response: urgent
   📋 Actions: 1
     • Review Q4 budget spreadsheet (Due: 2025-08-05)
   📅 Meetings: 1
     • schedule meeting
   🏷️  Gmail labels applied
   💬 Smart reply generated (234 chars)

📊 Action Extraction Summary:
  📋 Total action items: 23
  🤝 Total commitments: 7
  📅 Meeting requests: 4
  ⏰ Items with deadlines: 15

⚠️  3 items due TODAY!
📅 8 items due this week
```

## 🧪 Development

### Setup Development Environment
```bash
git clone https://github.com/haasonsaas/email-agent.git
cd email-agent
pip install -e ".[dev]"
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=email_agent

# Type checking
mypy src/email_agent
```

### Code Quality
```bash
# Format code
black src/
isort src/

# Lint code  
ruff check src/

# Quality analysis
pyrefly check
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for GPT-4 integration
- **Google** for Gmail API
- **Crew-AI** for multi-agent orchestration
- **Typer** and **Textual** for beautiful CLI/TUI interfaces
- **Rich** for terminal formatting
- **SQLAlchemy** for robust data management

## 🚀 Roadmap

- [ ] Microsoft Outlook/Exchange integration
- [ ] Slack/Teams integration for notifications
- [ ] Natural language query interface
- [ ] Email template generation
- [ ] Advanced analytics dashboard
- [ ] Multi-user support
- [ ] Mobile app companion
- [ ] Integration with task management tools (Todoist, Notion, etc.)

---

**Built for productivity. Powered by AI. Privacy-first.** 🚀
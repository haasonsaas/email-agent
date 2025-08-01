# Contributing to Email Agent

Welcome! We're excited that you're interested in contributing to the Email Agent project. This guide will help you get started with contributing code, documentation, or other improvements.

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Git
- Virtual environment tools (venv, conda, etc.)
- Gmail API credentials for testing
- OpenAI API key for AI features

### Development Setup

1. **Fork and Clone**
   ```bash
   # Fork the repository on GitHub
   git clone https://github.com/your-username/email-agent.git
   cd email-agent
   ```

2. **Set Up Environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Configure Development Environment**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit .env with your credentials
   vim .env
   ```

4. **Set Up Pre-commit Hooks**
   ```bash
   # Install pre-commit
   pip install pre-commit
   
   # Install hooks
   pre-commit install
   ```

5. **Verify Setup**
   ```bash
   # Run tests
   python -m pytest
   
   # Run type checking
   mypy src/
   
   # Run linting
   flake8 src/
   ```

## 📋 Development Workflow

### 1. Choose an Issue
- Browse [open issues](https://github.com/haasonsaas/email-agent/issues)
- Look for `good-first-issue` or `help-wanted` labels
- Comment on the issue to indicate you're working on it

### 2. Create a Branch
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

### 3. Make Changes
- Write code following our style guidelines
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 4. Commit Changes
```bash
# Stage changes
git add .

# Commit with conventional commit format
git commit -m "feat: add email filtering capability"
```

### 5. Push and Create PR
```bash
# Push to your fork
git push origin feature/your-feature-name

# Create pull request on GitHub
```

## 📝 Code Standards

### Code Style
We use several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pre-commit**: Automated checks

### Formatting
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Check linting
flake8 src/ tests/

# Type checking
mypy src/
```

### Commit Messages
We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

**Examples:**
```
feat(cli): add email search command

Add new CLI command to search emails by various criteria including
sender, subject, date range, and content.

Closes #123
```

## 🧪 Testing

### Test Structure
```
tests/
├── unit/                 # Unit tests
├── integration/          # Integration tests
├── fixtures/            # Test data and fixtures
└── conftest.py          # Pytest configuration
```

### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_agents.py

# Run with coverage
python -m pytest --cov=src/email_agent

# Run integration tests
python -m pytest tests/integration/
```

### Writing Tests
```python
import pytest
from email_agent.models import Email
from email_agent.agents.categorizer import CategorizerAgent

class TestCategorizerAgent:
    def test_categorizes_work_email(self):
        # Arrange
        agent = CategorizerAgent()
        email = Email(
            subject="Project deadline update",
            sender="boss@company.com",
            content="The project deadline has been moved..."
        )
        
        # Act
        result = agent.categorize(email)
        
        # Assert
        assert result.category == "work"
        assert result.confidence > 0.8
```

### Test Data
Use fixtures for test data:
```python
@pytest.fixture
def sample_email():
    return Email(
        id="test-123",
        subject="Test Email",
        sender="test@example.com",
        content="This is a test email content"
    )
```

## 🏗️ Architecture Guidelines

### Adding New Features

#### 1. New CLI Commands
```python
# src/email_agent/cli/commands/your_command.py
import typer
from email_agent.cli.base import BaseCommand

app = typer.Typer()

@app.command()
def your_command(
    option: str = typer.Option(..., help="Your option description")
):
    """Your command description."""
    # Implementation here
```

#### 2. New Agents
```python
# src/email_agent/agents/your_agent.py
from email_agent.agents.base import BaseAgent
from email_agent.models import Email, AgentResult

class YourAgent(BaseAgent):
    def __init__(self, config: dict):
        super().__init__(config)
        # Initialize your agent
    
    def process(self, email: Email) -> AgentResult:
        # Process the email
        return AgentResult(
            success=True,
            data={"your": "result"}
        )
```

#### 3. New Rules
```python
# src/email_agent/rules/your_rule.py
from email_agent.rules.base import BaseRule
from email_agent.models import Email

class YourRule(BaseRule):
    def matches(self, email: Email) -> bool:
        # Check if rule applies to email
        return True
    
    def execute(self, email: Email) -> dict:
        # Execute rule action
        return {"action": "completed"}
```

### Database Changes

1. **Create Migration**
   ```python
   # src/email_agent/storage/migrations/001_your_migration.py
   def upgrade(connection):
       connection.execute("""
           ALTER TABLE emails ADD COLUMN new_field TEXT;
       """)
   
   def downgrade(connection):
       connection.execute("""
           ALTER TABLE emails DROP COLUMN new_field;
       """)
   ```

2. **Update Models**
   ```python
   # src/email_agent/storage/models.py
   class EmailORM(Base):
       __tablename__ = "emails"
       
       # Existing fields...
       new_field = Column(String, nullable=True)
   ```

## 📚 Documentation

### Code Documentation
- Use docstrings for all public functions and classes
- Follow Google docstring format
- Include type hints

```python
def process_email(email: Email, config: dict) -> ProcessingResult:
    """Process an email using the configured agents.
    
    Args:
        email: The email to process
        config: Processing configuration
        
    Returns:
        Processing result with analysis and actions
        
    Raises:
        ProcessingError: If email processing fails
    """
```

### Documentation Updates
- Update relevant documentation for new features
- Add examples and usage instructions
- Update API documentation for public interfaces

### README Updates
Keep the main README current:
- Update feature lists
- Add new CLI commands
- Update installation instructions

## 🐛 Bug Reports

### Before Reporting
1. Check existing issues
2. Reproduce the bug
3. Gather relevant information

### Bug Report Template
```markdown
**Bug Description**
A clear description of the bug.

**Steps to Reproduce**
1. Go to '...'
2. Click on '....'
3. See error

**Expected Behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment**
- OS: [e.g. macOS]
- Python version: [e.g. 3.11]
- Email Agent version: [e.g. 1.0.0]

**Additional Context**
Any other context about the problem.
```

## ✨ Feature Requests

### Feature Request Template
```markdown
**Feature Description**
A clear description of the feature you'd like.

**Use Case**
Describe the problem this feature would solve.

**Proposed Solution**
How you envision the feature working.

**Alternatives**
Other solutions you've considered.

**Additional Context**
Any other context or screenshots.
```

## 🔍 Code Review Process

### Submitting PRs
1. **Clear Description**: Explain what and why
2. **Link Issues**: Reference related issues
3. **Screenshots**: For UI changes
4. **Tests**: Include relevant tests
5. **Documentation**: Update docs if needed

### Review Checklist
- [ ] Code follows style guidelines
- [ ] Tests pass and coverage is maintained
- [ ] Documentation is updated
- [ ] No breaking changes (or clearly documented)
- [ ] Performance implications considered

### Addressing Feedback
- Respond to all comments
- Make requested changes
- Update tests if needed
- Ask questions if unclear

## 🚀 Release Process

### Version Numbering
We follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- `MAJOR`: Breaking changes
- `MINOR`: New features (backwards compatible)
- `PATCH`: Bug fixes

### Release Checklist
1. Update version numbers
2. Update CHANGELOG.md
3. Create release branch
4. Final testing
5. Create GitHub release
6. Deploy to package registry

## 💬 Communication

### Channels
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Requests**: Code review and discussion

### Getting Help
- Check existing documentation first
- Search closed issues
- Ask in GitHub Discussions
- Tag maintainers if urgent

## 🏆 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Added to GitHub contributors page

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to Email Agent! 🎉

# Testing Guide

Comprehensive testing strategy for the Email Agent project, covering unit tests, integration tests, and end-to-end testing.

## 🧪 Testing Framework

### Test Stack
- **pytest**: Primary testing framework
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mocking utilities
- **pytest-cov**: Coverage reporting
- **factory-boy**: Test data generation
- **responses**: HTTP mocking

### Configuration
```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
python_classes = Test*
addopts = 
    --strict-markers
    --disable-warnings
    --cov=src/email_agent
    --cov-report=html
    --cov-report=term-missing
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
    ai: Tests requiring AI/OpenAI API
```

## 📁 Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_agents.py      # Agent unit tests
│   ├── test_models.py      # Model unit tests
│   ├── test_rules.py       # Rules engine tests
│   └── test_cli.py         # CLI unit tests
├── integration/             # Integration tests
│   ├── test_gmail_integration.py
│   ├── test_database_integration.py
│   └── test_agent_workflow.py
├── e2e/                    # End-to-end tests
│   ├── test_full_workflow.py
│   └── test_cli_commands.py
├── fixtures/               # Test data
│   ├── emails/            # Sample email files
│   ├── responses/         # API response mocks
│   └── configs/           # Test configurations
├── conftest.py            # Pytest configuration
└── factories.py           # Test data factories
```

## 🏃 Running Tests

### Basic Commands
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_agents.py

# Run specific test method
pytest tests/unit/test_agents.py::TestCategorizerAgent::test_categorizes_work_email

# Run tests with specific marker
pytest -m unit
pytest -m integration
pytest -m "not slow"
```

### Coverage Reports
```bash
# Generate coverage report
pytest --cov=src/email_agent --cov-report=html

# View coverage in browser
open htmlcov/index.html

# Check coverage threshold
pytest --cov=src/email_agent --cov-fail-under=80
```

### Parallel Testing
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest -n auto
pytest -n 4  # Use 4 processes
```

## 🔧 Test Configuration

### conftest.py
```python
import pytest
import asyncio
from unittest.mock import Mock
from email_agent.models import Email, EmailAddress
from email_agent.config import Settings

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def settings():
    """Provide test settings."""
    return Settings(
        database_path=":memory:",
        openai_api_key="test-key",
        gmail_client_secret_path="test-credentials.json"
    )

@pytest.fixture
def mock_openai():
    """Mock OpenAI API responses."""
    with patch('openai.ChatCompletion.create') as mock:
        mock.return_value = {
            'choices': [{'message': {'content': 'test response'}}]
        }
        yield mock

@pytest.fixture
def sample_email():
    """Provide a sample email for testing."""
    return Email(
        id="test-123",
        gmail_id="gmail-456",
        subject="Test Subject",
        sender=EmailAddress(email="test@example.com", name="Test User"),
        recipients=[EmailAddress(email="recipient@example.com")],
        content="This is test email content",
        received_at=datetime.now()
    )
```

### Test Factories
```python
# tests/factories.py
import factory
from datetime import datetime
from email_agent.models import Email, EmailAddress

class EmailAddressFactory(factory.Factory):
    class Meta:
        model = EmailAddress
    
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Faker('name')

class EmailFactory(factory.Factory):
    class Meta:
        model = Email
    
    id = factory.Sequence(lambda n: f"email-{n}")
    gmail_id = factory.Sequence(lambda n: f"gmail-{n}")
    subject = factory.Faker('sentence', nb_words=4)
    sender = factory.SubFactory(EmailAddressFactory)
    recipients = factory.List([factory.SubFactory(EmailAddressFactory)])
    content = factory.Faker('text', max_nb_chars=500)
    received_at = factory.LazyFunction(datetime.now)
```

## 📧 Unit Tests

### Testing Agents
```python
# tests/unit/test_agents.py
import pytest
from unittest.mock import Mock, patch
from email_agent.agents.categorizer import CategorizerAgent
from email_agent.models import Email, AgentResult

class TestCategorizerAgent:
    @pytest.fixture
    def agent(self, settings):
        return CategorizerAgent(settings)
    
    @pytest.fixture
    def work_email(self):
        return Email(
            subject="Project deadline update",
            sender=EmailAddress(email="boss@company.com"),
            content="The project deadline has been moved to next Friday."
        )
    
    def test_categorizes_work_email(self, agent, work_email, mock_openai):
        # Arrange
        mock_openai.return_value = {
            'choices': [{'message': {'content': 'work'}}]
        }
        
        # Act
        result = agent.categorize(work_email)
        
        # Assert
        assert result.category == "work"
        assert result.confidence > 0.7
        mock_openai.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_categorization(self, agent, work_email, mock_openai):
        # Test async version
        result = await agent.categorize_async(work_email)
        assert result.category == "work"
    
    def test_handles_api_error(self, agent, work_email):
        with patch('openai.ChatCompletion.create', side_effect=Exception("API Error")):
            result = agent.categorize(work_email)
            assert result.category == "unknown"
            assert result.error is not None
```

### Testing Models
```python
# tests/unit/test_models.py
import pytest
from datetime import datetime
from email_agent.models import Email, EmailAddress, EmailThread

class TestEmail:
    def test_email_creation(self):
        email = Email(
            id="test-123",
            subject="Test Subject",
            sender=EmailAddress(email="test@example.com"),
            content="Test content"
        )
        assert email.id == "test-123"
        assert email.subject == "Test Subject"
        assert email.sender.email == "test@example.com"
    
    def test_email_validation(self):
        with pytest.raises(ValueError):
            Email(id="", subject="Test")  # Empty ID should fail
    
    def test_email_serialization(self, sample_email):
        # Test JSON serialization
        data = sample_email.dict()
        assert data['id'] == sample_email.id
        assert data['subject'] == sample_email.subject
        
        # Test deserialization
        restored = Email(**data)
        assert restored.id == sample_email.id
```

### Testing CLI Commands
```python
# tests/unit/test_cli.py
import pytest
from typer.testing import CliRunner
from email_agent.cli.main import app

class TestCLI:
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    def test_help_command(self, runner):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Email Agent" in result.stdout
    
    def test_sync_command(self, runner, mock_gmail_service):
        result = runner.invoke(app, ["sync", "--days", "1"])
        assert result.exit_code == 0
        assert "Synced" in result.stdout
    
    def test_stats_command(self, runner, mock_database):
        mock_database.count_emails.return_value = 42
        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "42" in result.stdout
```

## 🔗 Integration Tests

### Database Integration
```python
# tests/integration/test_database_integration.py
import pytest
from email_agent.storage.database import DatabaseManager
from email_agent.models import Email

class TestDatabaseIntegration:
    @pytest.fixture
    def db_manager(self, tmp_path):
        db_path = tmp_path / "test.db"
        return DatabaseManager(str(db_path))
    
    def test_email_crud_operations(self, db_manager, sample_email):
        # Create
        db_manager.save_email(sample_email)
        
        # Read
        retrieved = db_manager.get_email(sample_email.id)
        assert retrieved.id == sample_email.id
        assert retrieved.subject == sample_email.subject
        
        # Update
        sample_email.category = "updated"
        db_manager.save_email(sample_email)
        updated = db_manager.get_email(sample_email.id)
        assert updated.category == "updated"
        
        # Delete
        db_manager.delete_email(sample_email.id)
        deleted = db_manager.get_email(sample_email.id)
        assert deleted is None
    
    def test_email_search(self, db_manager):
        # Create test emails
        emails = [
            Email(id="1", subject="Meeting tomorrow", sender="boss@company.com"),
            Email(id="2", subject="Birthday party", sender="friend@personal.com"),
            Email(id="3", subject="Meeting next week", sender="colleague@company.com")
        ]
        
        for email in emails:
            db_manager.save_email(email)
        
        # Search by subject
        results = db_manager.search_emails(subject_contains="meeting")
        assert len(results) == 2
        
        # Search by sender domain
        results = db_manager.search_emails(sender_domain="company.com")
        assert len(results) == 2
```

### Gmail API Integration
```python
# tests/integration/test_gmail_integration.py
import pytest
from unittest.mock import Mock, patch
from email_agent.connectors.gmail import GmailConnector

class TestGmailIntegration:
    @pytest.fixture
    def gmail_connector(self, settings):
        with patch('email_agent.connectors.gmail.build') as mock_build:
            mock_service = Mock()
            mock_build.return_value = mock_service
            connector = GmailConnector(settings)
            connector.service = mock_service
            return connector
    
    def test_fetch_emails(self, gmail_connector):
        # Mock Gmail API response
        gmail_connector.service.users().messages().list().execute.return_value = {
            'messages': [{'id': 'msg1'}, {'id': 'msg2'}]
        }
        
        gmail_connector.service.users().messages().get().execute.return_value = {
            'id': 'msg1',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'From', 'value': 'test@example.com'}
                ],
                'body': {'data': 'VGVzdCBib2R5'}  # Base64 encoded "Test body"
            }
        }
        
        emails = gmail_connector.fetch_emails(days=1)
        assert len(emails) >= 1
        assert emails[0].subject == 'Test Subject'
```

## 🚀 End-to-End Tests

### Full Workflow Tests
```python
# tests/e2e/test_full_workflow.py
import pytest
from email_agent.main import EmailAgent
from email_agent.config import Settings

class TestFullWorkflow:
    @pytest.fixture
    def email_agent(self, tmp_path, mock_openai, mock_gmail_service):
        settings = Settings(
            database_path=str(tmp_path / "test.db"),
            openai_api_key="test-key"
        )
        return EmailAgent(settings)
    
    @pytest.mark.slow
    def test_complete_email_processing(self, email_agent):
        # This test runs the complete workflow:
        # 1. Fetch emails from Gmail
        # 2. Process them through AI agents
        # 3. Store results in database
        # 4. Generate summary
        
        # Act
        result = email_agent.process_emails(days=1)
        
        # Assert
        assert result.processed_count > 0
        assert result.errors_count == 0
        assert len(result.categories) > 0
```

### CLI End-to-End Tests
```python
# tests/e2e/test_cli_commands.py
import subprocess
import pytest

class TestCLIEndToEnd:
    @pytest.mark.slow
    def test_cli_sync_and_stats(self, tmp_path):
        # Set up test database
        db_path = tmp_path / "test.db"
        
        # Run sync command
        result = subprocess.run([
            "email-agent", "sync",
            "--db-path", str(db_path),
            "--days", "1"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "Synced" in result.stdout
        
        # Run stats command
        result = subprocess.run([
            "email-agent", "stats",
            "--db-path", str(db_path)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "Total emails" in result.stdout
```

## 🎭 Mocking Strategies

### OpenAI API Mocking
```python
@pytest.fixture
def mock_openai_categorizer():
    with patch('openai.ChatCompletion.create') as mock:
        mock.return_value = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'category': 'work',
                        'confidence': 0.95,
                        'reasoning': 'Contains work-related keywords'
                    })
                }
            }]
        }
        yield mock

@pytest.fixture
def mock_openai_summarizer():
    with patch('openai.ChatCompletion.create') as mock:
        mock.return_value = {
            'choices': [{
                'message': {
                    'content': 'This email discusses project deadlines and next steps.'
                }
            }]
        }
        yield mock
```

### Gmail API Mocking
```python
@pytest.fixture
def mock_gmail_service():
    with patch('googleapiclient.discovery.build') as mock_build:
        mock_service = Mock()
        
        # Mock messages list
        mock_service.users().messages().list().execute.return_value = {
            'messages': [
                {'id': 'msg1', 'threadId': 'thread1'},
                {'id': 'msg2', 'threadId': 'thread2'}
            ]
        }
        
        # Mock message get
        def mock_get_message(userId, id):
            return Mock(execute=Mock(return_value={
                'id': id,
                'threadId': f'thread-{id}',
                'payload': {
                    'headers': [
                        {'name': 'Subject', 'value': f'Subject {id}'},
                        {'name': 'From', 'value': f'sender{id}@example.com'},
                        {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'}
                    ],
                    'body': {'data': 'VGVzdCBjb250ZW50'}  # "Test content" in base64
                }
            }))
        
        mock_service.users().messages().get.side_effect = mock_get_message
        mock_build.return_value = mock_service
        yield mock_service
```

## 📊 Test Data Management

### Fixtures and Sample Data
```python
# tests/fixtures/sample_emails.py
SAMPLE_EMAILS = [
    {
        'id': 'work-email-1',
        'subject': 'Q4 Planning Meeting',
        'sender': 'manager@company.com',
        'content': 'We need to discuss Q4 planning...',
        'expected_category': 'work'
    },
    {
        'id': 'personal-email-1',
        'subject': 'Weekend BBQ Invitation',
        'sender': 'friend@personal.com',
        'content': 'Hey! Want to join our BBQ this weekend?',
        'expected_category': 'personal'
    }
]
```

### Database Seeding
```python
@pytest.fixture
def seeded_database(db_manager):
    """Create a database with sample data."""
    from tests.fixtures.sample_emails import SAMPLE_EMAILS
    
    for email_data in SAMPLE_EMAILS:
        email = Email(**email_data)
        db_manager.save_email(email)
    
    return db_manager
```

## 🔍 Test Debugging

### Debug Mode
```bash
# Run tests with verbose output
pytest -v

# Run with print statements
pytest -s

# Run specific test with debugging
pytest -vvs tests/unit/test_agents.py::TestCategorizerAgent::test_categorizes_work_email

# Drop into debugger on failure
pytest --pdb
```

### Logging in Tests
```python
import logging

def test_with_logging(caplog):
    with caplog.at_level(logging.INFO):
        # Your test code here
        pass
    
    assert "Expected log message" in caplog.text
```

## ⚡ Performance Testing

### Load Testing
```python
import pytest
import time
from concurrent.futures import ThreadPoolExecutor

class TestPerformance:
    @pytest.mark.slow
    def test_concurrent_email_processing(self, email_agent):
        emails = [EmailFactory() for _ in range(100)]
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(email_agent.process_email, email)
                for email in emails
            ]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        
        assert len(results) == 100
        assert end_time - start_time < 30  # Should complete in under 30 seconds
```

### Memory Testing
```python
import psutil
import os

def test_memory_usage():
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Run memory-intensive operation
    emails = [EmailFactory() for _ in range(1000)]
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Assert memory increase is reasonable (less than 100MB)
    assert memory_increase < 100 * 1024 * 1024
```

## 🚀 Continuous Integration

### GitHub Actions
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -e .
    
    - name: Run tests
      run: |
        pytest --cov=src/email_agent --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## 📈 Test Metrics

### Coverage Goals
- **Unit Tests**: 90%+ coverage
- **Integration Tests**: Cover all major workflows
- **Critical Paths**: 100% coverage for core functionality

### Test Performance
- **Unit Tests**: < 1 second each
- **Integration Tests**: < 10 seconds each
- **E2E Tests**: < 60 seconds each
- **Full Suite**: < 5 minutes

### Quality Metrics
- All tests should be deterministic
- No flaky tests in CI
- Clear test names and documentation
- Minimal test dependencies

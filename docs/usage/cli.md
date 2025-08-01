# Command Line Interface (CLI) Guide

The Email Agent provides a comprehensive CLI for managing emails, rules, and system operations.

## 🚀 Getting Started

```bash
# Activate virtual environment
source venv/bin/activate

# View all available commands
email-agent --help
```

## 📋 Available Commands

### Core Operations

#### `sync` - Sync emails from Gmail
```bash
# Sync emails from the last 7 days (default)
email-agent sync

# Sync emails from specific number of days
email-agent sync --days 30

# Sync with verbose output
email-agent sync --verbose
```

#### `stats` - View email statistics
```bash
# View basic statistics
email-agent stats

# View detailed statistics
email-agent stats --detailed
```

#### `brief` - Generate email brief
```bash
# Generate brief for today
email-agent brief

# Generate brief for specific date
email-agent brief --date 2025-01-15

# Generate brief for date range
email-agent brief --start-date 2025-01-01 --end-date 2025-01-31
```

### Dashboard

#### `dashboard` - Launch TUI dashboard
```bash
# Launch interactive dashboard
email-agent dashboard
```

### Configuration

#### `init` - Initialize Email Agent
```bash
# Initialize with default settings
email-agent init

# Initialize with custom database path
email-agent init --db-path /custom/path/data.db
```

#### `config` - Manage configuration
```bash
# View current configuration
email-agent config show

# Set configuration value
email-agent config set openai.api_key "your-api-key"

# Get specific configuration value
email-agent config get database.path
```

### Rules Management

#### `rules` - Manage email rules
```bash
# List all rules
email-agent rules list

# Add new rule
email-agent rules add --name "VIP Emails" --condition "from:vip@company.com" --action "priority:high"

# Remove rule
email-agent rules remove --name "VIP Emails"

# Test rules against emails
email-agent rules test
```

### Categories

#### `categories` - View email categories
```bash
# List all categories with counts
email-agent categories

# Show emails in specific category
email-agent categories --category "action-required"

# Show category distribution
email-agent categories --stats
```

## 🔧 Global Options

All commands support these global options:

```bash
# Verbose output
email-agent --verbose <command>

# Quiet mode (minimal output)
email-agent --quiet <command>

# Custom config file
email-agent --config /path/to/config.yaml <command>

# Custom database path
email-agent --db-path /path/to/database.db <command>
```

## 📝 Examples

### Daily Workflow
```bash
# 1. Sync new emails
email-agent sync --days 1

# 2. View statistics
email-agent stats

# 3. Generate daily brief
email-agent brief

# 4. Launch dashboard for detailed view
email-agent dashboard
```

### Initial Setup
```bash
# 1. Initialize the system
email-agent init

# 2. Configure API keys
email-agent config set openai.api_key "your-key"

# 3. First sync (last 7 days)
email-agent sync

# 4. View results
email-agent stats --detailed
```

### Rule Management
```bash
# Add rule for urgent emails
email-agent rules add \
  --name "Urgent" \
  --condition "subject:urgent OR subject:ASAP" \
  --action "priority:high,category:action-required"

# Test the rule
email-agent rules test

# List all rules
email-agent rules list
```

## 🐛 Troubleshooting

### Common Issues

1. **Permission denied errors**
   ```bash
   # Ensure proper permissions
   chmod +x email-agent
   ```

2. **Missing dependencies**
   ```bash
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

3. **Database locked**
   ```bash
   # Check for running processes
   ps aux | grep email-agent
   ```

4. **API rate limits**
   ```bash
   # Use smaller sync batches
   email-agent sync --days 1
   ```

### Debug Mode

Enable debug logging:
```bash
# Set debug environment variable
export EMAIL_AGENT_DEBUG=1
email-agent sync --verbose
```

## 📊 Performance Tips

1. **Batch Processing**: Sync in smaller date ranges for better performance
2. **Parallel Processing**: Use `--workers` flag for multi-threaded operations
3. **Selective Sync**: Use filters to sync only relevant emails
4. **Regular Maintenance**: Run cleanup commands periodically

```bash
# Example optimized sync
email-agent sync --days 7 --workers 4 --filter "is:unread"
```

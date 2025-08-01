# Email Agent Scripts

## Overview

This directory contains utility scripts for the Email Agent system. Most functionality has been integrated into the main CLI commands.

## Migration Scripts

The `migration/` directory contains scripts that were used during development and migration. These have been superseded by the main CLI commands:

### Use CLI Instead:

- **Gmail Authentication**: Use `email-agent config gmail`
- **CEO Label Setup**: Use `email-agent ceo setup`
- **Label Emails**: Use `email-agent ceo label --limit 500`
- **Analyze Labels**: Use `email-agent ceo analyze`
- **Pull Emails**: Use `email-agent pull sync`

### CLI Commands

```bash
# Set up Gmail authentication
email-agent config gmail

# Create CEO label system
email-agent ceo setup

# Label emails with CEO system (dry run)
email-agent ceo label --dry-run

# Actually apply labels to 500 emails
email-agent ceo label --limit 500

# Analyze labeled emails
email-agent ceo analyze

# Pull emails from Gmail
email-agent pull sync --since "3 months ago"
```

## Legacy Scripts

The scripts in `migration/` are kept for reference but should not be used directly. They include:

- `authenticate_gmail.py` - Gmail OAuth setup
- `create_ceo_labels.py` - Label creation
- `apply_ceo_labels.py` - Label application
- `analyze_labeled_emails.py` - Label analysis
- `bulk_label_emails.py` - Bulk processing
- Various test scripts

All functionality from these scripts has been properly integrated into the main application.
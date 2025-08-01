# Email Agent Utilities

This directory contains utility scripts for maintaining and managing the Email Agent system.

## Available Utilities

### cleanup_overlabeled_emails.py
A comprehensive cleanup utility to find and fix over-labeled emails in the Gmail system.

**Features:**
- Scans all emails with CEO labels
- Identifies emails with >3 labels (over-labeled)
- Provides detailed analysis and statistics
- Can remove excessive labels for re-processing
- Supports dry-run mode for safety

**Usage:**
```bash
# Dry run (analysis only)
python cleanup_overlabeled_emails.py

# Execute cleanup
python cleanup_overlabeled_emails.py --execute

# Scan more emails
python cleanup_overlabeled_emails.py --max-scan 500
```

**Options:**
- `--execute` - Actually perform the cleanup (default is dry-run)
- `--max-scan N` - Maximum number of emails to scan (default: 500)
- `--max-cleanup N` - Maximum number of emails to clean up (default: 100)
- `--examples N` - Number of examples to show in summary (default: 10)
# Text User Interface (TUI) Guide

The Email Agent features a rich, interactive terminal user interface built with Textual for real-time email management and monitoring.

## 🚀 Launching the TUI

```bash
# Activate virtual environment
source venv/bin/activate

# Launch the dashboard
email-agent dashboard
```

## 🖥️ Interface Overview

The TUI dashboard consists of several key sections:

### Header Bar
- **System Status**: Shows connection status and sync state
- **Quick Stats**: Total emails, unread count, categories
- **Current Time**: Live timestamp

### Main Content Area
- **Email List**: Sortable table of emails with key information
- **Category Distribution**: Visual breakdown of email categories
- **Priority Indicators**: Color-coded priority levels

### Footer
- **Keyboard Shortcuts**: Context-sensitive help
- **Status Messages**: Real-time feedback and notifications

## ⌨️ Keyboard Shortcuts

### Navigation
- `↑/↓` or `j/k` - Navigate email list
- `Page Up/Down` - Scroll by page
- `Home/End` - Jump to top/bottom
- `Tab` - Switch between panels

### Actions
- `Enter` - View selected email details
- `r` - Refresh/sync emails
- `s` - Open search/filter
- `c` - View categories
- `q` - Quit application

### Email Management
- `m` - Mark as read/unread
- `d` - Delete email
- `a` - Archive email
- `f` - Flag/unflag email
- `p` - Change priority

### Views
- `1` - Inbox view
- `2` - Action required
- `3` - High priority
- `4` - Categories view
- `5` - Search results

## 📊 Dashboard Features

### Email List View
The main email table displays:
- **From**: Sender name and email
- **Subject**: Email subject (truncated if long)
- **Date**: Received date/time
- **Category**: AI-assigned category
- **Priority**: Priority level (High/Medium/Low)
- **Status**: Read/unread, flagged indicators

### Category Panel
Shows distribution of emails across categories:
- Action Required
- Informational
- Personal
- Work
- Newsletters
- Promotions
- Custom categories

### Statistics Panel
Real-time statistics including:
- Total email count
- Unread count
- Category breakdown
- Sync status
- Last sync time

## 🔍 Search and Filtering

### Quick Search
Press `s` to open search dialog:
```
Search: from:john subject:meeting
```

### Advanced Filters
- **By Sender**: `from:email@domain.com`
- **By Subject**: `subject:meeting`
- **By Date**: `date:2025-01-15`
- **By Category**: `category:action-required`
- **By Priority**: `priority:high`
- **Combinations**: `from:boss priority:high`

### Filter Examples
```
# Unread high-priority emails
is:unread priority:high

# Emails from specific domain this week
from:@company.com date:this-week

# Action items from meetings
subject:meeting category:action-required
```

## 🎨 Customization

### Themes
The TUI supports multiple color themes:
- **Default**: Standard terminal colors
- **Dark**: Dark mode optimized
- **Light**: Light mode optimized
- **Minimal**: Minimal color scheme

### Configuration
Customize via config file:
```yaml
tui:
  theme: dark
  refresh_interval: 30
  auto_sync: true
  show_categories: true
  compact_view: false
```

## 📧 Email Details View

Press `Enter` on any email to view details:

### Detail Panel Layout
- **Header**: From, To, Subject, Date
- **Body**: Email content (formatted)
- **Attachments**: File list with sizes
- **Actions**: Reply, Forward, Archive, Delete
- **AI Analysis**: Category, sentiment, summary

### Actions Available
- `r` - Reply to email
- `f` - Forward email
- `a` - Archive
- `d` - Delete
- `p` - Print/export
- `Esc` - Return to list

## 🔄 Real-time Updates

### Auto-sync
The dashboard can automatically sync new emails:
- Configurable interval (default: 5 minutes)
- Background processing
- Non-blocking updates
- Visual progress indicators

### Status Indicators
- 🟢 **Connected**: Gmail API active
- 🟡 **Syncing**: Currently updating
- 🔴 **Error**: Connection issues
- ⚪ **Offline**: No connection

## 🐛 Troubleshooting

### Common Issues

1. **TUI not rendering properly**
   ```bash
   # Check terminal compatibility
   echo $TERM
   
   # Try with different terminal
   TERM=xterm-256color email-agent dashboard
   ```

2. **Slow performance**
   ```bash
   # Reduce refresh interval
   email-agent config set tui.refresh_interval 60
   
   # Enable compact view
   email-agent config set tui.compact_view true
   ```

3. **Keyboard shortcuts not working**
   ```bash
   # Check terminal key bindings
   # Try alternative shortcuts
   # Restart terminal session
   ```

### Debug Mode
```bash
# Enable TUI debug logging
export TEXTUAL_LOG=debug
email-agent dashboard
```

## 💡 Tips and Tricks

### Productivity Features
1. **Bulk Actions**: Select multiple emails with `Shift+Click`
2. **Quick Categories**: Use number keys for quick category switching
3. **Search History**: Recent searches are saved and accessible
4. **Keyboard Navigation**: Learn shortcuts for faster operation

### Workflow Optimization
1. **Start with categories** to get overview
2. **Use filters** to focus on specific types
3. **Process by priority** - handle high priority first
4. **Regular cleanup** - archive or delete processed emails

### Performance
1. **Limit email count** in large mailboxes
2. **Use date filters** for focused views
3. **Enable compact mode** for faster rendering
4. **Adjust refresh intervals** based on needs

## 🎯 Advanced Usage

### Custom Views
Create saved searches and filters:
```bash
# Save common filter
email-agent config set tui.saved_filters.work "from:@company.com"
email-agent config set tui.saved_filters.urgent "priority:high is:unread"
```

### Integration with CLI
Combine TUI with CLI commands:
```bash
# Sync then launch dashboard
email-agent sync && email-agent dashboard

# Generate brief then review in TUI
email-agent brief --date today && email-agent dashboard
```

### Monitoring Mode
Run TUI in monitoring mode for continuous updates:
```bash
# Auto-refresh every 2 minutes
email-agent dashboard --auto-refresh 2m
```

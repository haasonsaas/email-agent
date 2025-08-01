#!/usr/bin/env python3
"""
Comprehensive cleanup utility to find and fix over-labeled emails.
This will scan ALL emails with CEO labels and remove excessive labeling.
"""

import asyncio
import json
import keyring
from collections import defaultdict, Counter
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table

console = Console()

class EmailLabelCleanup:
    def __init__(self):
        self.service = None
        self.ceo_labels = {}
        self.overlabeled_emails = []
        
    def setup_gmail_service(self):
        """Setup Gmail API service."""
        creds_json = keyring.get_password("email_agent", "gmail_credentials_default")
        if not creds_json:
            console.print("[red]❌ No Gmail credentials found[/red]")
            return False
        
        credentials = json.loads(creds_json)
        creds = Credentials.from_authorized_user_info(credentials, [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify'
        ])
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        self.service = build('gmail', 'v1', credentials=creds)
        
        # Get all CEO labels
        results = self.service.users().labels().list(userId='me').execute()
        for label in results.get('labels', []):
            if label['name'].startswith('EmailAgent/CEO/'):
                self.ceo_labels[label['name']] = label['id']
        
        console.print(f"✅ Connected to Gmail API")
        console.print(f"📊 Found {len(self.ceo_labels)} CEO labels")
        return True
    
    async def find_overlabeled_emails(self, max_scan: int = 500):
        """Find emails with excessive CEO labels."""
        console.print(f"\n🔍 Scanning for over-labeled emails (max {max_scan})...")
        
        # Get all unique emails that have ANY CEO label
        all_email_ids = set()
        
        # Collect email IDs from each label
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Collecting email IDs from labels...", total=len(self.ceo_labels))
            
            for label_name, label_id in self.ceo_labels.items():
                try:
                    # Get emails with this label
                    search_result = self.service.users().messages().list(
                        userId='me',
                        labelIds=[label_id],
                        maxResults=max_scan // len(self.ceo_labels) + 50  # Distribute scanning
                    ).execute()
                    
                    messages = search_result.get('messages', [])
                    for msg in messages:
                        all_email_ids.add(msg['id'])
                    
                    progress.console.print(f"  {label_name.replace('EmailAgent/CEO/', '')}: {len(messages)} emails")
                    
                except Exception as e:
                    progress.console.print(f"  [red]Error scanning {label_name}: {e}[/red]")
                
                progress.advance(task)
        
        unique_emails = list(all_email_ids)[:max_scan]  # Limit total emails to scan
        console.print(f"\n📧 Found {len(all_email_ids)} unique emails with CEO labels")
        console.print(f"🔍 Analyzing {len(unique_emails)} emails for over-labeling...")
        
        # Analyze each email for label count
        self.overlabeled_emails = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Analyzing email labeling...", total=len(unique_emails))
            
            for email_id in unique_emails:
                try:
                    # Get email details
                    msg = self.service.users().messages().get(
                        userId='me',
                        id=email_id,
                        format='metadata',
                        metadataHeaders=['Subject', 'From', 'Date']
                    ).execute()
                    
                    # Count CEO labels on this email
                    msg_labels = msg.get('labelIds', [])
                    ceo_label_ids = [lid for lid in msg_labels if lid in self.ceo_labels.values()]
                    ceo_label_names = []
                    
                    for label_id in ceo_label_ids:
                        for label_name, ceo_id in self.ceo_labels.items():
                            if label_id == ceo_id:
                                ceo_label_names.append(label_name.replace('EmailAgent/CEO/', ''))
                    
                    # Consider over-labeled if more than 3 CEO labels (our intelligent limit)
                    if len(ceo_label_names) > 3:
                        # Get email metadata
                        headers = msg['payload'].get('headers', [])
                        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
                        
                        self.overlabeled_emails.append({
                            'id': email_id,
                            'subject': subject,
                            'sender': sender,
                            'date': date,
                            'ceo_label_count': len(ceo_label_names),
                            'ceo_labels': ceo_label_names,
                            'ceo_label_ids': ceo_label_ids
                        })
                
                except Exception as e:
                    # Skip emails we can't access
                    pass
                
                progress.advance(task)
        
        # Sort by label count (most over-labeled first)
        self.overlabeled_emails.sort(key=lambda x: x['ceo_label_count'], reverse=True)
        
        console.print(f"\n📊 Analysis Complete!")
        console.print(f"  • Total emails scanned: {len(unique_emails)}")
        console.print(f"  • Over-labeled emails found: [red]{len(self.overlabeled_emails)}[/red]")
        
        return len(self.overlabeled_emails)
    
    def show_overlabeled_summary(self, show_examples: int = 10):
        """Show summary of over-labeled emails."""
        if not self.overlabeled_emails:
            console.print("[green]✅ No over-labeled emails found![/green]")
            return
        
        console.print(f"\n📋 Over-Labeled Email Summary:")
        
        # Label count distribution
        label_counts = Counter(email['ceo_label_count'] for email in self.overlabeled_emails)
        
        table = Table(title="Label Count Distribution")
        table.add_column("CEO Labels", style="cyan")
        table.add_column("Email Count", style="magenta")
        table.add_column("Severity", style="yellow")
        
        for count in sorted(label_counts.keys(), reverse=True):
            email_count = label_counts[count]
            if count >= 10:
                severity = "🚨 Extreme"
            elif count >= 7:
                severity = "⛔ Severe" 
            elif count >= 5:
                severity = "⚠️ High"
            else:
                severity = "🔶 Moderate"
            
            table.add_row(str(count), str(email_count), severity)
        
        console.print(table)
        
        # Show worst examples
        console.print(f"\n🔍 Top {min(show_examples, len(self.overlabeled_emails))} Over-Labeled Emails:")
        
        for i, email in enumerate(self.overlabeled_emails[:show_examples]):
            console.print(f"\n{i+1}. [bold]{email['subject'][:60]}...[/bold]")
            console.print(f"   From: {email['sender'][:50]}")
            console.print(f"   Date: {email['date']}")
            console.print(f"   CEO Labels ({email['ceo_label_count']}): {', '.join(email['ceo_labels'][:8])}{'...' if len(email['ceo_labels']) > 8 else ''}")
    
    async def cleanup_overlabeled_emails(self, dry_run: bool = True, max_cleanup: int = 100):
        """Clean up over-labeled emails by removing excessive labels."""
        if not self.overlabeled_emails:
            console.print("[yellow]No over-labeled emails to clean up[/yellow]")
            return
        
        emails_to_clean = self.overlabeled_emails[:max_cleanup]
        
        if dry_run:
            console.print(f"\n[yellow]🔍 DRY RUN: Would clean up {len(emails_to_clean)} over-labeled emails[/yellow]")
            console.print("\nCleanup strategy:")
            console.print("  • Remove ALL CEO labels from over-labeled emails")
            console.print("  • Let them be re-processed with intelligent consolidation")
            console.print("  • They'll get proper, focused labels")
            console.print("\n[bold]To actually clean up, run with --execute flag[/bold]")
            return
        
        console.print(f"\n🧹 Cleaning up {len(emails_to_clean)} over-labeled emails...")
        console.print("[red]⚠️  This will remove ALL CEO labels from over-labeled emails![/red]")
        console.print("[green]Proceeding with cleanup (non-interactive mode)...[/green]")
        
        cleaned_count = 0
        error_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Cleaning over-labeled emails...", total=len(emails_to_clean))
            
            for email in emails_to_clean:
                try:
                    # Remove ALL CEO labels from this email
                    if email['ceo_label_ids']:
                        body = {'removeLabelIds': email['ceo_label_ids']}
                        self.service.users().messages().modify(
                            userId='me',
                            id=email['id'],
                            body=body
                        ).execute()
                        
                        cleaned_count += 1
                        progress.console.print(f"   ✅ Cleaned: {email['subject'][:40]}... (removed {len(email['ceo_label_ids'])} labels)")
                
                except Exception as e:
                    error_count += 1
                    progress.console.print(f"   ❌ Error: {email['subject'][:40]}... - {str(e)[:50]}")
                
                progress.advance(task)
        
        console.print(f"\n[bold green]✅ Cleanup Complete![/bold green]")
        console.print(f"  • Successfully cleaned: [green]{cleaned_count}[/green] emails")
        console.print(f"  • Errors: [red]{error_count}[/red] emails")
        console.print(f"  • Labels removed: [yellow]{sum(len(e['ceo_label_ids']) for e in emails_to_clean[:cleaned_count])}[/yellow] total")
        
        console.print(f"\n[bold]🔄 Next Steps:[/bold]")
        console.print("1. Run: email-agent ceo collaborative --limit 100")
        console.print("2. The cleaned emails will be re-processed with intelligent consolidation")
        console.print("3. They'll get proper, focused labels this time!")


async def main():
    import sys
    
    console.print(Panel.fit(
        "[bold red]🧹 Email Label Cleanup Utility[/bold red]",
        border_style="red"
    ))
    
    # Parse arguments
    dry_run = "--execute" not in sys.argv
    max_scan = 500
    max_cleanup = 100
    show_examples = 10
    
    for i, arg in enumerate(sys.argv):
        if arg == "--max-scan" and i + 1 < len(sys.argv):
            max_scan = int(sys.argv[i + 1])
        elif arg == "--max-cleanup" and i + 1 < len(sys.argv):
            max_cleanup = int(sys.argv[i + 1])
        elif arg == "--examples" and i + 1 < len(sys.argv):
            show_examples = int(sys.argv[i + 1])
    
    if dry_run:
        console.print("[yellow]🔍 ANALYSIS MODE - No changes will be made[/yellow]")
        console.print("[dim]Use --execute to actually clean up emails[/dim]\n")
    
    # Initialize cleanup system
    cleanup = EmailLabelCleanup()
    
    if not cleanup.setup_gmail_service():
        return
    
    # Find over-labeled emails
    overlabeled_count = await cleanup.find_overlabeled_emails(max_scan)
    
    # Show summary
    cleanup.show_overlabeled_summary(show_examples)
    
    # Clean up if requested
    if overlabeled_count > 0:
        await cleanup.cleanup_overlabeled_emails(dry_run, max_cleanup)
    
    console.print(f"\n[bold green]Analysis complete![/bold green]")

if __name__ == "__main__":
    asyncio.run(main())
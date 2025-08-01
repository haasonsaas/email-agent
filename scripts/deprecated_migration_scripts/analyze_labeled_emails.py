#!/usr/bin/env python3
"""Analyze emails that have been labeled in Gmail."""

import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import keyring
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from collections import Counter, defaultdict
from datetime import datetime

console = Console()

def analyze_gmail_labels():
    """Analyze emails with CEO labels directly from Gmail."""
    
    console.print(Panel.fit("[bold cyan]🎯 CEO Gmail Label Analysis[/bold cyan]", border_style="cyan"))
    
    # Load Gmail credentials
    creds_json = keyring.get_password("email_agent", "gmail_credentials_default")
    if not creds_json:
        console.print("[red]❌ No Gmail credentials found.[/red]")
        return
    
    creds_data = json.loads(creds_json)
    creds = Credentials.from_authorized_user_info(creds_data, [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ])
    
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    
    service = build('gmail', 'v1', credentials=creds)
    
    # Get all CEO labels
    results = service.users().labels().list(userId='me').execute()
    ceo_labels = {label['name']: label['id'] for label in results.get('labels', []) 
                  if label['name'].startswith('EmailAgent/CEO/')}
    
    console.print(f"Found [yellow]{len(ceo_labels)}[/yellow] CEO labels\n")
    
    # Analyze each label
    label_stats = {}
    sample_emails = defaultdict(list)
    
    for label_name, label_id in ceo_labels.items():
        try:
            # Get emails with this label
            results = service.users().messages().list(
                userId='me',
                labelIds=[label_id],
                maxResults=100
            ).execute()
            
            messages = results.get('messages', [])
            label_stats[label_name] = len(messages)
            
            # Get sample emails for important labels
            important_labels = ['DecisionRequired', 'Investors', 'Customers', 'QuickWins', 'DeepWork']
            short_name = label_name.replace('EmailAgent/CEO/', '')
            
            if short_name in important_labels and messages:
                # Get details for up to 5 samples
                for msg in messages[:5]:
                    try:
                        message = service.users().messages().get(
                            userId='me',
                            id=msg['id'],
                            format='metadata',
                            metadataHeaders=['Subject', 'From', 'Date']
                        ).execute()
                        
                        headers = {h['name']: h['value'] 
                                 for h in message['payload'].get('headers', [])}
                        
                        sample_emails[short_name].append({
                            'subject': headers.get('Subject', 'No Subject'),
                            'from': headers.get('From', 'Unknown'),
                            'date': headers.get('Date', 'Unknown')
                        })
                    except:
                        pass
                        
        except Exception as e:
            console.print(f"[dim]Error checking {label_name}: {str(e)[:50]}[/dim]")
    
    # Display results
    console.print("[bold]📊 Label Distribution:[/bold]\n")
    
    # Sort by count
    sorted_labels = sorted(label_stats.items(), key=lambda x: x[1], reverse=True)
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Label", style="cyan", width=30)
    table.add_column("Count", justify="right", style="yellow")
    table.add_column("Visual", style="green")
    
    for label, count in sorted_labels:
        if count > 0:
            short_name = label.replace('EmailAgent/CEO/', '')
            bar = "█" * min(count // 2, 30)
            table.add_row(short_name, str(count), bar)
    
    console.print(table)
    
    # Show samples for important categories
    console.print("\n[bold]📧 Sample Emails by Category:[/bold]\n")
    
    if sample_emails.get('DecisionRequired'):
        console.print("[bold red]🔴 Decisions Required:[/bold red]")
        for email in sample_emails['DecisionRequired']:
            console.print(f"  • {email['subject'][:60]}...")
            console.print(f"    From: {email['from'][:40]}...")
        console.print()
    
    if sample_emails.get('Investors'):
        console.print("[bold yellow]💰 Investor Communications:[/bold yellow]")
        for email in sample_emails['Investors']:
            console.print(f"  • {email['subject'][:60]}...")
            console.print(f"    From: {email['from'][:40]}...")
        console.print()
    
    if sample_emails.get('QuickWins'):
        console.print("[bold green]✅ Quick Wins:[/bold green]")
        for email in sample_emails['QuickWins']:
            console.print(f"  • {email['subject'][:60]}...")
        console.print()
    
    # Summary
    total_labeled = sum(label_stats.values())
    console.print(Panel(f"""[bold]📈 Summary[/bold]
    
Total emails with CEO labels: {total_labeled}

[bold yellow]Top Categories:[/bold yellow]
{chr(10).join(f"• {label.replace('EmailAgent/CEO/', '')}: {count}" 
              for label, count in sorted_labels[:5] if count > 0)}

[bold green]💡 Next Actions:[/bold green]
1. Check DecisionRequired emails first
2. Review Investor communications
3. Knock out QuickWins during breaks
4. Schedule time for DeepWork items""", border_style="green"))

if __name__ == "__main__":
    analyze_gmail_labels()
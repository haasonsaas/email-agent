#!/usr/bin/env python3
"""Create comprehensive CEO-focused Gmail labels."""

import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import keyring
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# CEO Label System with colors
CEO_LABELS = {
    # Strategic Labels - Shades of Blue/Purple
    'EmailAgent/CEO/Investors': {'color': '1c4587', 'description': 'All investor communications'},  # Navy blue
    'EmailAgent/CEO/Customers': {'color': '16a766', 'description': 'Customer feedback & issues'},  # Green (valid)
    'EmailAgent/CEO/Team': {'color': '8e63ce', 'description': 'Team matters & HR'},  # Purple
    'EmailAgent/CEO/Board': {'color': '434343', 'description': 'Board communications'},  # Dark gray
    'EmailAgent/CEO/Metrics': {'color': 'fad165', 'description': 'KPIs & reports'},  # Yellow (valid)
    
    # Operational Labels - Earth tones
    'EmailAgent/CEO/Legal': {'color': '8e63ce', 'description': 'Contracts & compliance'},  # Purple (valid)
    'EmailAgent/CEO/Finance': {'color': '16a766', 'description': 'Financial operations'},  # Green (valid)
    'EmailAgent/CEO/Product': {'color': '1c4587', 'description': 'Product decisions'},  # Blue (valid)
    'EmailAgent/CEO/Vendors': {'color': 'fb4c2f', 'description': 'Vendor relationships'},  # Red (valid)
    'EmailAgent/CEO/PR-Marketing': {'color': 'e07798', 'description': 'External communications'},  # Pink
    
    # Time-Sensitive Labels - Warm colors
    'EmailAgent/CEO/DecisionRequired': {'color': 'fb4c2f', 'description': 'Needs CEO decision'},  # Red
    'EmailAgent/CEO/SignatureRequired': {'color': 'ffad47', 'description': 'Needs signature'},  # Orange (valid)
    'EmailAgent/CEO/WeeklyReview': {'color': 'ffad47', 'description': 'Weekly planning items'},  # Light orange
    'EmailAgent/CEO/Delegatable': {'color': '16a766', 'description': 'Can be delegated'},  # Teal
    
    # Relationship Labels - Cool colors
    'EmailAgent/CEO/KeyRelationships': {'color': '8e63ce', 'description': 'Important contacts'},  # Purple (valid)
    'EmailAgent/CEO/Networking': {'color': '1c4587', 'description': 'Network building'},  # Blue (valid)
    'EmailAgent/CEO/Advisors': {'color': '1c4587', 'description': 'Advisor communications'},  # Blue (valid)
    
    # Personal Efficiency - Neutral colors
    'EmailAgent/CEO/QuickWins': {'color': '16a766', 'description': 'Handle in <5 minutes'},  # Green (valid)
    'EmailAgent/CEO/DeepWork': {'color': '8e63ce', 'description': 'Requires focus time'},  # Purple (valid)
    'EmailAgent/CEO/ReadLater': {'color': '999999', 'description': 'Non-urgent info'},  # Light gray
}

def create_ceo_labels():
    """Create all CEO labels in Gmail."""
    console.print(Panel.fit("[bold cyan]🏢 Creating CEO Label System[/bold cyan]", border_style="cyan"))
    
    # Load credentials
    creds_json = keyring.get_password("email_agent", "gmail_credentials_default")
    if not creds_json:
        console.print("[red]❌ No credentials found[/red]")
        return
    
    creds_data = json.loads(creds_json)
    creds = Credentials.from_authorized_user_info(creds_data, [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ])
    
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    
    service = build('gmail', 'v1', credentials=creds)
    
    # Get existing labels
    results = service.users().labels().list(userId='me').execute()
    existing_labels = {label['name']: label['id'] for label in results.get('labels', [])}
    
    # Create results table
    table = Table(title="CEO Label Creation Results", show_header=True, header_style="bold cyan")
    table.add_column("Label", style="cyan", width=35)
    table.add_column("Status", style="green", width=10)
    table.add_column("Description", style="yellow", width=35)
    
    created_count = 0
    existing_count = 0
    
    for label_name, config in CEO_LABELS.items():
        if label_name in existing_labels:
            table.add_row(label_name, "✓ Exists", config['description'])
            existing_count += 1
        else:
            try:
                label_body = {
                    'name': label_name,
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show',
                    'color': {
                        'backgroundColor': f"#{config['color']}",
                        'textColor': '#ffffff'
                    }
                }
                
                result = service.users().labels().create(userId='me', body=label_body).execute()
                table.add_row(label_name, "✅ Created", config['description'])
                created_count += 1
            except Exception as e:
                table.add_row(label_name, "❌ Failed", str(e)[:30] + "...")
    
    console.print("\n")
    console.print(table)
    
    # Summary
    console.print(f"\n[bold green]Summary:[/bold green]")
    console.print(f"  • Created: [green]{created_count}[/green] new labels")
    console.print(f"  • Existing: [yellow]{existing_count}[/yellow] labels already present")
    console.print(f"  • Total: [cyan]{len(CEO_LABELS)}[/cyan] CEO labels available")
    
    # Usage tips
    tips = Panel("""[bold yellow]💡 CEO Label Usage Tips:[/bold yellow]

[bold]Daily Workflow:[/bold]
1. Check [red]DecisionRequired[/red] and [orange]SignatureRequired[/orange] first
2. Handle [cyan]QuickWins[/cyan] during small time gaps
3. Schedule [purple]DeepWork[/purple] items for focused time blocks
4. Review [green]Delegatable[/green] items to pass to team

[bold]Weekly Planning:[/bold]
• Review all [orange]WeeklyReview[/orange] labeled emails
• Check [blue]Investors[/blue] for any pending updates
• Monitor [green]Customers[/green] for trends

[bold]Relationship Management:[/bold]
• Regularly engage with [purple]KeyRelationships[/purple]
• Set reminders for [blue]Networking[/blue] follow-ups
• Keep [light_blue]Advisors[/light_blue] in the loop

[bold]Efficiency Tips:[/bold]
• Use multiple labels on emails (e.g., Investor + DecisionRequired)
• Archive processed emails to keep inbox clean
• Review [gray]ReadLater[/gray] during downtime""", border_style="green")
    
    console.print("\n")
    console.print(tips)

if __name__ == "__main__":
    create_ceo_labels()
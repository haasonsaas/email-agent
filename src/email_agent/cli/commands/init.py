"""Initialization commands for Email Agent."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

from ...config import settings
from ...storage import DatabaseManager

console = Console()
app = typer.Typer()


@app.command()
def setup():
    """Initialize Email Agent with interactive setup."""
    
    console.print(Panel.fit(
        "[bold cyan]Email Agent Setup[/bold cyan]\n"
        "This will guide you through setting up Email Agent for the first time.",
        title="Welcome",
        border_style="cyan"
    ))
    
    # Create data directories
    setup_directories()
    
    # Initialize database
    setup_database()
    
    # Optional: setup first connector
    if Confirm.ask("Would you like to set up your first email connector now?"):
        setup_first_connector()
    
    console.print(Panel.fit(
        "[bold green]Setup Complete![/bold green]\n\n"
        "Next steps:\n"
        "1. Add email connectors: [cyan]email-agent config add-connector[/cyan]\n"
        "2. Pull your first emails: [cyan]email-agent pull[/cyan]\n"
        "3. Generate a daily brief: [cyan]email-agent brief[/cyan]",
        title="Success",
        border_style="green"
    ))


def setup_directories():
    """Create necessary directories."""
    try:
        # Create data directory
        data_dir = settings.data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logs directory
        logs_dir = settings.logs_dir
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create briefs directory
        briefs_dir = settings.briefs_dir
        briefs_dir.mkdir(parents=True, exist_ok=True)
        
        console.print("[green]✓[/green] Created directories:")
        console.print(f"  Data: {data_dir}")
        console.print(f"  Logs: {logs_dir}")
        console.print(f"  Briefs: {briefs_dir}")
        
    except Exception as e:
        console.print(f"[red]Failed to create directories: {str(e)}[/red]")
        raise typer.Exit(1)


def setup_database():
    """Initialize the database."""
    try:
        with console.status("[bold blue]Initializing database..."):
            DatabaseManager()
        
        console.print("[green]✓[/green] Database initialized")
        
    except Exception as e:
        console.print(f"[red]Failed to initialize database: {str(e)}[/red]")
        raise typer.Exit(1)


def setup_first_connector():
    """Setup the first email connector interactively."""
    connector_type = Prompt.ask(
        "Choose connector type",
        choices=["gmail", "outlook", "imap"],
        default="gmail"
    )
    
    if connector_type == "gmail":
        setup_gmail_connector()
    else:
        console.print(f"[yellow]{connector_type} connector setup not yet implemented[/yellow]")


def setup_gmail_connector():
    """Setup Gmail connector."""
    console.print("\n[bold]Gmail Connector Setup[/bold]")
    console.print("You'll need to create a Google Cloud project and enable the Gmail API.")
    console.print("Visit: https://console.cloud.google.com/")
    
    client_id = Prompt.ask("Enter Google Client ID")
    client_secret = Prompt.ask("Enter Google Client Secret", password=True)
    
    if client_id and client_secret:
        # Save to .env file
        env_file = Path(".env")
        
        env_content = []
        if env_file.exists():
            env_content = env_file.read_text().splitlines()
        
        # Update or add Google credentials
        updated = False
        for i, line in enumerate(env_content):
            if line.startswith("GOOGLE_CLIENT_ID="):
                env_content[i] = f"GOOGLE_CLIENT_ID={client_id}"
                updated = True
            elif line.startswith("GOOGLE_CLIENT_SECRET="):
                env_content[i] = f"GOOGLE_CLIENT_SECRET={client_secret}"
                updated = True
        
        if not updated:
            env_content.extend([
                f"GOOGLE_CLIENT_ID={client_id}",
                f"GOOGLE_CLIENT_SECRET={client_secret}"
            ])
        
        env_file.write_text("\n".join(env_content) + "\n")
        console.print("[green]✓[/green] Gmail credentials saved to .env file")
        
        # Test the connector
        if Confirm.ask("Test Gmail connection now?"):
            test_gmail_connection(client_id, client_secret)


def test_gmail_connection(client_id: str, client_secret: str):
    """Test Gmail connector."""
    async def run_test():
        try:
            from ...connectors import GmailConnector
            from ...models import ConnectorConfig
            
            config = ConnectorConfig(
                type="gmail",
                name="test_gmail",
                config={
                    "client_id": client_id,
                    "client_secret": client_secret
                }
            )
            
            connector = GmailConnector(config.config)
            
            with console.status("[bold blue]Testing Gmail connection..."):
                success = await connector.authenticate()
            
            if success:
                console.print("[green]✓[/green] Gmail connection successful!")
            else:
                console.print("[red]✗[/red] Gmail connection failed")
                
        except Exception as e:
            console.print(f"[red]Gmail test failed: {str(e)}[/red]")
    
    asyncio.run(run_test())


@app.command()
def check():
    """Check Email Agent installation and configuration."""
    console.print("[bold]Email Agent Configuration Check[/bold]\n")
    
    checks = [
        ("Data directory", check_data_directory),
        ("Database", check_database),
        ("Environment variables", check_environment),
        ("Connectors", check_connectors),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            if result:
                console.print(f"[green]✓[/green] {check_name}")
            else:
                console.print(f"[red]✗[/red] {check_name}")
                all_passed = False
        except Exception as e:
            console.print(f"[red]✗[/red] {check_name}: {str(e)}")
            all_passed = False
    
    if all_passed:
        console.print("\n[bold green]All checks passed![/bold green]")
    else:
        console.print("\n[bold red]Some checks failed. Run 'email-agent init setup' to fix issues.[/bold red]")


def check_data_directory() -> bool:
    """Check if data directory exists."""
    return settings.data_dir.exists()


def check_database() -> bool:
    """Check if database is accessible."""
    try:
        db = DatabaseManager()
        db.get_email_stats()
        return True
    except Exception:
        return False


def check_environment() -> bool:
    """Check environment configuration."""
    # Check for at least one API key
    return bool(settings.openai_api_key or settings.anthropic_api_key)


def check_connectors() -> bool:
    """Check if connectors are configured."""
    try:
        db = DatabaseManager()
        configs = db.get_connector_configs()
        return len(configs) > 0
    except Exception:
        return False


@app.command()
def reset(
    confirm: bool = typer.Option(
        False,
        "--yes",
        help="Skip confirmation prompt"
    )
):
    """Reset Email Agent configuration (WARNING: This deletes all data)."""
    
    if not confirm:
        console.print("[bold red]WARNING: This will delete all Email Agent data![/bold red]")
        if not Confirm.ask("Are you sure you want to reset everything?"):
            console.print("Reset cancelled.")
            return
    
    try:
        # Remove data directory
        import shutil
        if settings.data_dir.exists():
            shutil.rmtree(settings.data_dir)
            console.print(f"[green]✓[/green] Removed data directory: {settings.data_dir}")
        
        # Remove .env file if it exists
        env_file = Path(".env")
        if env_file.exists():
            env_file.unlink()
            console.print("[green]✓[/green] Removed .env file")
        
        console.print("[bold green]Reset complete![/bold green]")
        console.print("Run 'email-agent init setup' to initialize again.")
        
    except Exception as e:
        console.print(f"[red]Reset failed: {str(e)}[/red]")
        raise typer.Exit(1)
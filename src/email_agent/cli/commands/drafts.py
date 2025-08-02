"""CLI commands for AI draft suggestions."""

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...agents.crew import EmailAgentCrew
from ...storage.database import DatabaseManager

console = Console()
app = typer.Typer()


@app.command()
def generate(
    email_id: str = typer.Option(..., help="ID of the email to respond to"),
    num_suggestions: int = typer.Option(
        3, help="Number of draft suggestions to generate"
    ),
    context: str = typer.Option(
        "reply", help="Context for the draft (reply, forward, new)"
    ),
):
    """Generate draft suggestions for responding to an email."""
    asyncio.run(_generate_drafts(email_id, num_suggestions, context))


@app.command()
def analyze_style(
    force_refresh: bool = typer.Option(
        False, "--force-refresh", help="Force refresh of writing style analysis"
    ),
    min_emails: int = typer.Option(10, help="Minimum number of sent emails to analyze"),
):
    """Analyze your writing style from sent emails."""
    asyncio.run(_analyze_writing_style(force_refresh, min_emails))


@app.command()
def style_summary():
    """Show summary of current writing style analysis."""
    asyncio.run(_show_style_summary())


@app.command()
def use_draft(
    email_id: str = typer.Option(..., help="ID of the email to respond to"),
    draft_index: int = typer.Option(
        0, help="Index of the draft suggestion to use (0-based)"
    ),
):
    """Use a draft suggestion and copy it to clipboard or save as draft."""
    asyncio.run(_use_draft_suggestion(email_id, draft_index))


async def _generate_drafts(email_id: str, num_suggestions: int, context: str):
    """Generate draft suggestions for an email."""
    try:
        db = DatabaseManager()
        email = db.get_email_by_id(email_id)

        if not email:
            console.print(f"[red]Email not found: {email_id}[/red]")
            return

        console.print(
            f"[blue]Generating {num_suggestions} draft suggestions for:[/blue]"
        )
        console.print(f"  Subject: {email.subject}")
        console.print(f"  From: {email.sender}")
        console.print(f"  Context: {context}")
        console.print()

        # Initialize crew and generate drafts
        crew = EmailAgentCrew()
        await crew.initialize_crew({})

        with console.status("[bold green]Generating draft suggestions..."):
            results = await crew.execute_task(
                "generate_drafts",
                original_email=email,
                context=context,
                num_suggestions=num_suggestions,
            )

        if "error" in results:
            console.print(f"[red]Error: {results['error']}[/red]")
            return

        # Display suggestions
        suggestions = results.get("suggestions", [])

        if not suggestions:
            console.print("[yellow]No draft suggestions generated.[/yellow]")
            return

        console.print(f"[green]Generated {len(suggestions)} draft suggestions:[/green]")
        console.print()

        for i, suggestion in enumerate(suggestions):
            # Create suggestion panel
            suggestion_content = []
            suggestion_content.append(f"[bold]Subject:[/bold] {suggestion['subject']}")
            suggestion_content.append("")
            suggestion_content.append("[bold]Body:[/bold]")
            suggestion_content.append(suggestion["body"])
            suggestion_content.append("")
            suggestion_content.append(
                f"[dim]Confidence: {suggestion['confidence']:.2f} | Style Match: {suggestion['style_match']:.2f}[/dim]"
            )
            suggestion_content.append(
                f"[dim]Tone: {suggestion['suggested_tone']} | Length: {suggestion['estimated_length']}[/dim]"
            )
            suggestion_content.append(
                f"[dim]Reasoning: {suggestion['reasoning']}[/dim]"
            )

            panel = Panel(
                "\n".join(suggestion_content),
                title=f"Draft Suggestion #{i+1}",
                border_style="blue" if i == 0 else "white",
            )
            console.print(panel)
            console.print()

        # Show usage tip
        console.print(
            f"[dim]Tip: Use 'email-agent drafts use-draft --email-id {email_id} --draft-index <0-{len(suggestions)-1}>' to use a suggestion[/dim]"
        )

        await crew.shutdown()

    except Exception as e:
        console.print(f"[red]Error generating drafts: {str(e)}[/red]")


async def _analyze_writing_style(force_refresh: bool, min_emails: int):
    """Analyze writing style from sent emails."""
    try:
        db = DatabaseManager()

        console.print(
            "[blue]Retrieving sent emails for writing style analysis...[/blue]"
        )

        # Get sent emails (this would need to be implemented in DatabaseManager)
        # For now, we'll simulate getting sent emails
        sent_emails = db.get_sent_emails(
            limit=100
        )  # This method needs to be implemented

        if len(sent_emails) < min_emails:
            console.print(
                f"[yellow]Only {len(sent_emails)} sent emails found. Need at least {min_emails} for accurate analysis.[/yellow]"
            )
            if len(sent_emails) == 0:
                console.print(
                    "[red]No sent emails found. Make sure you have sent emails synced.[/red]"
                )
                return

        console.print(
            f"[green]Found {len(sent_emails)} sent emails for analysis[/green]"
        )

        # Initialize crew and analyze style
        crew = EmailAgentCrew()
        await crew.initialize_crew({})

        with console.status("[bold green]Analyzing writing style..."):
            results = await crew.execute_task(
                "analyze_writing_style",
                sent_emails=sent_emails,
                force_refresh=force_refresh,
            )

        if "error" in results:
            console.print(f"[red]Error: {results['error']}[/red]")
            return

        # Display analysis results
        console.print("[green]Writing Style Analysis Complete![/green]")
        console.print()

        # Create analysis table
        table = Table(title="Writing Style Profile")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Description", style="dim")

        table.add_row(
            "Average Length", f"{results['avg_length']} words", "Typical email length"
        )
        table.add_row(
            "Formality Score",
            f"{results['formality_score']:.2f}/1.0",
            "0=casual, 1=formal",
        )
        table.add_row(
            "Greeting Style", results["greeting_style"], "Most common greeting"
        )
        table.add_row("Closing Style", results["closing_style"], "Most common closing")
        table.add_row(
            "Sentence Complexity",
            f"{results['sentence_complexity']:.2f}/1.0",
            "0=simple, 1=complex",
        )

        console.print(table)
        console.print()

        # Show common phrases
        if results.get("common_phrases"):
            console.print("[bold]Common Phrases:[/bold]")
            for phrase in results["common_phrases"][:5]:
                console.print(f"  • {phrase}")
            console.print()

        # Show tone keywords
        if results.get("tone_keywords"):
            console.print("[bold]Tone Keywords:[/bold]")
            for keyword in results["tone_keywords"][:8]:
                console.print(f"  • {keyword}")
            console.print()

        # Show preferred times
        if results.get("preferred_times"):
            console.print("[bold]Preferred Sending Times:[/bold]")
            times = [f"{hour}:00" for hour in results["preferred_times"]]
            console.print(f"  {', '.join(times)}")
            console.print()

        console.print(
            "[green]Writing style analysis saved. Draft suggestions will now be personalized![/green]"
        )

        await crew.shutdown()

    except Exception as e:
        console.print(f"[red]Error analyzing writing style: {str(e)}[/red]")


async def _show_style_summary():
    """Show summary of current writing style analysis."""
    try:
        crew = EmailAgentCrew()
        await crew.initialize_crew({})

        # Get style summary
        summary = crew.draft_agent.get_style_summary()

        if summary.get("status") == "not_analyzed":
            console.print("[yellow]Writing style not yet analyzed.[/yellow]")
            console.print(
                "Run 'email-agent drafts analyze-style' to analyze your writing style."
            )
            return

        console.print("[green]Current Writing Style Summary:[/green]")
        console.print()

        # Create summary table
        table = Table(title="Writing Style Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Status", summary.get("status", "unknown"))
        table.add_row("Last Updated", summary.get("last_updated", "unknown"))
        table.add_row("Average Length", f"{summary.get('avg_length', 0)} words")
        table.add_row("Formality Score", f"{summary.get('formality_score', 0):.2f}/1.0")
        table.add_row("Greeting Style", summary.get("greeting_style", "unknown"))
        table.add_row("Closing Style", summary.get("closing_style", "unknown"))
        table.add_row(
            "Sentence Complexity", f"{summary.get('sentence_complexity', 0):.2f}/1.0"
        )
        table.add_row("Common Phrases", str(summary.get("common_phrases_count", 0)))
        table.add_row("Tone Keywords", str(summary.get("tone_keywords_count", 0)))
        table.add_row("Preferred Times", str(summary.get("preferred_times", [])))

        console.print(table)

        await crew.shutdown()

    except Exception as e:
        console.print(f"[red]Error showing style summary: {str(e)}[/red]")


async def _use_draft_suggestion(email_id: str, draft_index: int):
    """Use a draft suggestion."""
    try:
        db = DatabaseManager()
        email = db.get_email_by_id(email_id)

        if not email:
            console.print(f"[red]Email not found: {email_id}[/red]")
            return

        # Generate drafts first
        crew = EmailAgentCrew()
        await crew.initialize_crew({})

        with console.status("[bold green]Generating draft suggestions..."):
            results = await crew.execute_task(
                "generate_drafts",
                original_email=email,
                context="reply",
                num_suggestions=max(3, draft_index + 1),
            )

        if "error" in results:
            console.print(f"[red]Error: {results['error']}[/red]")
            return

        suggestions = results.get("suggestions", [])

        if draft_index >= len(suggestions):
            console.print(
                f"[red]Draft index {draft_index} not available. Only {len(suggestions)} suggestions generated.[/red]"
            )
            return

        suggestion = suggestions[draft_index]

        # Display the selected draft
        console.print(f"[green]Using Draft Suggestion #{draft_index + 1}:[/green]")
        console.print()

        draft_content = []
        draft_content.append(f"[bold]Subject:[/bold] {suggestion['subject']}")
        draft_content.append("")
        draft_content.append("[bold]Body:[/bold]")
        draft_content.append(suggestion["body"])

        panel = Panel(
            "\n".join(draft_content), title="Selected Draft", border_style="green"
        )
        console.print(panel)
        console.print()

        # Try to copy to clipboard (optional)
        try:
            import pyperclip

            draft_text = f"Subject: {suggestion['subject']}\n\n{suggestion['body']}"
            pyperclip.copy(draft_text)
            console.print("[green]Draft copied to clipboard![/green]")
        except ImportError:
            console.print(
                "[dim]Install 'pyperclip' to enable clipboard functionality[/dim]"
            )
        except Exception:
            console.print("[yellow]Could not copy to clipboard[/yellow]")

        # Optionally save as draft in email system (would need implementation)
        console.print(
            "[dim]To save as draft in your email client, copy the content above.[/dim]"
        )

        await crew.shutdown()

    except Exception as e:
        console.print(f"[red]Error using draft suggestion: {str(e)}[/red]")

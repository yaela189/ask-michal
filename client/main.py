# -*- coding: utf-8 -*-
import sys

import click

from client.auth import login, load_token, clear_token
from client.api import MichalClient
from client.ui import (
    console,
    bidi,
    display_welcome,
    display_answer,
    display_error,
    get_question,
    display_thinking,
)

DEFAULT_SERVER = "http://localhost:8000"


@click.group()
@click.option(
    "--server",
    default=DEFAULT_SERVER,
    envvar="MICHAL_SERVER_URL",
    help="Server URL",
)
@click.pass_context
def cli(ctx, server):
    """Ask Michal - AI HR Assistant for Division 96"""
    ctx.ensure_object(dict)
    ctx.obj["server"] = server


@cli.command()
@click.pass_context
def auth(ctx):
    """Login with Google account."""
    try:
        console.print(bidi("מפנה לדפדפן להתחברות עם Google..."))
        login(ctx.obj["server"])
        console.print(f"[green]{bidi('התחברת בהצלחה!')}[/green]")
    except Exception as e:
        display_error(f"שגיאה בהתחברות: {e}")
        sys.exit(1)


@cli.command()
def logout():
    """Clear saved authentication."""
    clear_token()
    console.print(f"[yellow]{bidi('התנתקת מהמערכת.')}[/yellow]")


@cli.command()
@click.pass_context
def chat(ctx):
    """Start interactive chat with Michal."""
    token = load_token()
    if not token:
        display_error("יש להתחבר תחילה. הרץ: ask-michal auth")
        sys.exit(1)

    client = MichalClient(ctx.obj["server"])

    try:
        quota = client.get_quota()
        display_welcome("", quota["queries_remaining"])
    except Exception:
        display_error("שגיאה בהתחברות לשרת. ודא/י שהשרת פעיל ושהתחברת.")
        sys.exit(1)

    console.print(f"[dim]{bidi('הקלד/י יציאה לצאת.')}[/dim]\n")

    while True:
        try:
            question = get_question()

            if question.strip() in ("יציאה", "exit", "quit", "q"):
                console.print(f"[cyan]{bidi('להתראות!')}[/cyan]")
                break

            if not question.strip():
                continue

            with display_thinking():
                result = client.ask(question)

            display_answer(
                result["answer"],
                result["sources"],
                result["queries_remaining"],
            )

        except KeyboardInterrupt:
            console.print(f"\n[cyan]{bidi('להתראות!')}[/cyan]")
            break
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                display_error("מכסת השאלות שלך נגמרה. פנה/י למנהל המערכת.")
            elif "401" in error_msg:
                display_error("הטוקן פג תוקף. הרץ: ask-michal auth")
                break
            else:
                display_error(f"שגיאה: {error_msg}")


@cli.command()
@click.pass_context
def quota(ctx):
    """Check remaining query quota."""
    token = load_token()
    if not token:
        display_error("יש להתחבר תחילה.")
        sys.exit(1)

    client = MichalClient(ctx.obj["server"])

    try:
        result = client.get_quota()
        console.print(bidi(f"שאלות נותרות: {result['queries_remaining']}"))
        console.print(bidi(f"שאלות ששאלת: {result['queries_used']}"))
    except Exception as e:
        display_error(f"שגיאה: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()

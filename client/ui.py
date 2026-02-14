# -*- coding: utf-8 -*-
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()


def bidi(text: str) -> str:
    """Apply BiDi reordering for terminal display of Hebrew text."""
    try:
        from bidi.algorithm import get_display

        lines = text.split("\n")
        processed = []
        for line in lines:
            if any("\u0590" <= c <= "\u05FF" for c in line):
                processed.append(get_display(line))
            else:
                processed.append(line)
        return "\n".join(processed)
    except ImportError:
        return text


def display_welcome(name: str, quota: int):
    welcome = bidi(f"שלום {name}! אני מיכל, קצינת השלישות הווירטואלית שלך.")
    quota_text = bidi(f"נותרו לך {quota} שאלות.")

    console.print(
        Panel(
            f"[bold cyan]{welcome}[/bold cyan]\n{quota_text}",
            title=bidi("שאלי את מיכל"),
            border_style="cyan",
        )
    )


def display_answer(answer: str, sources: list[str], queries_remaining: int):
    display_text = bidi(answer)

    console.print(
        Panel(
            display_text,
            title=bidi("מיכל"),
            border_style="green",
            padding=(1, 2),
        )
    )

    if sources:
        source_text = " | ".join(bidi(s) for s in sources)
        console.print(f"[dim]{bidi('מקורות:')} {source_text}[/dim]")

    console.print(f"[dim]{bidi(f'שאלות נותרות: {queries_remaining}')}[/dim]\n")


def display_error(message: str):
    console.print(
        Panel(
            bidi(message),
            title=bidi("שגיאה"),
            border_style="red",
        )
    )


def get_question() -> str:
    return Prompt.ask(f"[cyan]{bidi('שאלה')}[/cyan]")


def display_thinking():
    return Live(
        Panel(bidi("מיכל חושבת..."), border_style="yellow"),
        refresh_per_second=4,
    )


def prompt_rating() -> int | None:
    value = Prompt.ask(
        f"[dim]{bidi('דרג/י את התשובה (1-5, Enter לדילוג)')}[/dim]",
        default="",
    )
    if not value.strip():
        return None
    try:
        rating = int(value)
        if 1 <= rating <= 5:
            return rating
    except ValueError:
        pass
    console.print(f"[dim]{bidi('דירוג לא תקין, מדלג.')}[/dim]")
    return None


def prompt_rating_comment() -> str | None:
    value = Prompt.ask(
        f"[dim]{bidi('הערה (Enter לדילוג)')}[/dim]",
        default="",
    )
    return value.strip() or None


def display_rating_thanks(queries_remaining: int):
    console.print(f"[green]{bidi('תודה על הדירוג!')}[/green]")
    console.print(f"[dim]{bidi(f'שאלות נותרות: {queries_remaining}')}[/dim]\n")

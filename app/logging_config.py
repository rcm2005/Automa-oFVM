"""Logging com Rich (terminal colorido) + arquivo rotativo."""
import logging
import logging.handlers
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

_THEME = Theme({
    "logging.level.info":    "bold cyan",
    "logging.level.warning": "bold yellow",
    "logging.level.error":   "bold red",
    "logging.level.critical":"bold white on red",
})

_console = Console(theme=_THEME)


def setup(logs_dir: Path, level: int = logging.INFO) -> None:
    logs_dir.mkdir(exist_ok=True)

    rich_handler = RichHandler(
        console=_console,
        show_path=False,
        rich_tracebacks=True,
        markup=True,
    )
    rich_handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%H:%M:%S]"))

    file_fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(file_fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(rich_handler)
    root.addHandler(file_handler)

    # webdriver_manager loga caminhos com colchetes que o Rich interpreta como markup
    logging.getLogger("WDM").setLevel(logging.WARNING)

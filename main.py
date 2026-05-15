"""Ponto de entrada: banner, logging, listener de teclado e servidor FastAPI."""
import json
import logging
import threading

import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from app import config
from app.logging_config import setup as setup_logging

console = Console()
logger  = logging.getLogger(__name__)


def _banner() -> None:
    next_run = "—"
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        tmp = BackgroundScheduler(timezone="America/Sao_Paulo")
        tmp.add_job(lambda: None, CronTrigger(
            day_of_week=config.SCHEDULE_DAY_OF_WEEK,
            hour=config.SCHEDULE_HOUR,
            minute=config.SCHEDULE_MINUTE,
            timezone="America/Sao_Paulo",
        ), id="x")
        tmp.start()
        next_run = tmp.get_job("x").next_run_time.strftime("%d/%m/%Y %H:%M")
        tmp.shutdown(wait=False)
    except Exception:
        pass

    state = {}
    if config.STATE_FILE.exists():
        state = json.loads(config.STATE_FILE.read_text())

    title = Text("⚡  AUTOMAÇÃO FVM  ⚡", style="bold white")
    body = (
        f"[bold cyan]Sistema:[/]  {config.SYSTEM_URL}\n"
        f"[bold cyan]Schedule:[/] toda segunda-feira às {config.SCHEDULE_HOUR:02d}:{config.SCHEDULE_MINUTE:02d}\n"
        f"[bold cyan]Próxima: [/] {next_run}\n"
        f"[bold cyan]Último:  [/] {state.get('last_extraction_date', '—')}  |  status: {state.get('last_status', '—')}\n\n"
        "[dim]Pressione [bold]R + Enter[/bold] para disparar agora  •  [bold]Q + Enter[/bold] para sair[/dim]"
    )
    console.print(Panel(body, title=title, border_style="green", padding=(1, 4)))


def _keyboard_listener() -> None:
    """Lê stdin em loop — 'r' dispara job, 'q' encerra."""
    from app.job import run_job
    while True:
        try:
            cmd = input().strip().lower()
        except EOFError:
            break
        if cmd == "r":
            logger.info("[bold green]Trigger manual via teclado[/]")
            threading.Thread(target=_safe_run_job, daemon=True).start()
        elif cmd == "q":
            logger.info("Encerrando por comando do usuário")
            import os, signal
            os.kill(os.getpid(), signal.SIGTERM)


def _safe_run_job() -> None:
    from app.job import run_job
    try:
        run_job()
    except Exception:
        logger.exception("Erro no job")


if __name__ == "__main__":
    setup_logging(config.LOGS_DIR)
    _banner()

    kb = threading.Thread(target=_keyboard_listener, daemon=True)
    kb.start()

    uvicorn.run(
        "app.server:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
        log_config=None,
    )

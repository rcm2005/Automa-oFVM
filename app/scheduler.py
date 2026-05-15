"""APScheduler: job semanal toda segunda-feira às 09:00 (Brasília)."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app import config
from app.job import run_job

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")


def start_scheduler() -> None:
    _scheduler.add_job(
        run_job,
        trigger=CronTrigger(
            day_of_week=config.SCHEDULE_DAY_OF_WEEK,
            hour=config.SCHEDULE_HOUR,
            minute=config.SCHEDULE_MINUTE,
            timezone="America/Sao_Paulo",
        ),
        id="weekly_report",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    next_run = _scheduler.get_job("weekly_report").next_run_time
    logger.info("Scheduler ativo — próxima execução: %s", next_run.strftime("%d/%m/%Y %H:%M"))


def stop_scheduler() -> None:
    _scheduler.shutdown(wait=False)
    logger.info("Scheduler encerrado")

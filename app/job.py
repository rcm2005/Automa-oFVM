"""Pipeline: lê estado → scraping → transforma → salva .xlsx → entrega → atualiza estado."""
import json
import logging
from datetime import date, timedelta

from app import config
from app import deliver as dlv
from app import transform, worker

logger = logging.getLogger(__name__)


def _load_state() -> dict:
    if config.STATE_FILE.exists():
        return json.loads(config.STATE_FILE.read_text())
    return {"last_extraction_date": None}


def _save_state(last: date, status: str) -> None:
    config.STATE_FILE.write_text(
        json.dumps(
            {
                "last_extraction_date": last.isoformat(),
                "last_run_at": date.today().isoformat(),
                "last_status": status,
            },
            indent=2,
        )
    )


def run_job() -> dict:
    state = _load_state()
    today = date.today()

    if state["last_extraction_date"]:
        start = date.fromisoformat(state["last_extraction_date"]) + timedelta(days=1)
    else:
        start = today - timedelta(days=7)

    end = today - timedelta(days=1)

    if start > end:
        logger.info("Nada a extrair: start=%s > end=%s (último=%s)", start, end, state["last_extraction_date"])
        return {"skipped": True, "reason": "no_new_data"}

    logger.info("Iniciando job %s → %s", start, end)

    df = worker.run(start, end)
    df = transform.normalize(df)

    filename = f"Treinamentos_{start.strftime('%d-%m-%Y')}_a_{end.strftime('%d-%m-%Y')}"
    xlsx_path = config.REPORTS_DIR / f"{filename}.xlsx"
    df.to_excel(xlsx_path, index=False, engine="openpyxl")
    logger.info("Relatório salvo: %s (%d registros)", xlsx_path.name, len(df))

    subject = f"Relatório FVM — {start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')}"
    body = (
        f"Período: {start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')}\n"
        f"Registros: {len(df)}\n\n"
        "Planilha Excel em anexo."
    )
    statuses = dlv.deliver(subject, body, attachment=xlsx_path)
    all_ok = all(statuses.values())

    if any(statuses.values()):
        _save_state(end, "ok" if all_ok else "partial")
    else:
        _save_state(end, "delivery_failed")

    result = {"start": start.isoformat(), "end": end.isoformat(), "rows": len(df), **statuses}
    logger.info("Job concluído: %s", result)
    return result

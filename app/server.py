"""FastAPI: /health, /trigger — ponto de entrada do serviço."""
import hashlib
import hmac
import logging
import threading
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request, status

from app import config
from app.job import run_job
from app.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)

_job_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Automação FVM", lifespan=lifespan)


def _verify_token(token: str) -> bool:
    """Compara em tempo constante para evitar timing attacks."""
    expected = hmac.new(
        config.TRIGGER_SECRET.encode(),
        b"fvm-trigger",
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(token, expected)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/trigger")
async def trigger(x_trigger_token: str = Header(...)):
    if not _verify_token(x_trigger_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    if not _job_lock.acquire(blocking=False):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job já em execução")

    def _run():
        try:
            run_job()
        except Exception:
            logger.exception("Erro no job disparado manualmente")
        finally:
            _job_lock.release()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return {"status": "job_started"}


if __name__ == "__main__":
    uvicorn.run("app.server:app", host=config.HOST, port=config.PORT, reload=False)

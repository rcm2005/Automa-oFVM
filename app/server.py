"""FastAPI: /health, /trigger — ponto de entrada do serviço."""
import hashlib
import hmac
import json
import logging
import threading
from contextlib import asynccontextmanager
from datetime import date

import uvicorn
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app import config
from app.job import run_job, run_job_for_period
from app.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)

_job_lock = threading.Lock()
_job_status = {
    "running": False,
    "last_result": None,
    "last_error": None,
}


MANUAL_PAGE = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FVM Automation</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: #0a0a0a;
      color: #e5e5e5;
      font-family: 'Courier New', monospace;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem 1rem;
    }
    main {
      width: 100%;
      max-width: 720px;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }
    header {
      border-bottom: 1px solid #1a1a1a;
      padding-bottom: 1.2rem;
    }
    h1 {
      margin: 0 0 0.35rem;
      font-size: 2.6rem;
      font-weight: 400;
    }
    header span {
      color: #7f93ff;
      font-size: 0.9rem;
    }
    form, .status {
      border: 1px solid #1a1a1a;
      padding: 1.4rem;
      background: #0d0d0d;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.8rem;
    }
    label {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      color: #666;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    input, button {
      min-height: 2.7rem;
      border: 1px solid #2a2a2a;
      background: #080808;
      color: #e5e5e5;
      font-family: 'Courier New', monospace;
      font-size: 0.95rem;
      padding: 0 0.8rem;
    }
    input:focus {
      outline: none;
      border-color: #7f93ff;
    }
    button {
      width: 100%;
      margin-top: 1rem;
      color: #7f93ff;
      cursor: pointer;
      text-transform: lowercase;
    }
    button:hover:not(:disabled) {
      border-color: #7f93ff;
      color: #aab4ff;
    }
    button:disabled {
      cursor: wait;
      color: #444;
    }
    .status {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      font-size: 0.88rem;
    }
    .item span {
      display: block;
      color: #555;
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 0.25rem;
    }
    .item strong {
      color: #ddd;
      font-weight: 400;
      overflow-wrap: anywhere;
    }
    .message {
      color: #888;
      min-height: 1.5rem;
      line-height: 1.6;
    }
    .message.ok { color: #4ade80; }
    .message.err { color: #ff7f7f; }
    @media (max-width: 620px) {
      h1 { font-size: 2.1rem; }
      .grid, .status { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>FVM Automation</h1>
      <span>geracao manual de relatorio</span>
    </header>

    <form id="manual-form">
      <div class="grid">
        <label>
          data inicio
          <input type="date" id="start-date" required>
        </label>
        <label>
          data fim
          <input type="date" id="end-date" required>
        </label>
      </div>
      <button type="submit" id="generate-button">[ gerar ]</button>
    </form>

    <div class="message" id="message"></div>

    <section class="status">
      <div class="item">
        <span>em execucao</span>
        <strong id="running">--</strong>
      </div>
      <div class="item">
        <span>ultimo periodo</span>
        <strong id="last-period">--</strong>
      </div>
      <div class="item">
        <span>ultima data no json</span>
        <strong id="last-date">--</strong>
      </div>
      <div class="item">
        <span>ultimo status</span>
        <strong id="last-status">--</strong>
      </div>
    </section>
  </main>

  <script>
    const refs = {
      form: document.getElementById("manual-form"),
      start: document.getElementById("start-date"),
      end: document.getElementById("end-date"),
      button: document.getElementById("generate-button"),
      message: document.getElementById("message"),
      running: document.getElementById("running"),
      lastPeriod: document.getElementById("last-period"),
      lastDate: document.getElementById("last-date"),
      lastStatus: document.getElementById("last-status"),
    };

    function isoDate(date) {
      return date.toISOString().slice(0, 10);
    }

    function setMessage(text, kind = "") {
      refs.message.textContent = text;
      refs.message.className = `message ${kind}`;
    }

    function setDefaultDates() {
      const end = new Date();
      end.setDate(end.getDate() - 1);
      const start = new Date(end);
      start.setDate(start.getDate() - 6);
      refs.start.value = isoDate(start);
      refs.end.value = isoDate(end);
    }

    async function refreshStatus() {
      const response = await fetch("/state", { cache: "no-store" });
      const data = await response.json();
      refs.running.textContent = data.running ? "sim" : "nao";
      refs.lastDate.textContent = data.state.last_extraction_date || "--";
      refs.lastStatus.textContent = data.state.last_status || "--";

      if (data.last_result && data.last_result.start && data.last_result.end) {
        refs.lastPeriod.textContent = `${data.last_result.start} a ${data.last_result.end}`;
      } else {
        refs.lastPeriod.textContent = "--";
      }
    }

    refs.form.addEventListener("submit", async (event) => {
      event.preventDefault();
      refs.button.disabled = true;
      setMessage("iniciando job...");

      try {
        const response = await fetch("/manual-run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            start_date: refs.start.value,
            end_date: refs.end.value,
          }),
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || "falha ao iniciar");
        }
        setMessage(`job iniciado: ${data.start} a ${data.end}`, "ok");
        await refreshStatus();
      } catch (error) {
        setMessage(error.message, "err");
      } finally {
        refs.button.disabled = false;
      }
    });

    setDefaultDates();
    refreshStatus().catch(() => setMessage("nao foi possivel carregar status", "err"));
    setInterval(refreshStatus, 5000);
  </script>
</body>
</html>"""


class ManualRunRequest(BaseModel):
    start_date: date
    end_date: date


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


@app.get("/", response_class=HTMLResponse)
async def manual_page():
    return MANUAL_PAGE


@app.get("/state")
async def state():
    current_state = {}
    if config.STATE_FILE.exists():
        try:
            current_state = json.loads(config.STATE_FILE.read_text())
        except json.JSONDecodeError:
            current_state = {"error": "state.json invalido"}
    return {
        "running": _job_status["running"],
        "last_result": _job_status["last_result"],
        "last_error": _job_status["last_error"],
        "state": current_state,
    }


def _start_background_job(target, error_label: str) -> None:
    if not _job_lock.acquire(blocking=False):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job já em execução")

    _job_status["running"] = True
    _job_status["last_error"] = None

    def _run():
        try:
            _job_status["last_result"] = target()
        except Exception as exc:
            _job_status["last_error"] = str(exc)
            logger.exception(error_label)
        finally:
            _job_status["running"] = False
            _job_lock.release()

    t = threading.Thread(target=_run, daemon=True)
    t.start()


@app.post("/manual-run")
async def manual_run(payload: ManualRunRequest):
    if payload.start_date > payload.end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Data inicial maior que data final")

    _start_background_job(
        lambda: run_job_for_period(payload.start_date, payload.end_date, mode="manual"),
        "Erro no job disparado pela pagina manual",
    )
    return {
        "status": "job_started",
        "start": payload.start_date.isoformat(),
        "end": payload.end_date.isoformat(),
    }


@app.post("/trigger")
async def trigger(x_trigger_token: str = Header(...)):
    if not _verify_token(x_trigger_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    _start_background_job(run_job, "Erro no job disparado manualmente")
    return {"status": "job_started"}


if __name__ == "__main__":
    uvicorn.run("app.server:app", host=config.HOST, port=config.PORT, reload=False)

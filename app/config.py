import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Sistema alvo
SYSTEM_URL = os.environ["SYSTEM_URL"]
SYSTEM_USERNAME = os.environ["SYSTEM_USERNAME"]
SYSTEM_PASSWORD = os.environ["SYSTEM_PASSWORD"]

# Segurança do endpoint /trigger
TRIGGER_SECRET = os.environ["TRIGGER_SECRET"]

# SMTP
SMTP_HOST = os.environ["SMTP_HOST"]
SMTP_PORT = int(os.environ["SMTP_PORT"])
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"]

# Telegram
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Servidor
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# Scheduler
SCHEDULE_DAY_OF_WEEK = os.getenv("SCHEDULE_DAY_OF_WEEK", "mon")
SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", 9))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", 0))

# Chrome (ajuste no .env conforme o ambiente)
CHROME_BINARY     = os.getenv("CHROME_BINARY", "/snap/bin/chromium")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/snap/bin/chromium.chromedriver")

# Caminhos
BASE_DIR = Path(__file__).parent.parent
STATE_FILE = BASE_DIR / "state.json"
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"

REPORTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

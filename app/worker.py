"""Selenium worker: login → relatorio_cursos → preenche datas → extrai tabela."""
import logging
from datetime import date
from io import StringIO

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app import config

logger = logging.getLogger(__name__)

BASE = "https://www.fvmconsultoria.com.br/sistema"
LOGIN_URL   = f"{BASE}/login.php"
REPORT_URL  = f"{BASE}/relatorio_cursos.php"
RESULT_URL  = f"{BASE}/relatorio_resultados.php"

WAIT = 20


def _build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    service = Service(config.CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=opts)


def _screenshot(driver: webdriver.Chrome, name: str) -> None:
    from app import config
    path = config.REPORTS_DIR / f"debug_{name}.png"
    driver.save_screenshot(str(path))
    logger.info("Screenshot: %s", path.name)


def _login(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    driver.get(LOGIN_URL)
    wait.until(EC.presence_of_element_located((By.ID, "usuario")))
    driver.find_element(By.ID, "usuario").send_keys(config.SYSTEM_USERNAME)
    driver.find_element(By.ID, "senha").send_keys(config.SYSTEM_PASSWORD)
    driver.find_element(By.NAME, "acesso").click()
    # Sidebar aparece somente após login bem-sucedido
    wait.until(EC.presence_of_element_located((By.ID, "side-menu")))
    logger.info("Login OK")


def _generate_report(driver: webdriver.Chrome, wait: WebDriverWait, start: date, end: date) -> str:
    driver.get(REPORT_URL)
    wait.until(EC.presence_of_element_located((By.ID, "start_date")))

    # Inputs type="date" esperam YYYY-MM-DD
    start_el = driver.find_element(By.ID, "start_date")
    end_el = driver.find_element(By.ID, "end_date")
    for el, val in [(start_el, start.strftime("%Y-%m-%d")), (end_el, end.strftime("%Y-%m-%d"))]:
        driver.execute_script(
            "arguments[0].value = arguments[1];"
            "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));"
            "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));",
            el, val,
        )
    # instrutor e empresa ficam vazios

    _screenshot(driver, f"antes_submit_{start}_{end}")

    # Submit do form que posta para relatorio_resultados.php
    driver.find_element(By.CSS_SELECTOR, "form[action='relatorio_resultados.php'] button[type='submit']").click()

    wait.until(EC.url_contains("relatorio_resultados.php"))
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-striped")))
    _screenshot(driver, f"resultado_{start}_{end}")
    logger.info("Relatório gerado: %s → %s", start, end)
    return driver.find_element(By.CSS_SELECTOR, "table.table-striped").get_attribute("outerHTML")


def run(start: date, end: date) -> pd.DataFrame:
    logger.info("Worker iniciado: %s → %s", start, end)
    driver = _build_driver()
    try:
        wait = WebDriverWait(driver, WAIT)
        _login(driver, wait)
        html = _generate_report(driver, wait, start, end)
    finally:
        driver.quit()

    tables = pd.read_html(StringIO(html))
    if not tables:
        raise ValueError("Tabela não encontrada na página de resultados")

    df = tables[0]
    logger.info("Extraídas %d linhas × %d colunas", *df.shape)
    return df

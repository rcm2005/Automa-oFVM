"""Transforma o DataFrame bruto extraído do sistema para o formato Excel da FVM."""
import logging
import re
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

# Palavras-chave que identificam RECICLAGEM no nome do curso
_RECICLAGEM = re.compile(r"reciclag", re.IGNORECASE)

# Palavras-chave que identificam FORMAÇÃO (tudo que não é reciclagem nem capacitação pura)
_FORMACAO = re.compile(
    r"NR[\s\-]*35|TRABALHO EM ALTURA|AJUDANTE|NOVO FORMATO|FORMAÇÃO|FORMACAO",
    re.IGNORECASE,
)

# Regex para extrair datas no padrão dd/mm/yyyy
_DATE_RE = re.compile(r"\d{2}/\d{2}/\d{4}")

_EXCEL_COLUMNS = [
    "Empresa",
    "Formação/Capacitação/Reciclagem",
    "TREINAMENTO",
    "DATA INICIO",
    "DATA FIM",
    "LOCAL",
    "ALUNOS",
    "RESP. PREENCHIMENTO - FVM",
]


def _classify(course_name: str) -> str:
    if _RECICLAGEM.search(course_name):
        return "RECICLAGEM"
    if _FORMACAO.search(course_name):
        return "FORMAÇÃO"
    return "CAPACITAÇÃO"


def _parse_dates(periodo: str) -> tuple[str, str]:
    """Extrai primeira e última data dd/mm/yyyy de um texto de período."""
    dates = _DATE_RE.findall(str(periodo))
    if not dates:
        return "", ""
    return dates[0], dates[-1]


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.dropna(how="all", inplace=True)

    # Colunas esperadas do sistema: ID, Nome, Carga Horária, Número, Período, Instrutor, Local, Empresa, Participantes
    df.columns = [c.strip() for c in df.columns]

    dates = df["Período"].apply(_parse_dates)
    df["DATA INICIO"] = [d[0] for d in dates]
    df["DATA FIM"]    = [d[1] for d in dates]

    df["Formação/Capacitação/Reciclagem"] = df["Nome"].apply(_classify)
    df["RESP. PREENCHIMENTO - FVM"] = "Fabio"

    df = df.rename(columns={
        "Nome":          "TREINAMENTO",
        "Local":         "LOCAL",
        "Participantes": "ALUNOS",
    })

    out = df[_EXCEL_COLUMNS].copy()
    logger.info("Transformação concluída: %d linhas", len(out))
    return out

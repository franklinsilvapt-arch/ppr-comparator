"""
Scraper genérico de sites das gestoras para extrair campos que a CMVM
não expõe (subscrição mínima, ISIN, TEC real, etc).

Arquitectura: cada gestora tem um EXTRACTOR que recebe o HTML e devolve
um dict {min_subs, isin, tec, manager_url, ...}. Um dispatcher escolhe
o extractor com base no domínio.

Configuração: MANUAL_OVERRIDES em universe.py deve ter `site_url` no
fundo respectivo. O run() aqui itera overrides com site_url e aplica.

Adicionar nova gestora:
  1. Cria extract_<gestora>(html) -> dict
  2. Regista em EXTRACTORS por domínio
"""
from __future__ import annotations

import re
import time
import unicodedata
from urllib.parse import urlparse

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

import requests


def _get(url: str, use_cffi: bool = False) -> str | None:
    try:
        if use_cffi:
            if cffi_requests is None:
                return None
            r = cffi_requests.get(url, impersonate="chrome120", timeout=20)
        else:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        if r.status_code != 200:
            return None
        # Força UTF-8 + normalização NFC — alguns sites (IMGA) usam
        # diacríticos combinados (ex: c+cedilla em vez de ç) o que quebra
        # regex com classes [çc].
        text = r.content.decode("utf-8", errors="replace")
        return unicodedata.normalize("NFC", text)
    except Exception:
        return None


# --------------------- IMGA (hospeda ABANCA + IMGA) ---------------------

def extract_imga(html: str) -> dict:
    out: dict = {}
    # Subscrição inicial: "€100 ou € 25 em Plano de Investimento"
    m = re.search(
        r"Subscri[çc][ãa]o\s*Inicial:?\s*</span>\s*(?:&nbsp;)?\s*<span[^>]*>\s*€\s*(\d+(?:[.,]\d+)?)",
        html,
    )
    if m:
        out["min_subs"] = float(m.group(1).replace(",", "."))

    # ISIN (PT + 10 chars)
    m = re.search(r"\b(PT[A-Z0-9]{10})\b", html)
    if m:
        out["isin"] = m.group(1)

    # TEC (Total Encargos Correntes) — geralmente algures num bloco
    m = re.search(
        r"(?i)(?:TEC|total\s+de\s+encargos\s+correntes)[^%]{0,80}?(\d+[.,]\d{1,2})\s*%",
        html,
    )
    if m:
        out["tec"] = float(m.group(1).replace(",", "."))

    return out


# --------------------- BIZ Capital ---------------------

def extract_biz(html: str) -> dict:
    out: dict = {}
    m = re.search(r"\b(PT[A-Z0-9]{10})\b", html)
    if m:
        out["isin"] = m.group(1)
    # Subscrição mínima tipicamente em texto livre; regex best-effort.
    m = re.search(
        r"(?i)subscri[çc][ãa]o\s+m[ií]nima[^.\d]{0,40}(\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?:€|EUR)",
        html,
    )
    if m:
        out["min_subs"] = float(m.group(1).replace(".", "").replace(",", "."))
    return out


# --------------------- Bankinter ---------------------

def extract_bankinter(html: str) -> dict:
    out: dict = {}
    m = re.search(r"\b(PT[A-Z0-9]{10})\b", html)
    if m:
        out["isin"] = m.group(1)
    m = re.search(
        r"(?i)subscri[çc][ãa]o\s+m[ií]nima[^.\d]{0,40}(\d+(?:[.,]\d+)?)\s*€",
        html,
    )
    if m:
        out["min_subs"] = float(m.group(1).replace(",", "."))
    m = re.search(r"(?i)TEC[^%]{0,60}?(\d+[.,]\d{1,2})\s*%", html)
    if m:
        out["tec"] = float(m.group(1).replace(",", "."))
    return out


# --------------------- Dispatch ---------------------

EXTRACTORS = {
    "imga.pt":        (extract_imga, False),
    "bizcapital.eu":  (extract_biz, False),
    "bankinter.pt":   (extract_bankinter, True),   # precisa curl_cffi
}


def extract_from_url(url: str) -> dict:
    host = urlparse(url).netloc.lower().lstrip("www.")
    for domain, (fn, cffi) in EXTRACTORS.items():
        if domain in host:
            html = _get(url, use_cffi=cffi)
            if not html:
                return {"_error": "fetch failed"}
            try:
                return fn(html)
            except Exception as e:
                return {"_error": str(e)}
    return {"_error": f"no extractor for {host}"}


def run(funds: list[dict]) -> None:
    """Aplica in-place: para fundos com site_url, extrai e preenche
    campos que estiverem vazios (não sobrescreve valores existentes)."""
    scraped = 0
    for f in funds:
        url = f.get("site_url")
        if not url:
            continue
        print(f"[sites] {f['id']} <- {url}")
        data = extract_from_url(url)
        if data.get("_error"):
            print(f"  ERROR: {data['_error']}")
            continue
        for k, v in data.items():
            if k.startswith("_") or v in (None, ""):
                continue
            if f.get(k) in (None, ""):
                f[k] = v
        if data:
            scraped += 1
            print(f"  {data}")
        time.sleep(0.8)
    if scraped:
        print(f"[sites] extraídos: {scraped}")


if __name__ == "__main__":
    from universe import get_funds
    run(get_funds())

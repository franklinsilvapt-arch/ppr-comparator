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

import html
import re
import time
import unicodedata
from urllib.parse import urlparse

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

import requests


def _num(s: str) -> float | None:
    """Converte '1.000' / '1,000.50' / '25' em float, tentando formato pt-PT."""
    s = s.strip()
    if not s:
        return None
    # Formato pt-PT: 1.000,50 → 1000.50
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") >= 1 and len(s.split(".")[-1]) == 3:
        # "1.000" como pt-PT milhares
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


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
        text = unicodedata.normalize("NFC", text)
        # Decode HTML entities (&ccedil; → ç, &#xE7; → ç, &euro; → €, etc)
        # para que as regex possam usar caracteres Unicode directos.
        return html.unescape(text)
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


# --------------------- BlueCrow ---------------------

def extract_bluecrow(html_text: str) -> dict:
    out: dict = {}
    m = re.search(r"\b(PT[A-Z0-9]{10})\b", html_text)
    if m:
        out["isin"] = m.group(1)
    # "Subscrição mínima </strong>€1.000" (após unescape)
    m = re.search(
        r"(?i)subscri[çc]ão\s*m[ií]nima[^<]*</strong>[^<\d]*([\d.,]+)",
        html_text,
    )
    if m:
        out["min_subs"] = _num(m.group(1))
    return out


# --------------------- GNB ---------------------

def extract_gnb(html_text: str) -> dict:
    out: dict = {}
    m = re.search(r"\b(PT[A-Z0-9]{10})\b", html_text)
    if m:
        out["isin"] = m.group(1)
    # "Subscrição Inicial (Mín.) </td> <td> <span ...>25 €"
    m = re.search(
        r"(?i)Subscri[çc]ão\s*Inicial\s*\(M[ií]n\.?\)"
        r"[^<]*</td>\s*<td>[^<]*<span[^>]*>\s*([\d.,]+)\s*€",
        html_text,
    )
    if m:
        out["min_subs"] = _num(m.group(1))
    return out


# --------------------- Optimize ---------------------

def extract_optimize(html: str) -> dict:
    out: dict = {}
    m = re.search(r"\b(PT[A-Z0-9]{10})\b", html)
    if m:
        out["isin"] = m.group(1)
    # "Valor mínimo de investimento:</p> ... <div ...>1 UP</div>"
    m = re.search(
        r"(?i)Valor\s+m[ií]nimo\s+de\s+investimento[^<]*</p>"
        r".{0,600}?elementor-widget-container\">\s*(.*?)\s*</div>",
        html, re.DOTALL,
    )
    if m:
        val = re.sub(r"\s+", " ", m.group(1)).strip()
        # "1 UP" ou "25 €" etc. Tentamos extrair €; caso contrário guardamos
        # a string crua em min_subs_text.
        mn = re.search(r"(\d+(?:[.,]\d+)?)\s*€", val)
        if mn:
            out["min_subs"] = float(mn.group(1).replace(",", "."))
        else:
            out["min_subs_text"] = val[:40]
    return out


# --------------------- Sixty Degrees ---------------------

def extract_sixty(html: str) -> dict:
    out: dict = {}
    m = re.search(r"\b(PT[A-Z0-9]{10})\b", html)
    if m:
        out["isin"] = m.group(1)
    return out


# --------------------- CGD / Caixa ---------------------

def extract_cgd(html: str) -> dict:
    out: dict = {}
    m = re.search(r"\b(PT[A-Z0-9]{10})\b", html)
    if m:
        out["isin"] = m.group(1)
    return out


# --------------------- Banco BPI ---------------------

def extract_bpi(html: str) -> dict:
    out: dict = {}
    m = re.search(r"\b(PT[A-Z0-9]{10})\b", html)
    if m:
        out["isin"] = m.group(1)
    return out


# --------------------- Banco Invest (Smart Invest) ---------------------

def extract_banco_invest(html: str) -> dict:
    out: dict = {}
    m = re.search(r"\b(PT[A-Z0-9]{10})\b", html)
    if m:
        out["isin"] = m.group(1)
    return out


# --------------------- Dispatch ---------------------

EXTRACTORS = {
    "imga.pt":               (extract_imga, False),
    "bizcapital.eu":         (extract_biz, False),
    "bankinter.pt":          (extract_bankinter, True),   # precisa curl_cffi
    "bluecrowcapital.com":   (extract_bluecrow, False),
    "gnbga.pt":              (extract_gnb, False),
    "optimize.pt":           (extract_optimize, False),
    "sixty-degrees.com":     (extract_sixty, False),
    "cgd.pt":                (extract_cgd, False),
    "bancobpi.pt":           (extract_bpi, False),
    "bancoinvest.pt":        (extract_banco_invest, False),
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

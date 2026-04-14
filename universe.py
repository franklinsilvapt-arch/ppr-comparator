"""
Universo de PPR fundos de investimento.

Para cada fundo: ISIN, ticker Morningstar/Yahoo (se existir),
fonte preferida, e metadata base.

NOTA: esta lista deve ser gerada automaticamente via scrape da CMVM PPRList.
Por agora é hardcoded como starter. Depois, `scrapers/cmvm.py` deve atualiza-la.

Fontes disponiveis:
- "yahoo"   : ticker 0P...F no Yahoo Finance (preferida)
- "investing": URL do Investing.com (fallback, usa curl_cffi)
- "golden_sgf": Excel histórico da Golden SGF
- "manual"   : override CSV local
"""

FUNDS = [
    {
        "id": "sgf-dr-financas",
        "name": "SGF Doutor Finanças PPR",
        "manager": "SGF",
        "isin": "PTYGFFIM0008",          # CONFIRMAR - placeholder
        "yahoo_ticker": None,             # buscar via search do Yahoo
        "source": "golden_sgf",           # SGF gere este fundo
        "investing_url": None,
        "tec": 1.85,
        "min_subs": 250,
        "risk_class": 5,
    },
    {
        "id": "invest-ar",
        "name": "Invest Alves Ribeiro PPR",
        "manager": "Invest Gestão de Ativos",
        "isin": "PTYINVIM0007",
        "yahoo_ticker": "0P000011IR.F",  # CONFIRMADO
        "source": "yahoo",
        "investing_url": None,
        "tec": 1.25,
        "min_subs": 100,
        "risk_class": 4,
    },
    {
        "id": "golden-sgf-ret-acc",
        "name": "Golden SGF PPR Retorno Acionista",
        "manager": "Golden SGF",
        "isin": None,                     # buscar no site SGF
        "yahoo_ticker": None,
        "source": "golden_sgf",
        "investing_url": None,
        "tec": 1.95,
        "min_subs": 250,
        "risk_class": 5,
    },
    {
        "id": "casa-inv-sg",
        "name": "Casa de Investimentos Save & Grow PPR",
        "manager": "Casa de Investimentos",
        "isin": "PTCUUBHM0004",           # confirmado via URL investing.com
        "yahoo_ticker": None,
        "source": "investing",
        "investing_url": "https://www.investing.com/funds/ptcuubhm0004",
        "tec": 1.70,
        "min_subs": 500,
        "risk_class": 5,
    },
    # TODO: adicionar restantes. Lista completa deve vir de scrapers/cmvm.py
]

def get_funds():
    return FUNDS

def get_fund(fund_id):
    for f in FUNDS:
        if f["id"] == fund_id:
            return f
    return None

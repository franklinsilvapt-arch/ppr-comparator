# PPR Comparator - Data Pipeline

Pipeline de recolha, cálculo e publicação de dados para o comparador de PPR em literaciafinanceira.pt.

## Arquitetura

```
CMVM PPRList  →  funds.json (universo + metadata)
     ↓
Para cada fundo:
  Yahoo Finance (0P...F)  →  cotações diárias
  ou Investing.com        →  fallback
  ou Golden SGF Excel     →  fallback para fundos SGF
  ou site da gestora      →  fallback manual
     ↓
calc_metrics.py  →  retornos (YTD, 1a, 3a, 5a, anualizado)
                 →  risco (vol, Sharpe, max DD, VaR, beta)
     ↓
data/latest.json  →  servido via GitHub Pages / Vercel
     ↓
Embed Webflow faz fetch do JSON
```

## Setup local

```bash
# 1. Clonar e entrar
git clone <teu-repo>
cd ppr-comparator

# 2. Virtualenv
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Primeira corrida (pode demorar 1-2 min)
python main.py

# 5. Ver output
cat data/latest.json | head -50
```

## Correr por partes (debug)

```bash
python -m scrapers.cmvm           # atualiza universo de PPR
python -m scrapers.yahoo          # puxa cotacoes Yahoo
python -m scrapers.golden_sgf     # puxa Excel Golden SGF
python -m scrapers.investing      # fallback Investing.com
python calc_metrics.py            # recalcula metricas
```

## Deploy

### Opção A: GitHub Pages (mais simples, grátis)

1. Push para GitHub
2. Settings → Pages → Source: `main` branch, pasta `/data`
3. JSON fica em `https://{user}.github.io/{repo}/latest.json`
4. GitHub Actions (já incluído em `.github/workflows/update.yml`) corre semanalmente

### Opção B: Vercel (mais rápido, CDN global)

1. `vercel deploy --prod`
2. JSON fica em `https://teu-projeto.vercel.app/data/latest.json`

## Integrar no Webflow

O ficheiro `embed/comparador-ppr.html` é o mesmo embed que já tens, mas agora com `fetch()` para puxar o JSON em vez de usar dados mock. Basta atualizar o URL na constante `DATA_URL` no topo do script e colar no Embed do Webflow.

## Frequência de atualização

Semanal, todas as segundas 08:00 UTC. Suficiente para PPR (long-term). Ver `.github/workflows/update.yml`.

## Troubleshooting

- **Yahoo bloqueia**: adicionar `time.sleep(1)` entre requests no `scrapers/yahoo.py`.
- **Fundo novo sem ticker Morningstar**: adicionar manualmente em `scrapers/manual_overrides.py`.
- **Cloudflare bloqueia Investing.com**: instalar `curl_cffi` (ver requirements).

"""Split embed-comparador-ppr.html into external CSS + JS + tiny Webflow embed.
Output: comparador-ppr.css, comparador-ppr.js, webflow-embed.html at repo root.
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
src = (ROOT / "embed-comparador-ppr.html").read_text(encoding="utf-8")

# 1. CSS - remover rules em html/body que afectariam a página Webflow
style_m = re.search(r"<style>\s*(.*?)\s*</style>", src, re.DOTALL)
css = style_m.group(1)

# Substitui bloco 'html, body, #lf-pc-calc {...}' por só '#lf-pc-calc {...}'
# (scoped) e remove ::-webkit-scrollbar rules em html/body. O componente
# corre na página Webflow: não pode tocar no chrome global.
css = re.sub(
    r"html, body, #lf-pc-calc \{[^}]*\}",
    "#lf-pc-calc { margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }",
    css,
    flags=re.DOTALL,
)
# Remove scrollbar rules em html/body (deixa só a do #lf-pc-calc)
css = re.sub(
    r"html::-webkit-scrollbar,\s*body::-webkit-scrollbar,\s*",
    "",
    css,
)
# Remove @import do Inter (fonte já carregada pelo Webflow)
css = re.sub(
    r"@import url\('https://fonts\.googleapis\.com/css2\?family=Inter[^']*'\);\s*",
    "",
    css,
)

(ROOT / "comparador-ppr.css").write_text(css + "\n", encoding="utf-8")

# 2. Markup interno (.lpc-container ... </div>)
co = src.find('<div class="lpc-container">')
pos = co + len('<div class="lpc-container">')
depth = 1
while depth > 0 and pos < len(src):
    no = src.find('<div', pos)
    nc = src.find('</div>', pos)
    if nc == -1:
        break
    if no != -1 and no < nc:
        depth += 1
        pos = no + 4
    else:
        depth -= 1
        pos = nc + len('</div>')
markup_inner = src[co:pos]

# 3. IIFE script (o último <script> sem src)
scripts = list(re.finditer(
    r"<script(?:[^>]*)?>\s*((\(function[\s\S]*?\)\(\)\s*;?))\s*</script>",
    src, re.DOTALL))
assert scripts, "IIFE not found"
iife_src = scripts[-1].group(1)

# 4. Preamble que injecta markup se o host estiver vazio (modo Webflow embed).
#    Em modo iframe standalone (onde o markup já existe no HTML), skip.
escaped = (
    markup_inner
    .replace("\\", "\\\\")
    .replace("`", "\\`")
    .replace("${", "\\${")
)
preamble = (
    "(function () {\n"
    "  // Auto-mount: se o elemento host estiver vazio, injecta o markup.\n"
    "  // Usado quando o ficheiro é carregado via <script src> no Webflow.\n"
    "  // Em modo iframe standalone (markup inline), o host já tem .lpc-\n"
    "  // container e salta-se este passo.\n"
    "  var host = document.getElementById('lf-pc-calc');\n"
    "  if (host && !host.querySelector('.lpc-container')) {\n"
    "    host.innerHTML = `" + escaped + "`;\n"
    "  }\n"
    "})();\n"
)

(ROOT / "comparador-ppr.js").write_text(preamble + "\n" + iife_src + "\n", encoding="utf-8")

# 5. Webflow embed minimal
webflow = (
    '<link rel="stylesheet" href="https://franklinsilvapt-arch.github.io/ppr-comparator/comparador-ppr.css">\n'
    '<div id="lf-pc-calc"></div>\n'
    '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js" defer></script>\n'
    '<script src="https://franklinsilvapt-arch.github.io/ppr-comparator/comparador-ppr.js" defer></script>\n'
)
(ROOT / "webflow-embed.html").write_text(webflow, encoding="utf-8")

for p in ["comparador-ppr.css", "comparador-ppr.js", "webflow-embed.html"]:
    sz = (ROOT / p).stat().st_size
    print(f"{p}: {sz} bytes")

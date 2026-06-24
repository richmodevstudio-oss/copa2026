"""Gera src/copa2026/third_place_data.py a partir da tabela oficial da Wikipédia.

A tabela dos 8 melhores terceiros (495 combinações) está no template
`Template:2026 FIFA World Cup third-place table`. Cada linha lista, em negrito,
os 8 grupos cujos terceiros avançam e, em 8 colunas (1A,1B,1D,1E,1G,1I,1K,1L),
qual terceiro (3X) enfrenta cada um desses primeiros colocados.

Rodar:  python scripts/generate_third_place_data.py
"""

from __future__ import annotations

import re
from pathlib import Path

import requests

WINNERS = ["A", "B", "D", "E", "G", "I", "K", "L"]
URL = (
    "https://en.wikipedia.org/w/index.php"
    "?title=Template:2026_FIFA_World_Cup_third-place_table&action=raw"
)
OUT = Path(__file__).resolve().parents[1] / "src" / "copa2026" / "third_place_data.py"


def parse(wikitext: str) -> dict[str, dict[str, str]]:
    blocks = re.split(r'!\s*scope="row"', wikitext)[1:]
    alloc: dict[str, dict[str, str]] = {}
    for block in blocks:
        groups = re.findall(r"'''([A-L])'''", block)
        thirds = re.findall(r"\b3([A-L])\b", block)
        if len(groups) != 8 or len(thirds) != 8:
            continue
        key = "".join(sorted(groups))
        if set(thirds) != set(groups):
            raise ValueError(f"linha inconsistente: {key} -> {thirds}")
        alloc[key] = dict(zip(WINNERS, thirds))
    if len(alloc) != 495:
        raise ValueError(f"esperado 495 combinações, obtido {len(alloc)}")
    return alloc


def main() -> None:
    text = requests.get(URL, timeout=30, headers={"User-Agent": "copa2026/1.0"}).text
    alloc = parse(text)
    lines = [
        '"""Tabela oficial dos 8 melhores terceiros (PRD §4.4).',
        "",
        "GERADO por scripts/generate_third_place_data.py — não editar à mão.",
        "Chave: 8 letras de grupo ordenadas. Valor: {grupo do 1º: grupo do 3º}.",
        '"""',
        "",
        "BEST_THIRD_ALLOCATION: dict[str, dict[str, str]] = {",
    ]
    for key in sorted(alloc):
        lines.append(f"    {key!r}: {alloc[key]!r},")
    lines.append("}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(alloc)} combinações escritas em {OUT}")


if __name__ == "__main__":
    main()

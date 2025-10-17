#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Uso:
  1) Salve este arquivo como arxiv_to_rayyan.py
  2) Instale dependências:  pip install arxiv pandas
  3) Rode:  python arxiv_to_rayyan.py --out rayyan.csv
  4) Cole sua query (no formato abaixo) e finalize com Ctrl+D (Linux/macOS) ou Ctrl+Z+Enter (Windows).

Exemplo de entrada (cole exatamente assim):
(
  ("All Metadata":"explainable artificial intelligence" OR
   "All Metadata":"XAI" OR
   "All Metadata":"interpretable AI" OR
   "All Metadata":"model explainability" OR
   "All Metadata":"model transparency")
)
AND
(
  ("All Metadata":"facial recognition" OR
   "All Metadata":"facial expression recognition" OR
   "All Metadata":"facial analysis" OR
   "All Metadata":"face emotion recognition" OR
   "All Metadata":"affective computing")
)
AND
(
  "All Metadata":"explainability" OR
  "All Metadata":"interpretability" OR
  "All Metadata":"trustworthy AI"
)
"""

import argparse
import re
import sys
import time
from typing import List

import pandas as pd

try:
    import arxiv
except ImportError as e:
    print("A biblioteca 'arxiv' não está instalada. Rode: pip install arxiv", file=sys.stderr)
    raise


def normalize_command_search_to_arxiv(cmd: str) -> str:
    """
    Converte a sintaxe do 'Command Search' (com "All Metadata":"...") para a sintaxe do arXiv:
      - "All Metadata":"frase"  ->  all:"frase"
      - Mantém AND / OR / ANDNOT e parênteses
      - Remove quebras de linha e espaços extras
    """
    s = cmd.strip()

    # Normalizar aspas curvas para simples/duplas comuns
    s = s.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")

    # Remover quebras de linha supérfluas
    s = re.sub(r'\s+', ' ', s)

    # Padronizar operadores para maiúsculo
    # Primeiro, proteger palavras dentro de aspas para não mexer nelas
    # Simplesmente faremos replace case-insensitive fora de aspas com regex de lookarounds simples
    def upper_ops(match: re.Match) -> str:
        return match.group(0).upper()

    # Transformar and/or/andnot (fora de aspas) em maiúsculo
    # Estratégia simples: substituir em toda string (não dentro de aspas) é complexo; como é uma query técnica,
    # vamos confiar que AND/OR aparecem fora de aspas. Ainda assim, também aceitamos minúsculas.
    for op in [" and ", " And ", " AND ", " or ", " Or ", " OR ", " andnot ", " Andnot ", " ANDNOT "]:
        s = s.replace(op, f" {op.strip().upper()} ")

    # Converter "All Metadata":"..."  -> all:"..."
    # Aceita aspas simples ou duplas: "All Metadata": "..."  ou  'All Metadata':'...'
    s = re.sub(r'(["\'])All Metadata\1\s*:\s*(["\'])(.+?)\2', r'all:"\3"', s, flags=re.IGNORECASE)

    # Também aceitar sem aspas na chave (raro): All Metadata:"..."
    s = re.sub(r'All Metadata\s*:\s*(["\'])(.+?)\1', r'all:"\2"', s, flags=re.IGNORECASE)

    # Remover espaços redundantes perto de parênteses
    s = re.sub(r'\(\s+', '(', s)
    s = re.sub(r'\s+\)', ')', s)

    # Remover espaços duplicados
    s = re.sub(r'\s{2,}', ' ', s).strip()

    return s


def chunked(iterable, size):
    """Divide iterável em blocos de tamanho fixo."""
    for i in range(0, len(iterable), size):
        yield iterable[i:i+size]


def search_arxiv_to_dataframe(query: str, max_results: int = 5000, page_size: int = 100, delay_seconds: float = 3.0) -> pd.DataFrame:
    """
    Faz a busca no arXiv usando a lib 'arxiv' com paginação e respeitando rate limit (~1 request a cada 3s).
    Retorna DataFrame com colunas adequadas ao Rayyan.
    """
    client = arxiv.Client(page_size=page_size, delay_seconds=delay_seconds, num_retries=3)

    search = arxiv.Search(
        query=query,
        max_results=max_results,             # total máximo
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )

    records: List[dict] = []
    count = 0

    for result in client.results(search):
        count += 1
        # Autores como "Sobrenome, Nome" separados por "; "
        authors = "; ".join([f"{a.name}" for a in result.authors]) if result.authors else ""

        # Campos
        title = (result.title or "").replace('\n', ' ').strip()
        abstract = (result.summary or "").replace('\n', ' ').strip()
        year = ""
        if result.published:
            try:
                year = str(result.published.year)
            except Exception:
                year = ""

        doi = result.doi or ""
        journal_ref = result.journal_ref or ""
        url = result.entry_id or ""   # link da publicação no arXiv
        arxiv_id = result.get_short_id() if hasattr(result, "get_short_id") else (result.entry_id.split('/')[-1] if result.entry_id else "")
        primary_cat = getattr(result, "primary_category", "") or ""
        categories = ""
        if getattr(result, "categories", None):
            categories = "; ".join(result.categories)

        # Montar registro com campos úteis ao Rayyan
        records.append({
            "Title": title,
            "Abstract": abstract,
            "Authors": authors,
            "Year": year,
            "DOI": doi,
            "Journal/Conference": journal_ref,
            "URL": url,
            "arXiv ID": arxiv_id,
            "Primary Category": primary_cat,
            "Categories": categories
        })

    df = pd.DataFrame.from_records(records, columns=[
        "Title", "Abstract", "Authors", "Year", "DOI", "Journal/Conference",
        "URL", "arXiv ID", "Primary Category", "Categories"
    ])
    return df


def main():
    parser = argparse.ArgumentParser(description="Converte query estilo 'Command Search' para arXiv, busca e exporta CSV para Rayyan.")
    parser.add_argument("--out", default="rayyan.csv", help="Caminho do arquivo CSV de saída (default: rayyan.csv)")
    parser.add_argument("--max", type=int, default=5000, help="Máximo de resultados a coletar (default: 5000)")
    parser.add_argument("--page-size", type=int, default=100, help="Tamanho da página por requisição à API (default: 100)")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay entre requisições (segundos) para respeitar rate limit do arXiv (default: 3.0)")
    args = parser.parse_args()

    print("Cole sua query no formato de 'Command Search' (finalize com Ctrl+D em Linux/macOS ou Ctrl+Z+Enter no Windows):\n", file=sys.stderr)
    raw_query = sys.stdin.read()

    if not raw_query.strip():
        print("Nenhuma query recebida via stdin.", file=sys.stderr)
        sys.exit(1)

    arxiv_query = normalize_command_search_to_arxiv(raw_query)
    print(f"\nQuery convertida para arXiv:\n{arxiv_query}\n", file=sys.stderr)

    df = search_arxiv_to_dataframe(
        arxiv_query,
        max_results=args.max,
        page_size=args.page_size,
        delay_seconds=args.delay
    )

    # CSV com BOM para abrir bem no Excel/LibreOffice; separador padrão ','
    df.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"CSV salvo em: {args.out}", file=sys.stderr)

    # Dica de tamanho
    print(f"Total de registros: {len(df)}", file=sys.stderr)


if __name__ == "__main__":
    main()

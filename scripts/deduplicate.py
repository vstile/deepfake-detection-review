#!/usr/bin/env python3
"""
deduplicate.py

Unisce più export (Scopus, IEEE Xplore, ScienceDirect) e rimuove i duplicati.
Chiave primaria: DOI normalizzato; fallback: titolo normalizzato.
Precedenza di ritenzione: Scopus > IEEE Xplore > ScienceDirect (configurabile).

Uso (esempio Set B):
  python deduplicate.py \
    --input Scopus:/raw/query-B_Scopus_71.csv \
    --input "IEEE Xplore:/raw/query-B_IEEEXplore_161.csv" \
    --input ScienceDirect:/processed/query-B_ScienceDirect_30_parsed.csv \
    --out /processed/query-B_merged_deduplicated.csv

Opzioni:
  --precedence "Scopus,IEEE Xplore,ScienceDirect"
  --print-stats           stampa riepilogo e intersezioni

Dipendenze: pandas (pip install pandas)
"""
import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


def norm_doi(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip().lower()
    s = s.replace("https://doi.org/", "").replace("http://doi.org/", "")
    s = s.strip().strip(".")
    m = re.search(r"(10\.\d{4,9}/\S+)", s)
    return m.group(1).rstrip(".,;)") if m else ""


def norm_title(s: str) -> str:
    if not isinstance(s, str):
        return ""
    # normalizzazione sobria per matching robusto
    s = s.strip().lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


COMMON_TITLE_COLS = [
    "Document Title", "Title", "Article Title", "Item Title", "publicationTitle", "title"
]
COMMON_DOI_COLS = ["DOI", "doi", "DOI Link", "DOI URL", "Article DOI", "Link"]
COMMON_YEAR_COLS = ["Publication Year", "Year", "Issue Year", "Publication year"]
COMMON_AUTH_COLS = [
    "Authors", "Authors Full Names", "Author(s)", "Authors Name",
    "AuthorsNames", "Authors with affiliations", "Authors/Affiliations"
]
COMMON_URL_COLS = ["PDF Link", "Link", "URL", "Document Link", "Article URL", "source"]


def read_csv_any(path: Path) -> pd.DataFrame:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception:
            continue
    raise RuntimeError(f"Cannot read {path} with common encodings")


def pick_first_present(df: pd.DataFrame, columns: List[str]) -> pd.Series:
    for c in columns:
        if c in df.columns:
            return df[c]
    # fallback: prima colonna
    return df.iloc[:, 0] if not df.empty else pd.Series([], dtype=object)


def extract_standard(df_raw: pd.DataFrame, label: str) -> pd.DataFrame:
    out = pd.DataFrame({
        "source": label,
        "title": pick_first_present(df_raw, COMMON_TITLE_COLS),
        "authors": pick_first_present(df_raw, COMMON_AUTH_COLS) if set(COMMON_AUTH_COLS) & set(df_raw.columns) else None,
        "year": pick_first_present(df_raw, COMMON_YEAR_COLS) if set(COMMON_YEAR_COLS) & set(df_raw.columns) else None,
        "doi": pick_first_present(df_raw, COMMON_DOI_COLS) if set(COMMON_DOI_COLS) & set(df_raw.columns) else None,
        "url": pick_first_present(df_raw, COMMON_URL_COLS) if set(COMMON_URL_COLS) & set(df_raw.columns) else None,
    })
    return out


def compute_stats(df: pd.DataFrame) -> Dict[str, int]:
    return df["source"].value_counts().to_dict()


def overlaps_by_title_sets(dfa: pd.DataFrame) -> Dict[Tuple[str, str], int]:
    # calcola intersezioni pairwise per debug
    srcs = sorted(dfa["source"].unique())
    out = {}
    for i in range(len(srcs)):
        for j in range(i + 1, len(srcs)):
            si, sj = srcs[i], srcs[j]
            ti = set(dfa.loc[dfa["source"] == si, "title_norm"].dropna().unique())
            tj = set(dfa.loc[dfa["source"] == sj, "title_norm"].dropna().unique())
            out[(si, sj)] = len(ti & tj)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", action="append", required=True,
                    help='Lista "Label:path", es. Scopus:/raw/x.csv  oppure "IEEE Xplore:/raw/y.csv"')
    ap.add_argument("--out", required=True, help="File CSV di output")
    ap.add_argument("--precedence", default="Scopus,IEEE Xplore,ScienceDirect",
                    help="Ordine di preferenza per record duplicati")
    ap.add_argument("--print-stats", action="store_true", help="Stampa riepilogo e intersezioni")
    args = ap.parse_args()

    precedence = [s.strip() for s in args.precedence.split(",") if s.strip()]
    prec_map = {label: i for i, label in enumerate(precedence)}

    inputs: List[Tuple[str, Path]] = []
    for spec in args.input:
        if ":" not in spec:
            print(f"[WARN] input senza etichetta, salto: {spec}")
            continue
        label, path = spec.split(":", 1)
        inputs.append((label.strip(), Path(path.strip())))

    frames = []
    for label, p in inputs:
        raw = read_csv_any(p)
        df = extract_standard(raw, label)
        df["title_norm"] = df["title"].map(norm_title)
        df["doi_norm"] = df["doi"].map(norm_doi)
        df["source_rank"] = df["source"].map(lambda s: prec_map.get(s, 99))
        df["__src_file__"] = p.name
        frames.append(df)

    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["source", "title", "authors", "year", "doi", "url", "title_norm", "doi_norm", "source_rank"]
    )

    initial_total = len(merged)
    per_source_before = compute_stats(merged)

    # Dedup: prima per DOI, poi per titolo
    merged = merged.sort_values(by=["doi_norm", "source_rank"], na_position="last")
    has_doi = merged[merged["doi_norm"].astype(str) != ""]
    no_doi = merged[merged["doi_norm"].astype(str) == ""]

    dedup_doi = has_doi.drop_duplicates(subset=["doi_norm"], keep="first")
    combined = pd.concat([dedup_doi, no_doi], ignore_index=True)
    combined = combined.sort_values(by=["title_norm", "source_rank"], na_position="last")
    dedup_all = combined.drop_duplicates(subset=["title_norm"], keep="first")

    final_total = len(dedup_all)
    removed = initial_total - final_total
    per_source_after = compute_stats(dedup_all)

    # Output minimale pulito
    out_cols = ["source", "title", "authors", "year", "doi", "url"]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    dedup_all[out_cols].to_csv(args.out, index=False)

    print(f"[OK] Input total: {initial_total} | Unique: {final_total} | Removed: {removed}")
    if args.print-stats:
        print("Per-source before:", per_source_before)
        print("Per-source after: ", per_source_after)
        print("Pairwise title overlaps:", overlaps_by_title_sets(pd.concat(frames, ignore_index=True)))
    else:
        # stampa sintetica
        print("Per-source before:", per_source_before)
        print("Per-source after:", per_source_after)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)

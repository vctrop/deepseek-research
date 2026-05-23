#!/usr/bin/env python3
"""verify_evidence_grades.py — GATE-7: Evidence Grade Sanity Check.

Cruza Access method e Coverage do header de cada deep read com as grades
dos claims extraídos. Viola se:
  - Access method é "snippet" ou "abstract" e claims são V ou P
  - Coverage < 25% e claims são V
  - Coverage não reportada

Uso:
    code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from verify_evidence_grades import check
print(check("{session_dir}/deep-reads/"))
    ''')
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def _parse_deep_read(filepath: Path) -> dict | None:
    """Parse um arquivo deep-reads/*.md e extrai metadata + claims.

    Returns:
        {"source_id": str, "access_method": str, "coverage_pct": float|None,
         "claims": [{"id": "C1", "grade": "V", "text": "..."}, ...]}
    """
    try:
        text = filepath.read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return None

    source_id = filepath.stem

    # Extrair Access method
    access_method = ""
    am_match = re.search(r'\*\*Access method:\*\*\s*(.+)', text)
    if am_match:
        access_method = am_match.group(1).strip().lower()

    # Extrair Coverage
    coverage_pct = None
    cov_match = re.search(r'\*\*Coverage:\*\*\s*([\d.]+)%', text)
    if cov_match:
        try:
            coverage_pct = float(cov_match.group(1))
        except ValueError:
            pass

    # Extrair claims e grades da tabela
    claims = []
    for claim_match in re.finditer(
        r'\|\s*(C\d+)\s*\|\s*"([^"]*)"\s*\|\s*(V|P|I|M|E)\s*\|',
        text
    ):
        claims.append({
            "id": claim_match.group(1).strip(),
            "text": claim_match.group(2).strip()[:80],
            "grade": claim_match.group(3).strip(),
        })

    # Fallback: se não encontrou claims no formato padrão, tentar formato alternativo
    if not claims:
        for claim_match in re.finditer(
            r'\|\s*(C\d+)\s*\|\s*([^|]+)\s*\|\s*(V|P|I|M|E)\s*\|',
            text
        ):
            claims.append({
                "id": claim_match.group(1).strip(),
                "text": claim_match.group(2).strip()[:80],
                "grade": claim_match.group(3).strip(),
            })

    return {
        "source_id": source_id,
        "access_method": access_method,
        "coverage_pct": coverage_pct,
        "claims": claims,
    }


def _is_snippet_or_abstract(access_method: str) -> bool:
    """Verifica se o access method indica fonte intermediária."""
    snippet_keywords = ["snippet", "abstract", "summary", "intermediar"]
    return any(kw in access_method for kw in snippet_keywords)


def check(deep_reads_dir: str) -> str:
    """Executa GATE-7 e retorna JSON com resultado."""
    dir_path = Path(deep_reads_dir)
    if not dir_path.exists():
        return json.dumps({
            "pass": True,
            "gate": "GATE-7",
            "description": "Evidence Grade Sanity Check",
            "note": "deep-reads directory not found — nothing to check",
            "violations": [],
        }, indent=2)

    md_files = sorted([
        f for f in dir_path.glob("*.md")
        if not f.name.startswith("_")
    ])

    violations = []
    warnings = []
    files_checked = 0

    for fpath in md_files:
        data = _parse_deep_read(fpath)
        if not data:
            continue
        files_checked += 1

        # Regra 1: Snippet/abstract com V ou P
        if _is_snippet_or_abstract(data["access_method"]):
            for claim in data["claims"]:
                if claim["grade"] in ("V", "P"):
                    violations.append(
                        f"{data['source_id']}/{claim['id']}: {claim['grade']}-grade "
                        f"claim from '{data['access_method']}' source. "
                        f"Should be I-grade. Claim: \"{claim['text']}\""
                    )

        # Regra 2: Coverage < 25% com V-grade
        if data["coverage_pct"] is not None and data["coverage_pct"] < 25:
            for claim in data["claims"]:
                if claim["grade"] == "V":
                    violations.append(
                        f"{data['source_id']}/{claim['id']}: V-grade claim "
                        f"with only {data['coverage_pct']:.0f}% coverage. "
                        f"Claim: \"{claim['text']}\""
                    )

        # Regra 3: Coverage não reportada
        if data["coverage_pct"] is None and data["claims"]:
            warnings.append(
                f"{data['source_id']}: Coverage not reported — "
                f"{len(data['claims'])} claims extracted. Assuming LOW cap."
            )

    result = {
        "pass": len(violations) == 0,
        "gate": "GATE-7",
        "description": "Evidence Grade Sanity Check",
        "files_checked": files_checked,
        "violations": violations,
        "warnings": warnings,
    }

    return json.dumps(result, indent=2)


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 2:
        print(check(sys.argv[1]))
    else:
        print("Usage: python verify_evidence_grades.py <deep_reads_dir>")

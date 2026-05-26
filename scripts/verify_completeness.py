#!/usr/bin/env python3
"""verify_completeness.py — GATE-6: Verification Completeness Check.

Verifica que toda fonte com URL no 02-source-inventory.md tem uma entrada
correspondente na tabela de verificação do 03-source-verification.md com
Status preenchido (ACCESSIBLE, UNVERIFIABLE, HALLUCINATED, ou EXCLUDED).

Uso:
    code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from verify_completeness import check
print(check("{session_dir}/02-source-inventory.md", "{session_dir}/03-source-verification.md"))
    ''')
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def _extract_sources(inventory_path: str) -> list[dict]:
    """Extrai fontes do 02-source-inventory.md.

    Suporta formatos antigo (5 colunas) e novo (6 colunas com DOI).
    Formato novo: | S{n} | Location | Type | DOI | Relevance | Why |
    Formato antigo: | S{n} | Location | Type | Relevance | Why |
    Retorna lista de {"id": "S1", "title": "...", "has_url": bool}
    """
    sources = []
    try:
        text = Path(inventory_path).read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return sources

    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("| S") or stripped.startswith("| CODE-")):
            continue
        if stripped.startswith("| Source"):
            continue
        parts = [p.strip() for p in stripped.split("|")]
        if len(parts) < 5:
            continue
        sid = parts[1]
        # parts[2] é sempre Location/Title
        title_or_path = parts[2] if len(parts) > 2 else ""
        has_url = bool(re.search(r'https?://', title_or_path))
        sources.append({"id": sid, "title": title_or_path, "has_url": has_url})
    return sources


def _extract_verified_status(verification_path: str) -> dict[str, str]:
    """Extrai Status de cada fonte do 03-source-verification.md.

    Procura linhas da Credibility Matrix: | S{n} | tier | rationale | P/S/T | STATUS |
    Retorna {"S1": "ACCESSIBLE", "S2": "UNVERIFIABLE", ...}
    """
    statuses = {}
    valid_statuses = {"ACCESSIBLE", "UNVERIFIABLE", "HALLUCINATED", "EXCLUDED"}

    try:
        text = Path(verification_path).read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return statuses

    # Padrão para linhas da Credibility Matrix
    for match in re.finditer(
        r'\|\s*(S\d+|CODE-\d+)\s*\|\s*(?:HIGH|MEDIUM|LOW)\s*\|\s*([^|]+)\s*\|\s*[PST]\s*\|\s*(\w+)',
        text
    ):
        sid = match.group(1).strip()
        status = match.group(3).strip().upper()
        if status in valid_statuses:
            statuses[sid] = status
        else:
            statuses[sid] = f"INVALID_STATUS:{status}"

    return statuses


def _extract_summary_numbers(verification_path: str) -> dict[str, int] | None:
    """Extrai os números da Verification Summary table."""
    try:
        text = Path(verification_path).read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return None

    # | N | N | N | N | N |
    match = re.search(
        r'\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|',
        text
    )
    if not match:
        return None

    return {
        "total": int(match.group(1)),
        "accessible": int(match.group(2)),
        "unverifiable": int(match.group(3)),
        "hallucinated": int(match.group(4)),
        "excluded": int(match.group(5)),
    }


def check(inventory_path: str, verification_path: str) -> str:
    """Executa GATE-6 e retorna JSON com resultado.

    Returns:
        JSON string: {"pass": bool, "violations": [...]}
    """
    sources = _extract_sources(inventory_path)
    statuses = _extract_verified_status(verification_path)
    summary = _extract_summary_numbers(verification_path)

    violations = []

    # 1. Cada fonte com URL deve ter status
    for src in sources:
        if not src["has_url"]:
            continue
        if src["id"] not in statuses:
            violations.append(
                f"Source {src['id']} ('{src['title'][:60]}') has URL but no entry "
                f"in Credibility Matrix"
            )
        elif statuses[src["id"]].startswith("INVALID_STATUS"):
            violations.append(
                f"Source {src['id']}: invalid status '{statuses[src['id']]}'"
            )

    # 2. Verificar soma
    if summary:
        total_from_summary = (
            summary["accessible"]
            + summary["unverifiable"]
            + summary["hallucinated"]
            + summary["excluded"]
        )
        if total_from_summary != summary["total"]:
            violations.append(
                f"Verification Summary numbers don't add up: "
                f"{summary['accessible']}+{summary['unverifiable']}+"
                f"{summary['hallucinated']}+{summary['excluded']} = "
                f"{total_from_summary}, but total = {summary['total']}"
            )

        # Verificar se bate com número de fontes
        if summary["total"] != len(sources):
            violations.append(
                f"Verification Summary total ({summary['total']}) != "
                f"sources in inventory ({len(sources)})"
            )
    else:
        violations.append("Verification Summary table not found or unparseable")

    # 3. Nenhuma fonte com status placeholder (título contendo "{")
    for src in sources:
        if "{" in src["title"] and src["has_url"]:
            violations.append(
                f"Source {src['id']}: title contains unresolved placeholder"
            )

    result = {
        "pass": len(violations) == 0,
        "gate": "GATE-6",
        "description": "Verification Completeness Check",
        "sources_total": len(sources),
        "sources_with_url": sum(1 for s in sources if s["has_url"]),
        "sources_with_status": len(statuses),
        "violations": violations,
    }

    return json.dumps(result, indent=2)


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 3:
        print(check(sys.argv[1], sys.argv[2]))
    else:
        print("Usage: python verify_completeness.py <inventory> <verification>")

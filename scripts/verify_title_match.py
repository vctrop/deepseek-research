#!/usr/bin/env python3
"""verify_title_match.py — GATE-0b: Verificação determinística do checkpoint JSON
de title matching (GATE-0).

Lê `02-source-inventory.md` → extrai fontes com URL.
Lê `03-gate0-results.json` → verifica que cada fonte com URL tem entry.
Verifica consistência match_pct ↔ verdict.
Reporta PASS/FAIL com lista de violações.

Usage (via code_execution no SKILL.md Close):
    code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from verify_title_match import check
print(check("{session_dir}"))
    ''')
"""

from __future__ import annotations

import json
import re
from pathlib import Path

STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "to", "for", "and",
    "with", "using", "via", "from", "is", "at", "by", "or",
    "as", "be", "it", "not", "but", "are", "was", "were",
    "been", "has", "have", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "shall",
    "this", "that", "these", "those",
}


def _extract_sources_with_url(inventory_path: Path) -> dict[str, dict]:
    """Extrai fontes que têm URL do source inventory.

    Returns:
        Dict[source_id, {title, url, line}]
    """
    sources: dict[str, dict] = {}

    if not inventory_path.exists():
        return sources

    text = inventory_path.read_text(encoding="utf-8")

    # Procurar a tabela consolidated sources
    # Formato: | S1 | {url} | ... |
    # ou v2: | S1 | {url} | ... | DOI | ... |
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()

        # Detectar início da tabela
        if stripped.startswith("| Source ID") or stripped.startswith("| Source"):
            in_table = True
            continue

        # Header separator
        if in_table and re.match(r'^\|[\s\-:|]+$', stripped):
            continue

        if in_table and stripped.startswith("|"):
            parts = [p.strip() for p in stripped.split("|")]
            # parts[0] vazio (leading pipe), parts[1] = ID, parts[2] = location,
            # parts[3] = type, parts[4..] depend on schema
            if len(parts) < 4:
                continue

            source_id = parts[1]
            location = parts[2]
            source_type = parts[3] if len(parts) > 3 else ""

            # Determine if this is v1 (5 cols) or v2 (6 cols with DOI)
            # Check for schema header comment
            schema_v2 = "<!-- schema: v2" in text

            if schema_v2 and len(parts) >= 6:
                # v2: ID | Location | Type | DOI | Relevance | Why
                # parts: ['', ID, Loc, Type, DOI, Rel, Why, '']
                pass
            elif not schema_v2 and len(parts) >= 6:
                # v1: ID | Location | Type | Relevance | Why
                # parts: ['', ID, Loc, Type, Rel, Why, '']
                pass

            # Só incluir fontes com URL
            if location and (location.startswith("http://") or location.startswith("https://")):
                # Tentar extrair título da linha da tabela — o título está
                # tipicamente na seção "Source Details" abaixo da tabela
                sources[source_id] = {
                    "url": location,
                    "type": source_type,
                    "line": line.strip()[:120],
                }

        # Sair da tabela quando encontrar uma linha não-tabela
        if in_table and stripped and not stripped.startswith("|"):
            # Verificar se ainda estamos na tabela (pode ter linha em branco)
            # Se a próxima linha não for tabela, sair
            in_table = False

    # Segunda passagem: extrair títulos da seção "Source Details"
    detail_pattern = re.compile(
        r'###\s+(S\d+|CODE-\d+)[:\s]+(.+?)(?=\n(?:-|\*\*|###|$))',
        re.MULTILINE | re.DOTALL,
    )
    for match in detail_pattern.finditer(text):
        sid = match.group(1)
        detail_text = match.group(2).strip()
        # Extrair primeira linha significativa como título
        title_line = detail_text.split("\n")[0].strip()
        # Remover asteriscos de markdown
        title_line = re.sub(r'\*+', '', title_line).strip()
        if sid in sources and title_line:
            sources[sid]["reported_title"] = title_line

    return sources


def check(session_dir: str) -> str:
    """Verifica o checkpoint GATE-0 JSON contra o source inventory.

    Args:
        session_dir: Caminho para o diretório da sessão.

    Returns:
        JSON string com {"pass": bool, "gate": "GATE-0b", "violations": [...]}
    """
    session = Path(session_dir)
    inventory_path = session / "02-source-inventory.md"
    checkpoint_path = session / "03-gate0-results.json"

    violations: list[str] = []

    # Verificar se o checkpoint existe
    if not checkpoint_path.exists():
        # Backward-compatible: WARN mas não FAIL
        sources_with_url = _extract_sources_with_url(inventory_path)
        url_count = len(sources_with_url)
        if url_count > 0:
            result = {
                "pass": True,
                "gate": "GATE-0b",
                "description": "Title Match Checkpoint Verification",
                "warnings": [
                    f"Missing checkpoint file: 03-gate0-results.json not found. "
                    f"{url_count} source(s) with URL in inventory could not be verified. "
                    f"GATE-0 was not recorded. Re-run Stage 3 for full verification."
                ],
                "violations": [],
            }
        else:
            result = {
                "pass": True,
                "gate": "GATE-0b",
                "description": "Title Match Checkpoint Verification",
                "warnings": ["No sources with URLs in inventory. GATE-0b skipped."],
                "violations": [],
            }
        return json.dumps(result, indent=2)

    # Ler o checkpoint
    try:
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        result = {
            "pass": False,
            "gate": "GATE-0b",
            "description": "Title Match Checkpoint Verification",
            "violations": [f"Failed to parse 03-gate0-results.json: {e}"],
        }
        return json.dumps(result, indent=2)

    verifications = checkpoint.get("verifications", [])

    # Extrair fontes com URL do inventory
    sources_with_url = _extract_sources_with_url(inventory_path)

    # Verificar que cada fonte com URL tem uma entry no checkpoint
    verified_ids = {v.get("source_id") for v in verifications}
    for sid in sources_with_url:
        if sid not in verified_ids:
            violations.append(
                f"Source '{sid}' ({sources_with_url[sid].get('url', '?')}) "
                f"has a URL but no GATE-0 verification entry"
            )

    # Verificar consistência match_pct ↔ verdict
    for v in verifications:
        sid = v.get("source_id", "?")
        verdict = v.get("verdict", "")
        match_pct = v.get("match_pct")

        if match_pct is None:
            if verdict in ("MATCH", "MISMATCH"):
                violations.append(
                    f"Source '{sid}': verdict={verdict} but match_pct is missing"
                )
            continue

        try:
            match_pct = float(match_pct)
        except (TypeError, ValueError):
            violations.append(
                f"Source '{sid}': invalid match_pct value: {match_pct}"
            )
            continue

        if verdict == "MATCH" and match_pct < 50:
            violations.append(
                f"Source '{sid}': verdict=MATCH but match_pct={match_pct}% (< 50% threshold)"
            )
        elif verdict == "MISMATCH" and match_pct >= 50:
            violations.append(
                f"Source '{sid}': verdict=MISMATCH but match_pct={match_pct}% (>= 50% threshold)"
            )

    # Cross-reference: verificar que fetched_url corresponde ao source ID
    # (evita que o orchestrator troque IDs acidentalmente)
    for v in verifications:
        sid = v.get("source_id", "")
        fetched_url = v.get("fetched_url", "")
        if sid in sources_with_url:
            expected_url = sources_with_url[sid].get("url", "")
            # Normalizar URLs para comparação (remover trailing slash, www)
            norm_fetched = fetched_url.rstrip("/").replace("https://www.", "https://")
            norm_expected = expected_url.rstrip("/").replace("https://www.", "https://")
            if norm_fetched != norm_expected:
                violations.append(
                    f"Source '{sid}': fetched_url mismatch — "
                    f"expected '{expected_url}', got '{fetched_url}'"
                )

    # Verificar o summary do checkpoint
    summary = checkpoint.get("summary", {})
    total_with_url = summary.get("total_with_url", 0)
    if total_with_url > 0 and total_with_url != len(sources_with_url):
        violations.append(
            f"Summary total_with_url={total_with_url} but inventory has "
            f"{len(sources_with_url)} source(s) with URL"
        )

    result = {
        "pass": len(violations) == 0,
        "gate": "GATE-0b",
        "description": "Title Match Checkpoint Verification",
        "sources_with_url": len(sources_with_url),
        "sources_verified": len(verifications),
        "violations": violations,
    }

    # Adicionar warnings do checkpoint se existirem
    warnings = checkpoint.get("warnings", [])
    if warnings:
        result["warnings"] = warnings

    return json.dumps(result, indent=2)

#!/usr/bin/env python3
"""verify_source_refs.py — GATE-8: Source ID Cross-Reference Check.

Verifica que todos os source_ids citados no 04-synthesis.md e 05-report.md
realmente existem no 02-source-inventory.md. Também detecta fontes órfãs
(presentes no inventory mas nunca citadas).

Uso:
    code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from verify_source_refs import check
print(check(
    "{session_dir}/02-source-inventory.md",
    "{session_dir}/04-synthesis.md",
    "{session_dir}/05-report.md"
))
    ''')
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def _extract_source_ids_from_inventory(inventory_path: str) -> set[str]:
    """Extrai todos os source_ids do 02-source-inventory.md."""
    ids = set()
    try:
        text = Path(inventory_path).read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return ids

    for match in re.finditer(r'\|\s*(S\d+|CODE-\d+)\s*\|', text):
        ids.add(match.group(1).strip())
    return ids


def _extract_cited_source_ids(*file_paths: str) -> set[str]:
    """Extrai todos os source_ids citados nos arquivos (04-synthesis, 05-report).

    Procura por padrões como S1, S15, CODE-03, etc. — sempre precedidos por
    word boundary e com dígitos.
    """
    cited = set()
    for fpath in file_paths:
        try:
            text = Path(fpath).read_text(encoding="utf-8")
        except (OSError, FileNotFoundError):
            continue

        for match in re.finditer(r'\b(S\d+|CODE-\d+)\b', text):
            cited.add(match.group(1).strip())
    return cited


def check(inventory_path: str, synthesis_path: str, report_path: str) -> str:
    """Executa GATE-8 e retorna JSON com resultado."""
    inventory_ids = _extract_source_ids_from_inventory(inventory_path)
    cited_ids = _extract_cited_source_ids(synthesis_path, report_path)

    violations = []

    # 1. Fontes citadas que não existem no inventory
    ghost_ids = cited_ids - inventory_ids
    for gid in sorted(ghost_ids):
        violations.append(
            f"Source '{gid}' cited in synthesis/report but not found in inventory"
        )

    # 2. Fontes no inventory que nunca são citadas (órfãs)
    orphan_ids = inventory_ids - cited_ids
    # Só reportar se houver mais que 2 órfãs (algumas são normais — ex: excluídas)
    if len(orphan_ids) > 2:
        violations.append(
            f"{len(orphan_ids)} sources in inventory are never cited in "
            f"synthesis or report: {', '.join(sorted(orphan_ids)[:10])}"
            + ("..." if len(orphan_ids) > 10 else "")
        )
    elif orphan_ids:
        # Poucas órfãs: listar como WARN, não violação
        pass  # não é violação, apenas nota

    result = {
        "pass": len(violations) == 0,
        "gate": "GATE-8",
        "description": "Source ID Cross-Reference Check",
        "sources_in_inventory": len(inventory_ids),
        "sources_cited": len(cited_ids),
        "ghost_sources": sorted(ghost_ids),
        "orphan_sources": sorted(orphan_ids),
        "violations": violations,
    }

    return json.dumps(result, indent=2)


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 4:
        print(check(sys.argv[1], sys.argv[2], sys.argv[3]))
    else:
        print("Usage: python verify_source_refs.py <inventory> <synthesis> <report>")

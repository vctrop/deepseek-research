#!/usr/bin/env python3
"""helpers.py — Funções utilitárias para o pipeline deepseek-research v3.0.

Chamado via `code_execution` a partir do SKILL.md. Cada função é standalone,
aceitando todos os parâmetros explicitamente — sem estado global, sem leitura
de arquivos de config.

Funções:
    resolve_placeholders   — preencher placeholders computáveis em templates
    compute_sha256         — SHA256 hex digest de um arquivo
    compute_saturation     — verificar saturação de deep reading
    build_subagent_prompt  — dispatch para 2 prompt builders

Uso (no SKILL.md):
    code_execution(code='''
import sys; sys.path.insert(0, '{SKILL_DIR}/scripts')
from helpers import compute_sha256
print(compute_sha256('{session_dir}/01-rq-brief.md'))
    ''')
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from prompts import (
    _build_bibliography_prompt,
    _build_code_prompt,
)

# Re-export resolve_fulltext para code_execution
from fulltext import resolve_fulltext  # noqa: F401


def resolve_placeholders(template_text: str, skill_dir: str = "", session_slug: str = "") -> str:
    """Preencher placeholders computáveis em uma string de template.

    Resolve: {iso8601_utc}, {date}, {skill_git_hash}, {slug}, {date}-{slug}
    NÃO resolve: {RQ_TEXT}, {rq_sha256}, {session_dir} (requerem output de stage).
    """
    from datetime import datetime, timezone

    result = template_text
    now = datetime.now(timezone.utc)
    result = result.replace("{iso8601_utc}", now.isoformat())

    if session_slug:
        result = result.replace("{date}-{slug}", session_slug)
        result = result.replace("{slug}", session_slug)

    result = result.replace("{date}", now.strftime("%Y-%m-%d"))

    git_hash = "unknown"
    if skill_dir:
        try:
            import subprocess
            r = subprocess.run(
                ["git", "-C", skill_dir, "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                git_hash = r.stdout.strip()
        except Exception:
            pass
    result = result.replace("{skill_git_hash}", git_hash)

    return result


def compute_sha256(filepath: str) -> str:
    """SHA256 hex digest de um arquivo. Retorna string vazia em erro."""
    try:
        with open(filepath, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except (OSError, FileNotFoundError):
        return ""


def compute_saturation(deep_reads_dir: str, rq_text: str, last_n: int = 2) -> bool:
    """Verificar se as últimas N deep reads adicionaram claims V ou E novos.

    Examina os arquivos .md em deep_reads_dir ordenados por data de modificação.
    Para as últimas last_n fontes, extrai claims V e E-grade.
    Compara com claims das fontes anteriores. Se nenhum claim V/E novo →
    saturação atingida.

    Args:
        deep_reads_dir: Caminho para o diretório deep-reads/.
        rq_text: Texto da RQ (para logging, não usado na lógica).
        last_n: Número de fontes recentes a verificar (default 2).

    Returns:
        True se saturação atingida (últimas N fontes sem claims V/E novos).
        False se ainda há claims novos ou se < 3 fontes processadas.
    """
    import re

    dir_path = Path(deep_reads_dir)
    if not dir_path.exists():
        return False

    md_files = sorted(
        [f for f in dir_path.glob("*.md") if not f.name.startswith("_")],
        key=lambda f: f.stat().st_mtime
    )

    if len(md_files) < 3:
        return False

    # Coletar claims V/E de fontes anteriores
    prior_files = md_files[:-last_n]
    recent_files = md_files[-last_n:]

    prior_claims: set[str] = set()
    for f in prior_files:
        try:
            text = f.read_text(encoding="utf-8")
            # Extrair claims V e E-grade (padrão: | Cn | "claim text" | V ... |)
            for match in re.finditer(r'\|\s*C\d+\s*\|\s*"([^"]+)"\s*\|\s*(V|E)\s*\|', text):
                # Normalizar: lowercase, strip
                claim = match.group(1).strip().lower()
                prior_claims.add(claim)
        except Exception:
            continue

    if not prior_claims:
        return False

    # Verificar se fontes recentes têm claims novos
    new_claims = 0
    for f in recent_files:
        try:
            text = f.read_text(encoding="utf-8")
            for match in re.finditer(r'\|\s*C\d+\s*\|\s*"([^"]+)"\s*\|\s*(V|E)\s*\|', text):
                claim = match.group(1).strip().lower()
                if claim not in prior_claims:
                    new_claims += 1
        except Exception:
            continue

    return new_claims == 0


def check_coverage_grade_consistency(deep_reads_dir: str, synthesis_path: str) -> str:
    """GATE-5x: verifica se findings STRONG no 04-synthesis citam fontes
    com coverage suficiente.

    Returns:
        JSON string com {"pass": bool, "violations": [...]}
    """
    import json as _json
    import re as _re
    from pathlib import Path as _Path

    dir_path = _Path(deep_reads_dir)
    violations = []

    # 1. Extrair coverage de cada deep read
    coverage_map: dict[str, float | None] = {}
    if dir_path.exists():
        for fpath in sorted(dir_path.glob("*.md")):
            if fpath.name.startswith("_"):
                continue
            try:
                text = fpath.read_text(encoding="utf-8")
            except Exception:
                continue
            sid = fpath.stem
            cov_match = _re.search(r'\*\*Coverage:\*\*\s*([\d.]+)%', text)
            if cov_match:
                try:
                    coverage_map[sid] = float(cov_match.group(1))
                except ValueError:
                    coverage_map[sid] = None
            else:
                coverage_map[sid] = None

    # 2. Extrair findings STRONG do synthesis
    try:
        synth_text = _Path(synthesis_path).read_text(encoding="utf-8")
    except Exception:
        return _json.dumps({"pass": True, "note": "synthesis file not found", "violations": []})

    # Procurar blocos de finding STRONG e os source_ids citados neles
    # Estratégia: encontrar "STRONG" e depois extrair S\d+ ou CODE-\d+ no parágrafo
    strong_blocks = _re.split(r'\n(?=###|\*\*STRONG)', synth_text)
    for block in strong_blocks:
        if "STRONG" not in block.upper():
            continue
        cited_ids = set(_re.findall(r'\b(S\d+|CODE-\d+)\b', block))
        for cid in cited_ids:
            cov = coverage_map.get(cid)
            if cov is None:
                violations.append(
                    f"STRONG finding cites source '{cid}' with unknown coverage "
                    f"(not in deep-reads or coverage not reported)"
                )
            elif cov < 50:
                violations.append(
                    f"STRONG finding cites source '{cid}' with only {cov:.0f}% coverage"
                )

    result = {
        "pass": len(violations) == 0,
        "gate": "GATE-5x",
        "description": "Coverage-Grade Consistency Check",
        "violations": violations,
    }
    return _json.dumps(result, indent=2)


def check_iron_rule_c_deterministic(report_path: str, synthesis_path: str) -> str:
    """GATE-2 determinístico: Iron Rule C com filtro de contexto.

    Substitui o grep cego por análise com 4 filtros de exclusão:
      1. Verbatim quote entre aspas com atribuição
      2. Negação ("not validated", "failed to confirm")
      3. Atribuição externa ("Smith et al. confirmed")
      4. Meta-linguagem ("this finding was confirmed")

    Returns:
        JSON string com {"pass": bool, "violations": [...]}
    """
    import json as _json
    import re as _re
    from pathlib import Path as _Path

    BARE_CLAIM_WORDS = [
        "validated", "proved", "confirmed", "demonstrated",
        "ensures", "guarantees", "always", "never",
        "optimal", "definitive", "conclusive",
        "certainly", "undoubtedly", "obviously", "clearly",
    ]

    violations = []
    files_to_check = []

    for fpath_str in [report_path, synthesis_path]:
        p = _Path(fpath_str)
        if p.exists():
            files_to_check.append(p)

    for fpath in files_to_check:
        try:
            text = fpath.read_text(encoding="utf-8")
        except Exception:
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            line_lower = line.lower()
            for word in BARE_CLAIM_WORDS:
                if word not in line_lower:
                    continue

                # Verificar padrões de exclusão
                window_start = max(0, line_lower.find(word) - 60)
                window_end = min(len(line_lower), line_lower.find(word) + len(word) + 60)
                context = line_lower[window_start:window_end]

                excluded = False

                # 1. Verbatim quote entre aspas com atribuição
                if _re.search(r'"[^"]*\b' + word + r'\b[^"]*"\s*(?:\(|\[|—)', context):
                    excluded = True

                # 2. Negação
                if _re.search(
                    r'\b(?:not|never|failed\s+to|does\s+not|do\s+not)\s+\w*\s*\b' + word + r'\b',
                    context
                ):
                    excluded = True

                # 3. Atribuição externa
                if _re.search(
                    r'\b(?:et\s+al\.?|authors?|researchers?|study|paper|work)\b',
                    context
                ):
                    excluded = True

                # 4. Meta-linguagem
                if _re.search(
                    r'\b(?:this|these|our|the)\s+\w+\s+(?:was|were|is|are|has|have)\s+\b' + word + r'\b',
                    context
                ):
                    excluded = True

                # 5. Auto-declaração da skill (ex: "No bare claims (validated, proved, ...)")
                if _re.search(
                    r'\b(?:no\s+bare\s+claims?|bare\s+claims?|iron\s+rule\s+c|'
                    r'qualified\s+language|all\s+claims\s+in\s+this\s+report|'
                    r'claims?\s+nus?)\b',
                    context
                ):
                    excluded = True

                # 6. Palavras proibidas listadas em sequência (ex: "validated, proved, confirmed...")
                bare_words_in_context = sum(
                    1 for w in BARE_CLAIM_WORDS if w in context
                )
                if bare_words_in_context >= 4:
                    excluded = True  # É uma lista de palavras proibidas, não um claim

                if not excluded:
                    violations.append({
                        "file": str(fpath.name),
                        "line": lineno,
                        "word": word,
                        "context": line.strip()[:120],
                    })

    result = {
        "pass": len(violations) == 0,
        "gate": "GATE-2",
        "description": "Iron Rule C (deterministic with context filters)",
        "violations": violations,
    }
    return _json.dumps(result, indent=2)


def build_subagent_prompt(
    template_name: str,  # "dsr-bibliography" | "dsr-code"
    **kwargs: str,
) -> str:
    """Constrói um prompt de sub-agent com interpolação segura.

    Templates suportados:
      - dsr-bibliography: kwargs = {rq_text, bibliography_path, main_topic,
        topics (optional), local_sources_json (optional)}
      - dsr-code: kwargs = {rq_text}
    """
    prompts = {
        "dsr-bibliography": _build_bibliography_prompt,
        "dsr-code": _build_code_prompt,
    }
    builder = prompts.get(template_name)
    if builder is None:
        raise ValueError(f"Unknown template: {template_name}. Valid: {list(prompts.keys())}")
    return builder(**kwargs)


def config_ensure(project_root: str = ".") -> str:
    """Verifica e corrige o arquivo .deepseek/deepseek-research.toml.

    Se o arquivo não existir, cria com todos os defaults.
    Se existir, adiciona chaves faltantes com valores default.
    Chaves existentes NUNCA são sobrescritas.

    Args:
        project_root: Caminho para o root do projeto (default: cwd).

    Returns:
        String descritiva: "created" | "added N keys: ..." | "ok".
    """
    import tomllib
    from pathlib import Path

    # Defaults (espelham SKILL.md § Configuration)
    DEFAULTS = {
        "source_axes": '["bibliography", "codebase"]',
        "output_dir": '"research-reports/"',
        "deep_reading": "true",
        "max_deep_reads": "10",
        "max_sources_per_axis": "20",
        "bibliography_path": '"bibliography/"',
        "oss_clone_dir": '"oss/"',
        "unpaywall_email": '""',
        "allow_scihub": "false",
        "scihub_domain": '""',
    }

    root = Path(project_root).resolve()
    config_dir = root / ".deepseek"
    config_path = config_dir / "deepseek-research.toml"

    # Parse existing if present
    existing: dict[str, str] = {}
    if config_path.exists():
        try:
            raw = config_path.read_text(encoding="utf-8")
            # Parse with tomllib to get structured values
            parsed = tomllib.loads(raw)
            # Convert back to TOML-compatible string values for re-emission
            for key, value in parsed.items():
                if isinstance(value, bool):
                    existing[key] = "true" if value else "false"
                elif isinstance(value, list):
                    items = ", ".join(f'"{v}"' for v in value)
                    existing[key] = f"[{items}]"
                elif isinstance(value, str):
                    existing[key] = f'"{value}"'
                elif isinstance(value, (int, float)):
                    existing[key] = str(value)
                else:
                    existing[key] = f'"{value}"'
        except Exception:
            # If TOML is corrupted, fall back to regex line parsing
            for line in raw.splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, _, val = line.partition("=")
                    existing[key.strip()] = val.strip()

    # Determine missing keys
    missing = {k: v for k, v in DEFAULTS.items() if k not in existing}

    if not missing and config_path.exists():
        return "ok"

    # Build TOML content
    config_dir.mkdir(parents=True, exist_ok=True)

    if not config_path.exists():
        # Create from scratch with all defaults
        lines = ["# deepseek-research v3.1 — Configuração auto-gerada\n"]
        for key, val in DEFAULTS.items():
            lines.append(f"{key} = {val}")
        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return "created"
    else:
        # Append missing keys
        with open(config_path, "a", encoding="utf-8") as f:
            f.write("\n# Auto-adicionados por config_ensure:\n")
            for key, val in missing.items():
                f.write(f"{key} = {val}\n")
        keys_list = ", ".join(missing.keys())
        return f"added {len(missing)} keys: {keys_list}"

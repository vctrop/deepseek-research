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


def build_subagent_prompt(
    template_name: str,  # "dsr-bibliography" | "dsr-code"
    **kwargs: str,
) -> str:
    """Constrói um prompt de sub-agent com interpolação segura.

    Templates suportados:
      - dsr-bibliography: kwargs = {rq_text, bibliography_path, main_topic, topics (optional)}
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

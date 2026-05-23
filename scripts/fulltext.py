#!/usr/bin/env python3
"""fulltext.py — PDF full-text acquisition para deepseek-research v3.0.

Implementa a cadeia de fallback SPEC-003:
  1. arXiv PDF direto (se arXiv ID disponível)
  2. Unpaywall API (legal, DOI → OA PDF URL)
  3. Sci-Hub (shadow library, opt-in)

Inclui evasão de detecção por editoras:
  - Headers de browser realista (Chrome Linux)
  - Rate limiting com delay aleatório
  - Cookie/sessão para publishers

Chamado via `code_execution` a partir do SKILL.md Stage 3.

Uso:
    code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from fulltext import resolve_fulltext
result = resolve_fulltext(
    doi="10.1038/nature12373",
    arxiv_id=None,
    source_id="S1",
    output_dir="{session_dir}/pdfs/",
    unpaywall_email="user@example.com",
    allow_scihub=False,
)
print(json.dumps(result))
    ''')
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

# ── Evasão de detecção ──────────────────────────────────────────────

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Domínios Sci-Hub conhecidos (tentados em ordem)
_SCI_HUB_DOMAINS = [
    "sci-hub.st",
    "sci-hub.se",
    "sci-hub.ru",
]

# Timeout HTTP padrão (segundos)
_HTTP_TIMEOUT = 30


def _interrequest_delay():
    """Delay aleatório entre requests para evitar detecção de bot."""
    time.sleep(random.uniform(1.5, 4.0))


def _http_get(url: str, headers: dict | None = None, timeout: int = _HTTP_TIMEOUT) -> tuple[int, bytes]:
    """HTTP GET com headers de browser. Retorna (status_code, body_bytes)."""
    if headers is None:
        headers = dict(BROWSER_HEADERS)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError:
        return 0, b""


def _http_get_text(url: str, headers: dict | None = None, timeout: int = _HTTP_TIMEOUT) -> tuple[int, str]:
    """HTTP GET retornando texto decodificado."""
    status, body = _http_get(url, headers=headers, timeout=timeout)
    text = ""
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        pass
    return status, text


def _download_binary(url: str, output_path: str, headers: dict | None = None) -> bool:
    """Baixa conteúdo binário de uma URL para arquivo local. Retorna True em sucesso."""
    status, body = _http_get(url, headers=headers)
    if status == 200 and body:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(body)
        return True
    return False


# ── arXiv PDF ───────────────────────────────────────────────────────

def _resolve_arxiv_pdf(arxiv_id: str, source_id: str, output_dir: str) -> dict | None:
    """Tenta baixar PDF diretamente do arXiv.

    arXiv IDs podem ser:
      - formato novo: YYMM.NNNNN (ex: 2407.16833)
      - formato antigo: subject/YYMMNNN (ex: hep-th/9901001)

    URL: https://arxiv.org/pdf/{id}.pdf
    """
    _interrequest_delay()
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    pdf_path = os.path.join(output_dir, f"{source_id}.pdf")

    status, _body = _http_get(pdf_url)
    if status != 200:
        return None

    if _download_binary(pdf_url, pdf_path):
        return {
            "status": "arxiv",
            "pdf_path": pdf_path,
            "pdf_url": pdf_url,
            "method": "arxiv_pdf_direct",
        }
    return None


# ── Unpaywall API ───────────────────────────────────────────────────

def _resolve_unpaywall(doi: str, email: str) -> dict | None:
    """Consulta a Unpaywall API v2 para localizar cópia OA do paper.

    Args:
        doi: DOI do paper (ex: "10.1038/nature12373")
        email: Email para identificar o usuário (requerido pela Unpaywall TOS)

    Returns:
        dict com chaves is_oa, oa_status, pdf_url, host_type, license, version,
        ou None se a API falhar.
    """
    _interrequest_delay()
    api_url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    status, text = _http_get_text(api_url)

    if status != 200:
        return None

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not data.get("is_oa"):
        return None

    best = data.get("best_oa_location")
    if not best:
        return None

    pdf_url = best.get("url_for_pdf") or best.get("url")
    if not pdf_url:
        return None

    return {
        "is_oa": True,
        "oa_status": data.get("oa_status"),
        "pdf_url": pdf_url,
        "host_type": best.get("host_type"),
        "license": best.get("license"),
        "version": best.get("version"),
        "title": data.get("title"),
        "journal": data.get("journal_name"),
    }


def _download_unpaywall_pdf(oa_info: dict, source_id: str, output_dir: str) -> dict | None:
    """Baixa o PDF da URL fornecida pelo Unpaywall."""
    pdf_url = oa_info["pdf_url"]
    pdf_path = os.path.join(output_dir, f"{source_id}.pdf")

    if _download_binary(pdf_url, pdf_path):
        return {
            "status": "oa",
            "pdf_path": pdf_path,
            "pdf_url": pdf_url,
            "oa_status": oa_info.get("oa_status"),
            "host_type": oa_info.get("host_type"),
            "license": oa_info.get("license"),
            "version": oa_info.get("version"),
            "method": f"unpaywall_{oa_info.get('host_type', 'unknown')}",
        }
    return None


# ── Sci-Hub ─────────────────────────────────────────────────────────

def _resolve_scihub(doi: str, domain: str) -> str | None:
    """Resolve um DOI via Sci-Hub e retorna a URL direta do PDF.

    Args:
        doi: DOI do paper
        domain: Domínio Sci-Hub ativo (ex: "sci-hub.st")

    Returns:
        URL direta do PDF ou None se falhar.
    """
    _interrequest_delay()
    scihub_url = f"https://{domain}/{doi}"
    status, html = _http_get_text(scihub_url)

    if status != 200:
        return None

    # Padrões comuns de embed de PDF no Sci-Hub
    patterns = [
        r'<iframe\s+[^>]*src\s*=\s*["\']([^"\']*\.pdf[^"\']*)["\']',
        r'<embed\s+[^>]*src\s*=\s*["\']([^"\']*\.pdf[^"\']*)["\']',
        r'location\.href\s*=\s*["\']([^"\']*\.pdf[^"\']*)["\']',
        r'<a\s+[^>]*href\s*=\s*["\']([^"\']*\.pdf[^"\']*)["\']',
        r'<button[^>]*onclick\s*=\s*["\']location\.href\s*=\s*[\'"]([^\'"]*\.pdf[^\'"]*)[\'"]',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            pdf_url = match.group(1)
            # Resolver URLs relativas
            if pdf_url.startswith("//"):
                pdf_url = "https:" + pdf_url
            elif pdf_url.startswith("/"):
                pdf_url = urljoin(f"https://{domain}", pdf_url)
            elif not pdf_url.startswith("http"):
                pdf_url = urljoin(f"https://{domain}", pdf_url)

            # Filtrar falsos positivos comuns
            if "sci-hub" in pdf_url.lower() and not pdf_url.endswith(".pdf"):
                continue  # provavelmente outra página HTML
            return pdf_url

    return None


def _try_scihub_domains(doi: str, domains: list[str]) -> str | None:
    """Tenta múltiplos domínios Sci-Hub. Retorna URL do PDF ou None."""
    for domain in domains:
        pdf_url = _resolve_scihub(doi, domain)
        if pdf_url:
            return pdf_url
    return None


def _download_scihub_pdf(pdf_url: str, source_id: str, output_dir: str) -> dict | None:
    """Baixa o PDF da URL resolvida pelo Sci-Hub."""
    pdf_path = os.path.join(output_dir, f"{source_id}.pdf")

    if _download_binary(pdf_url, pdf_path):
        return {
            "status": "scihub",
            "pdf_path": pdf_path,
            "pdf_url": pdf_url,
            "method": "scihub",
        }
    return None


# ── Orquestrador ────────────────────────────────────────────────────

def resolve_fulltext(
    doi: str | None = None,
    arxiv_id: str | None = None,
    source_id: str = "S0",
    output_dir: str = "/tmp/dsr-pdfs/",
    unpaywall_email: str = "",
    allow_scihub: bool = False,
    scihub_domain: str = "",
) -> dict:
    """Resolve o texto completo de uma fonte bibliográfica.

    Cadeia de fallback:
      1. arXiv PDF (se arxiv_id fornecido)
      2. Unpaywall API (se doi e unpaywall_email fornecidos)
      3. Sci-Hub (se allow_scihub=True e doi fornecido)

    Args:
        doi: DOI do paper (opcional)
        arxiv_id: ID do arXiv (opcional, ex: "2407.16833")
        source_id: Identificador da fonte (para nomear o arquivo)
        output_dir: Diretório para salvar o PDF
        unpaywall_email: Email para API Unpaywall
        allow_scihub: Habilitar fallback Sci-Hub
        scihub_domain: Domínio Sci-Hub específico (auto-detecta se vazio)

    Returns:
        dict: {
            "status": "arxiv" | "oa" | "scihub" | "unavailable",
            "pdf_path": str | None,
            "pdf_url": str | None,
            "method": str,
            "error": str | None  (apenas se unavailable)
        }
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. arXiv PDF
    if arxiv_id:
        result = _resolve_arxiv_pdf(arxiv_id, source_id, output_dir)
        if result:
            return result

    # 2. Unpaywall
    if doi and unpaywall_email:
        oa_info = _resolve_unpaywall(doi, unpaywall_email)
        if oa_info:
            result = _download_unpaywall_pdf(oa_info, source_id, output_dir)
            if result:
                return result

    # 3. Sci-Hub (opt-in)
    if doi and allow_scihub:
        domains = [scihub_domain] if scihub_domain else _SCI_HUB_DOMAINS
        pdf_url = _try_scihub_domains(doi, domains)
        if pdf_url:
            result = _download_scihub_pdf(pdf_url, source_id, output_dir)
            if result:
                return result

    # Fallback: indisponível
    error_parts = []
    if doi and not unpaywall_email:
        error_parts.append("Unpaywall not configured (unpaywall_email empty)")
    if doi and not allow_scihub:
        error_parts.append("Sci-Hub disabled (allow_scihub=false)")
    if not doi and not arxiv_id:
        error_parts.append("No DOI or arXiv ID provided")

    return {
        "status": "unavailable",
        "pdf_path": None,
        "pdf_url": None,
        "method": "none",
        "error": "; ".join(error_parts) if error_parts else "All methods exhausted",
    }


# ── Smoke test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    # Teste básico: arXiv PDF de paper conhecido
    print("=== Smoke test: fulltext.py ===")
    result = resolve_fulltext(
        arxiv_id="2407.16833",
        source_id="test",
        output_dir="/tmp/dsr-pdfs-test/",
    )
    print(json.dumps(result, indent=2))
    if result["pdf_path"]:
        size = os.path.getsize(result["pdf_path"])
        print(f"  PDF size: {size} bytes")
        # SHA256 do PDF
        sha = hashlib.sha256()
        with open(result["pdf_path"], "rb") as f:
            sha.update(f.read())
        print(f"  SHA256: {sha.hexdigest()}")

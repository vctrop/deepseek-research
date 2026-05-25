#!/usr/bin/env python3
"""fulltext.py — PDF full-text acquisition para deepseek-research v3.1.

Implementa a cadeia de fallback SPEC-003 expandida:
  1. arXiv PDF direto (se arXiv ID disponível)
  2. Unpaywall API (legal, DOI → OA PDF URL)
  3. Shadow libraries configuráveis (opt-in), em ordem:
     - Sci-Hub + SciDB mirrors
     - Library Genesis SciMag
     - Anna's Archive metasearch
  4. Abstract via DOI (fallback mínimo, sempre ativo)

Inclui evasão de detecção por editoras:
  - Headers de browser realista (Chrome Linux)
  - Rate limiting com delay aleatório
  - Detecção de Cloudflare/paywall para evitar falsos positivos

Chamado via `code_execution` a partir do SKILL.md Stage 3.

Uso:
    code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from fulltext import resolve_fulltext
result = resolve_fulltext(
    doi="10.1038/nature12373",
    source_id="S1",
    output_dir="{session_dir}/pdfs/",
    unpaywall_email="user@example.com",
    shadow_libraries=["scihub", "libgen"],
)
print(json.dumps(result))
    ''')
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin

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
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Domínios Sci-Hub + mirrors conhecidos (tentados em ordem)
# Inclui SciDB (continuação do Sci-Hub) e mirrors regionais.
# Fonte: shadowlibraries.github.io, atualizado 2026-05.
_SCI_HUB_DOMAINS = [
    "sci-hub.st",
    "sci-hub.se",
    "sci-hub.ru",
    "sci-hub.hlgczx.com",
    "sci-hub.mobi",
    "scidb.org",
    "sci-hub.ee",
]

# Timeout HTTP padrão (segundos)
_HTTP_TIMEOUT = 30

# Tamanho máximo de PDF aceito (50 MB)
_MAX_PDF_BYTES = 50 * 1024 * 1024


def _interrequest_delay():
    """Delay aleatório entre requests para evitar detecção de bot."""
    time.sleep(random.uniform(1.5, 4.0))


def _http_get(url: str, headers: dict | None = None, timeout: int = _HTTP_TIMEOUT) -> tuple[int, bytes, int]:
    """HTTP GET com headers de browser. Retorna (status_code, body_bytes, content_length).

    content_length é extraído do header Content-Length, ou 0 se ausente.
    Decompõe automaticamente respostas gzip/deflate.
    """
    if headers is None:
        headers = dict(BROWSER_HEADERS)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            content_encoding = resp.headers.get("Content-Encoding", "").lower()
            if "gzip" in content_encoding:
                body = gzip.decompress(body)
            elif "deflate" in content_encoding:
                import zlib
                body = zlib.decompress(body)
            clen = int(resp.headers.get("Content-Length", 0))
            return resp.status, body, clen
    except urllib.error.HTTPError as e:
        body = e.read()
        clen = int(e.headers.get("Content-Length", 0)) if hasattr(e, "headers") else 0
        return e.code, body, clen
    except urllib.error.URLError:
        return 0, b"", 0


def _http_get_text(url: str, headers: dict | None = None, timeout: int = _HTTP_TIMEOUT) -> tuple[int, str]:
    """HTTP GET retornando texto decodificado."""
    status, body, _clen = _http_get(url, headers=headers, timeout=timeout)
    text = ""
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        pass
    return status, text


def _download_binary(url: str, output_path: str, headers: dict | None = None) -> bool:
    """Baixa conteúdo binário de uma URL para arquivo local.

    Verifica Content-Length antes do download; rejeita se > _MAX_PDF_BYTES.
    Retorna True em sucesso.
    """
    status, body, content_length = _http_get(url, headers=headers)

    # Verificar tamanho antes de salvar
    effective_size = content_length if content_length > 0 else len(body)
    if effective_size > _MAX_PDF_BYTES:
        return False

    if status == 200 and body:
        # Validar que o conteúdo é realmente um PDF (se extensão for .pdf)
        if output_path.endswith(".pdf") and not body.startswith(b"%PDF"):
            return False
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

    status, body, content_length = _http_get(pdf_url)
    if status != 200:
        return None

    # Verificar tamanho antes de salvar
    effective_size = content_length if content_length > 0 else len(body)
    if effective_size > _MAX_PDF_BYTES:
        return None

    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    with open(pdf_path, "wb") as f:
        f.write(body)

    return {
        "status": "arxiv",
        "pdf_path": pdf_path,
        "pdf_url": pdf_url,
        "method": "arxiv_pdf_direct",
    }


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


def _download_shadow_pdf(
    pdf_url: str, source_id: str, output_dir: str, method: str
) -> dict | None:
    """Baixa PDF de uma shadow library genérica.

    Args:
        pdf_url: URL direta do PDF.
        source_id: Identificador da fonte.
        output_dir: Diretório de output.
        method: Nome do método para o campo 'method' (ex: "scihub", "libgen").

    Returns:
        dict com status/method/pdf_path ou None.
    """
    pdf_path = os.path.join(output_dir, f"{source_id}.pdf")
    _interrequest_delay()
    if _download_binary(pdf_url, pdf_path):
        return {
            "status": method,
            "pdf_path": pdf_path,
            "pdf_url": pdf_url,
            "method": method,
        }
    return None


# Backward-compat wrapper
def _download_scihub_pdf(pdf_url: str, source_id: str, output_dir: str) -> dict | None:
    return _download_shadow_pdf(pdf_url, source_id, output_dir, "scihub")


# ── Library Genesis (SciMag) ─────────────────────────────────────────

# Domínios LibGen SciMag conhecidos (tentados em ordem)
_LIBGEN_SCIMAG_DOMAINS = [
    "libgen.is",
    "libgen.li",
    "libgen.rs",
]


def _resolve_libgen(doi: str) -> str | None:
    """Tenta resolver um DOI via LibGen SciMag JSON API.

    LibGen expõe um endpoint JSON informal em /scimag/json.php?doi={doi}.
    Constrói URL de download a partir do MD5 como fallback quando
    download_url está ausente.

    Returns:
        URL de download direto ou None.
    """
    import urllib.parse

    for domain in _LIBGEN_SCIMAG_DOMAINS:
        _interrequest_delay()
        json_url = f"https://{domain}/scimag/json.php?doi={doi}"
        status, text = _http_get_text(json_url)
        if status != 200:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue

        if isinstance(data, list):
            for item in data:
                url = _extract_libgen_download_url(item)
                if url:
                    return url
        elif isinstance(data, dict):
            url = _extract_libgen_download_url(data)
            if url:
                return url

    return None


def _extract_libgen_download_url(item: dict) -> str | None:
    """Extrai URL de download de um item do JSON do LibGen.

    Tenta download_url direto primeiro; fallback para construção
    via MD5 + título.
    """
    # Tentar campo download_url ou link direto
    url = item.get("download_url") or item.get("link")
    if url:
        return url

    # Fallback: construir URL a partir do MD5
    md5 = item.get("md5")
    if not md5:
        return None

    title = item.get("title", "paper")
    # Sanitizar título para URL
    safe_title = title[:100].replace(" ", "_").replace("/", "_")
    safe_title = "".join(c for c in safe_title if c.isalnum() or c in "._-")
    if not safe_title:
        safe_title = "paper"

    return f"https://download.library.lol/main/{md5}/{safe_title}.pdf"


# ── Anna's Archive ───────────────────────────────────────────────────

_ANNA_ARCHIVE_URL = "https://annas-archive.org"

# Sinais de Cloudflare challenge no HTML
_CLOUDFLARE_SIGNALS = [
    "Checking your browser",
    "Just a moment",
    "cf-browser-verify",
    "cf-challenge",
]


def _resolve_annas_archive(doi: str) -> str | None:
    """Tenta resolver um DOI via Anna's Archive (HTML scraping).

    Anna's Archive é um metasearch que agrega Sci-Hub, LibGen, Z-Library
    e Internet Archive. Não hospeda PDFs — redireciona para a fonte original.

    Returns:
        URL direta do PDF ou None.
    """
    # 1. Buscar por DOI na página de search
    _interrequest_delay()
    search_url = f"{_ANNA_ARCHIVE_URL}/search?q={doi}"
    status, html = _http_get_text(search_url, timeout=_HTTP_TIMEOUT)
    if status != 200:
        return None

    # Detectar Cloudflare challenge antes de tentar parse
    if _is_cloudflare_block(html):
        return None

    # 2. Extrair link para a página de detalhe (md5 em path ou query param)
    md5_match = re.search(r'href="[^"]*md5[=/]([a-f0-9]{32})', html)
    if not md5_match:
        return None

    md5_hash = md5_match.group(1)
    detail_url = f"{_ANNA_ARCHIVE_URL}/md5/{md5_hash}"

    # 3. Acessar página de detalhe para extrair link de download
    _interrequest_delay()
    status2, html2 = _http_get_text(detail_url, timeout=_HTTP_TIMEOUT)
    if status2 != 200:
        return None

    if _is_cloudflare_block(html2):
        return None

    # 4. Extrair link de download — PDF direto ou IPFS
    pdf_match = re.search(r'href="(https?://[^"]+\.pdf)"', html2)
    if pdf_match:
        return pdf_match.group(1)

    ipfs_match = re.search(r'href="(https?://ipfs\.io/ipfs/[a-zA-Z0-9]+[^"]*)"', html2)
    if ipfs_match:
        return ipfs_match.group(1)

    return None


def _is_cloudflare_block(html: str) -> bool:
    """Detecta página de bloqueio Cloudflare no HTML."""
    html_lower = html.lower()
    return any(signal.lower() in html_lower for signal in _CLOUDFLARE_SIGNALS)


# ── Abstract Fallback ────────────────────────────────────────────────

# Meta tags comuns para abstract em páginas de publisher
_ABSTRACT_META_PATTERNS = [
    re.compile(r'<meta\s+name="description"\s+content="([^"]{100,})"', re.I),
    re.compile(r'<meta\s+name="citation_abstract"\s+content="([^"]+)"', re.I),
    re.compile(r'<meta\s+property="og:description"\s+content="([^"]{100,})"', re.I),
    re.compile(r'<meta\s+name="dc\.description"\s+content="([^"]{100,})"', re.I),
]

# Container estrutural para abstract (div ou section)
_ABSTRACT_CONTAINER_PATTERN = re.compile(
    r'<(?:div|section)[^>]*class="[^"]*abstract[^"]*"[^>]*>(.*?)</(?:div|section)>',
    re.I | re.DOTALL,
)

# Sinais de página de login/paywall (falso positivo para abstract)
_LOGIN_SIGNALS = [
    "sign in", "log in", "subscribe", "purchase now",
    "access through", "institutional access", "checkout",
    "add to cart", "rent", "get access",
]


def _fetch_abstract_via_doi(doi: str) -> str | None:
    """Tenta extrair o abstract de um paper via DOI (dx.doi.org).

    Acessa a página do publisher via redirecionamento do DOI.
    Extrai abstract de meta tags ou div/section abstract.
    Não requer autenticação — funciona para publishers que exibem
    abstract publicamente mesmo com paywall no PDF.

    Returns:
        Texto do abstract (até 2000 chars) ou None.
    """
    import html as html_mod

    _interrequest_delay()
    doi_url = f"https://doi.org/{doi}"
    status, html_text = _http_get_text(doi_url)
    if status != 200:
        return None

    # Descartar páginas de login/paywall
    if _is_login_page(html_text):
        return None

    # Tentar meta tags primeiro (mais confiável)
    for pattern in _ABSTRACT_META_PATTERNS:
        match = pattern.search(html_text)
        if match:
            abstract = html_mod.unescape(match.group(1))
            if len(abstract) >= 100:
                return abstract[:2000]

    # Fallback: container estrutural
    match = _ABSTRACT_CONTAINER_PATTERN.search(html_text)
    if match:
        raw = match.group(1)
        clean = re.sub(r'<[^>]+>', ' ', raw)
        clean = re.sub(r'\s+', ' ', clean).strip()
        clean = html_mod.unescape(clean)
        if len(clean) >= 100:
            return clean[:2000]

    return None


def _is_login_page(html_text: str) -> bool:
    """Detecta página de login/paywall que não contém abstract real."""
    html_lower = html_text.lower()
    return any(signal in html_lower for signal in _LOGIN_SIGNALS)


# ── Orquestrador ────────────────────────────────────────────────────

# Whitelist de shadow libraries válidas
_SHADOW_LIBRARY_WHITELIST = {"scihub", "libgen", "annas_archive"}


def resolve_fulltext(
    doi: str | None = None,
    arxiv_id: str | None = None,
    source_id: str = "S0",
    output_dir: str = "/tmp/dsr-pdfs/",
    unpaywall_email: str = "",
    shadow_libraries: list[str] | None = None,
    scihub_domain: str = "",
) -> dict:
    """Resolve o texto completo de uma fonte bibliográfica.

    Cadeia de fallback:
      1. arXiv PDF (se arxiv_id fornecido)
      2. Unpaywall API (se doi e unpaywall_email fornecidos)
      3. Shadow libraries (em ordem, se habilitadas em shadow_libraries):
         - "scihub": Sci-Hub + mirrors (inclui SciDB)
         - "libgen": Library Genesis SciMag
         - "annas_archive": Anna's Archive metasearch
      4. Abstract via DOI (fallback mínimo, sempre ativo)

    Args:
        doi: DOI do paper (opcional)
        arxiv_id: ID do arXiv (opcional, ex: "2407.16833")
        source_id: Identificador da fonte (para nomear o arquivo)
        output_dir: Diretório para salvar o PDF
        unpaywall_email: Email para API Unpaywall
        shadow_libraries: Lista de shadow libraries habilitadas, em ordem
                          de fallback. None ou [] = nenhuma.
        scihub_domain: Domínio Sci-Hub específico (auto-detecta se vazio)

    Returns:
        dict: {
            "status": "arxiv" | "oa" | "scihub" | "libgen" | "annas_archive"
                     | "abstract_only" | "unavailable",
            "pdf_path": str | None,
            "pdf_url": str | None,
            "abstract": str | None,
            "method": str,
            "error": str | None  (apenas se unavailable)
        }
    """
    os.makedirs(output_dir, exist_ok=True)

    if shadow_libraries is None:
        shadow_libraries = []

    # Validar e filtrar shadow libraries desconhecidas
    unknown = [lib for lib in shadow_libraries if lib not in _SHADOW_LIBRARY_WHITELIST]
    if unknown:
        import sys as _sys
        print(
            f"WARNING: unknown shadow libraries ignored: {unknown}",
            file=_sys.stderr,
        )
    shadow_libraries = [lib for lib in shadow_libraries if lib in _SHADOW_LIBRARY_WHITELIST]

    # 1. arXiv PDF
    if arxiv_id:
        result = _resolve_arxiv_pdf(arxiv_id, source_id, output_dir)
        if result:
            return result

    # 2. Unpaywall (legal)
    if doi and unpaywall_email:
        oa_info = _resolve_unpaywall(doi, unpaywall_email)
        if oa_info:
            result = _download_unpaywall_pdf(oa_info, source_id, output_dir)
            if result:
                return result

    # 3. Shadow libraries (em ordem, se habilitadas)
    if doi:
        if "scihub" in shadow_libraries:
            # Normalizar scihub_domain: remover protocolo e trailing slash
            if scihub_domain:
                domain = scihub_domain.strip()
                domain = re.sub(r'^https?://', '', domain)
                domain = domain.rstrip('/')
                domains = [domain] if domain else _SCI_HUB_DOMAINS
            else:
                domains = _SCI_HUB_DOMAINS
            pdf_url = _try_scihub_domains(doi, domains)
            if pdf_url:
                result = _download_shadow_pdf(pdf_url, source_id, output_dir, "scihub")
                if result:
                    return result

        if "libgen" in shadow_libraries:
            pdf_url = _resolve_libgen(doi)
            if pdf_url:
                result = _download_shadow_pdf(pdf_url, source_id, output_dir, "libgen")
                if result:
                    return result

        if "annas_archive" in shadow_libraries:
            pdf_url = _resolve_annas_archive(doi)
            if pdf_url:
                result = _download_shadow_pdf(pdf_url, source_id, output_dir, "annas_archive")
                if result:
                    return result

    # 4. Abstract via DOI (fallback mínimo, sempre ativo)
    if doi:
        abstract = _fetch_abstract_via_doi(doi)
        if abstract:
            return {
                "status": "abstract_only",
                "pdf_path": None,
                "pdf_url": None,
                "abstract": abstract[:2000],
                "method": "doi_abstract",
            }

    # Fallback: indisponível
    error_parts = []
    if doi and not unpaywall_email:
        error_parts.append("Unpaywall not configured (unpaywall_email empty)")
    if doi and not shadow_libraries:
        error_parts.append("No shadow libraries enabled")
    if not doi and not arxiv_id:
        error_parts.append("No DOI or arXiv ID provided")

    return {
        "status": "unavailable",
        "pdf_path": None,
        "pdf_url": None,
        "abstract": None,
        "method": "none",
        "error": "; ".join(error_parts) if error_parts else "All methods exhausted",
    }


# ── Batch resolver ──────────────────────────────────────────────────

DOI_PATTERN = re.compile(r'\b(10\.\d{4,}/[^\s\]]+)')
ARXIV_ID_PATTERN = re.compile(r'arXiv:(\d{4}\.\d{4,5}(?:v\d+)?)')


def resolve_all_fulltext(
    inventory_path: str,
    output_dir: str,
    unpaywall_email: str = "",
    shadow_libraries: list[str] | None = None,
    scihub_domain: str = "",
) -> str:
    """Lê 02-source-inventory.md, extrai DOI e arXiv ID, resolve em batch.

    Retorna JSON com mapping source_id → resultado e sumário.
    """
    try:
        with open(inventory_path, "r", encoding="utf-8") as f:
            inventory_text = f.read()
    except (OSError, FileNotFoundError):
        return json.dumps({"error": f"Inventory not found: {inventory_path}", "results": {}})

    if shadow_libraries is None:
        shadow_libraries = []

    results = {}
    summary = {"total": 0, "arxiv": 0, "oa": 0, "unavailable": 0, "abstract_only": 0}
    for lib in shadow_libraries:
        if lib in _SHADOW_LIBRARY_WHITELIST:
            summary[lib] = 0

    # Extrair source_id + texto da linha da tabela
    source_rows = re.findall(
        r'\|\s*([A-Z]+\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+)\s*\|\s*\d\s*\|',
        inventory_text
    )

    for sid, title_or_path_raw, stype in source_rows:
        # Pular fontes que não são papers
        if "paper" not in stype.lower():
            continue

        row_text = title_or_path_raw
        doi = None
        arxiv_id = None

        # Extrair DOI
        doi_match = DOI_PATTERN.search(row_text)
        if doi_match:
            doi = doi_match.group(1).rstrip(".")

        # Extrair arXiv ID
        arxiv_match = ARXIV_ID_PATTERN.search(row_text)
        if arxiv_match:
            arxiv_id = arxiv_match.group(1)

        if not doi and not arxiv_id:
            continue  # sem DOI nem arXiv ID → não podemos resolver

        summary["total"] += 1
        result = resolve_fulltext(
            doi=doi,
            arxiv_id=arxiv_id,
            source_id=sid.strip(),
            output_dir=output_dir,
            unpaywall_email=unpaywall_email,
            shadow_libraries=shadow_libraries,
            scihub_domain=scihub_domain,
        )
        results[sid.strip()] = result

        # Atualizar sumário
        status = result.get("status", "unavailable")
        summary[status] = summary.get(status, 0) + 1

    return json.dumps({"results": results, "summary": summary}, indent=2)


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

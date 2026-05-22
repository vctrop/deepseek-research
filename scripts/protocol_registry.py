#!/usr/bin/env python3
"""protocol_registry.py — OSF (Open Science Framework) protocol pre-registration.

Called via `code_execution` from Stage 1.6. Pure Python stdlib + `requests`
(available in most Python environments; falls back to urllib if unavailable).

Usage:
    from protocol_registry import register_protocol
    result = register_protocol(osf_token, project_id, protocol_dict)
    # Returns: {"doi_url": "...", "registration_id": "..."} or None on failure
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# Try requests first, fall back to urllib
try:
    import requests  # type: ignore[import-untyped]

    _HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error

    _HAS_REQUESTS = False


def register_protocol(
    token: str,
    project_id: str,
    protocol: dict,
    api_base: str = "https://api.osf.io/v2",
) -> dict | None:
    """Register a research protocol as an OSF registration.

    Args:
        token: OSF personal access token (from https://osf.io/settings/tokens).
        project_id: OSF project GUID (5-char alphanumeric).
        protocol: Dict with keys: title, description, category, questions (list
            of {qid, title, response} dicts matching the OSF registration schema).

    Returns:
        dict with doi_url and registration_id on success, None on failure.

    Graceful degradation:
        - If token is empty or "none": returns None immediately (no API call).
        - If network error: returns None with stderr message.
        - If HTTP error: returns None with status code.
    """
    if not token or token.lower() in ("none", ""):
        return None

    url = f"{api_base}/registrations/"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = {
        "data": {
            "type": "registrations",
            "attributes": {
                "title": protocol.get("title", "Untitled Protocol"),
                "description": protocol.get("description", ""),
                "category": protocol.get("category", "analysis"),
                "registration_supplement": protocol.get("registration_supplement",
                    "osf-preregistration"),
                "registration_responses": _build_responses(
                    protocol.get("questions", [])
                ),
                "project": project_id,
            },
        }
    }

    try:
        if _HAS_REQUESTS:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 201:
                data = resp.json()
                reg_id = data["data"]["id"]
                doi_url = f"https://doi.org/10.17605/OSF.IO/{reg_id}"
                return {"doi_url": doi_url, "registration_id": reg_id}
            else:
                print(
                    f"OSF API error: HTTP {resp.status_code} — {resp.text[:200]}",
                    flush=True,
                )
                return None
        else:
            # urllib fallback
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=30)
            body = json.loads(resp.read().decode("utf-8"))
            reg_id = body["data"]["id"]
            doi_url = f"https://doi.org/10.17605/OSF.IO/{reg_id}"
            return {"doi_url": doi_url, "registration_id": reg_id}

    except Exception as e:
        print(f"OSF registration failed: {e}", flush=True)
        return None


def register_local(
    protocol: dict,
    output_path: str,
) -> dict:
    """Generate a local pre-registration record (no external API).

    Always succeeds. Writes a JSON metadata file and returns a faux-DOI
    based on SHA256 of the protocol content.

    Args:
        protocol: Same dict as register_protocol.
        output_path: Path to write the local registration JSON file.

    Returns:
        dict with local_doi (SHA256-based identifier) and file_path.
    """
    import hashlib

    protocol_bytes = json.dumps(protocol, sort_keys=True, ensure_ascii=False).encode(
        "utf-8"
    )
    sha = hashlib.sha256(protocol_bytes).hexdigest()[:16]

    registration_record = {
        "protocol": protocol,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "sha256": sha,
        "method": "local",
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(registration_record, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")

    return {"local_doi": f"local://sha256:{sha}", "file_path": str(out)}


def _build_responses(questions: list[dict]) -> dict:
    """Convert Q&A list to OSF registration_responses format."""
    responses = {}
    for q in questions:
        qid = q.get("qid", "")
        response = q.get("response", "")
        if qid:
            responses[qid] = {"value": response}
    return responses

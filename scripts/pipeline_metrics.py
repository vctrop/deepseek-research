#!/usr/bin/env python3
"""pipeline_metrics.py — Aggregate pipeline metrics for MANIFEST.txt.

Reads all session files and computes summary statistics for the
Pipeline Metrics section appended to MANIFEST.txt during Close phase.

Usage (via code_execution no SKILL.md Close):
    code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from pipeline_metrics import compute
print(compute("{session_dir}"))
    ''')
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def _classify_deep_read(fpath: Path) -> str:
    """Classify a deep read file as completed/failed/inaccessible/orphan/unclassified.

    Classification rules (SPEC-005 F-7):
    - 0 bytes → orphan
    - Header contains "**Status:** FAILED" → failed
    - Header contains "INACCESSIBLE" or "BLOCKED" → inaccessible
    - Header contains "**Overall Assessment:** COMPREHENSIVE/PARTIAL/MINIMAL" → completed
    - Claims table populated (≥1 claim) without status header → completed
    - None of the above → unclassified
    """
    try:
        st_size = fpath.stat().st_size
    except OSError:
        return "unclassified"

    if st_size == 0:
        return "orphan"

    try:
        text = fpath.read_text(encoding="utf-8")
    except OSError:
        return "unclassified"

    # Check for explicit status markers
    if re.search(r'\*\*Status:\*\*\s*FAILED', text):
        return "failed"
    if re.search(r'\bINACCESSIBLE\b', text) or re.search(r'\bBLOCKED\b', text):
        return "inaccessible"

    # Check for Overall Assessment
    if re.search(r'\*\*Overall Assessment:\*\*\s*(COMPREHENSIVE|PARTIAL|MINIMAL)', text):
        return "completed"

    # Check for populated claims table (≥1 claim row: | C1 | ... | V/P/I/M/E |)
    if re.search(r'\|\s*C\d+\s*\|', text):
        return "completed"

    return "unclassified"


def _count_deep_reads(deep_reads_dir: Path) -> dict:
    """Count deep reads with classification and aggregate coverage stats (F-7)."""
    result = {
        "completed": 0,
        "failed": 0,
        "inaccessible": 0,
        "orphan": 0,
        "unclassified": 0,
        "total_files": 0,
        "coverage_min": None,
        "coverage_max": None,
        "coverage_mean": None,
    }
    coverages = []
    if deep_reads_dir.exists():
        for fpath in sorted(deep_reads_dir.glob("*.md")):
            if fpath.name.startswith("_"):
                continue
            result["total_files"] += 1

            classification = _classify_deep_read(fpath)
            if classification in result:
                result[classification] += 1
            else:
                result["unclassified"] += 1

            # Extract coverage for completed/inaccessible/failed files
            try:
                text = fpath.read_text(encoding="utf-8")
            except OSError:
                continue
            cov_match = re.search(r'\*\*Coverage:\*\*\s*([\d.]+)%', text)
            if cov_match:
                try:
                    coverages.append(float(cov_match.group(1)))
                except ValueError:
                    pass

    if coverages:
        result["coverage_min"] = round(min(coverages), 1)
        result["coverage_max"] = round(max(coverages), 1)
        result["coverage_mean"] = round(sum(coverages) / len(coverages), 1)

    return result


def _count_evidence_grades(deep_reads_dir: Path) -> dict[str, int]:
    """Count V/P/I/M/E grades across all deep reads."""
    grades: dict[str, int] = {"V": 0, "P": 0, "I": 0, "M": 0, "E": 0}
    if not deep_reads_dir.exists():
        return grades
    for fpath in sorted(deep_reads_dir.glob("*.md")):
        if fpath.name.startswith("_"):
            continue
        try:
            text = fpath.read_text(encoding="utf-8")
        except OSError:
            continue
        for grade_match in re.finditer(r'\|\s*C\d+\s*\|\s*[^|]+\s*\|\s*(V|P|I|M|E)\s*\|', text):
            g = grade_match.group(1).strip()
            if g in grades:
                grades[g] += 1
    return grades


def _count_findings(synthesis_text: str) -> dict[str, int]:
    """Count STRONG/MODERATE/WEAK findings in synthesis."""
    counts = {"STRONG": 0, "MODERATE": 0, "WEAK": 0}
    for match in re.finditer(r'\((STRONG|MODERATE|WEAK)\)', synthesis_text):
        level = match.group(1)
        if level in counts:
            counts[level] += 1
    return counts


def _extract_sources_from_inventory(inventory_path: Path) -> dict:
    """Extract source counts from inventory."""
    result = {"total": 0, "bibliography": 0, "codebase": 0, "with_url": 0}
    if not inventory_path.exists():
        return result
    try:
        text = inventory_path.read_text(encoding="utf-8")
    except OSError:
        return result

    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("| S") or stripped.startswith("| CODE-")):
            continue
        parts = [p.strip() for p in stripped.split("|")]
        if len(parts) < 4:
            continue
        result["total"] += 1
        stype = parts[3] if len(parts) > 3 else ""
        if stype.lower() == "paper":
            result["bibliography"] += 1
        elif stype.lower() in ("code", "repo", "oss"):
            result["codebase"] += 1
        location = parts[2] if len(parts) > 2 else ""
        if re.search(r'https?://', location):
            result["with_url"] += 1

    return result


def compute(session_dir: str) -> str:
    """Compute pipeline metrics for a session.

    Args:
        session_dir: Path to the session directory.

    Returns:
        Markdown-formatted string with Pipeline Metrics section.
    """
    session = Path(session_dir)
    lines: list[str] = []

    # Deep reads
    dr = _count_deep_reads(session / "deep-reads")
    grades = _count_evidence_grades(session / "deep-reads")
    sources_info = _extract_sources_from_inventory(session / "02-source-inventory.md")

    # Synthesis findings
    findings: dict[str, int] = {"STRONG": 0, "MODERATE": 0, "WEAK": 0}
    synth_path = session / "04-synthesis.md"
    if synth_path.exists():
        try:
            findings = _count_findings(synth_path.read_text(encoding="utf-8"))
        except OSError:
            pass

    # Build metrics block
    lines.append("## Pipeline Metrics")
    lines.append("")
    lines.append(f"- **Sources discovered:** {sources_info['total']} "
                 f"(bibliography: {sources_info['bibliography']}, "
                 f"codebase: {sources_info['codebase']})")
    lines.append(f"- **Sources with URL:** {sources_info['with_url']}")

    # Verification
    verif_path = session / "03-source-verification.md"
    if verif_path.exists():
        try:
            verif_text = verif_path.read_text(encoding="utf-8")
            accessible = len(re.findall(r'\bACCESSIBLE\b', verif_text))
            unverifiable = len(re.findall(r'\bUNVERIFIABLE\b', verif_text))
            hallucinated = len(re.findall(r'\bHALLUCINATED\b', verif_text))
            excluded = len(re.findall(r'\bEXCLUDED\b', verif_text))
            lines.append(f"- **Verified:** {accessible} accessible, "
                         f"{unverifiable} unverifiable, "
                         f"{hallucinated} hallucinated, "
                         f"{excluded} excluded")
        except OSError:
            pass

    # Deep read classification (F-7)
    dr_status_parts = [f"{dr['completed']} completed"]
    if dr['failed'] > 0:
        dr_status_parts.append(f"{dr['failed']} failed")
    if dr['inaccessible'] > 0:
        dr_status_parts.append(f"{dr['inaccessible']} inaccessible")
    if dr['orphan'] > 0:
        dr_status_parts.append(f"{dr['orphan']} orphan")
    if dr['unclassified'] > 0:
        dr_status_parts.append(f"{dr['unclassified']} unclassified")
    lines.append(f"- **Deep reads:** {', '.join(dr_status_parts)} "
                 f"({dr['total_files']} total)")
    if dr["coverage_mean"] is not None:
        lines.append(f"- **Coverage:** min {dr['coverage_min']}%, "
                     f"max {dr['coverage_max']}%, "
                     f"mean {dr['coverage_mean']}%")
    else:
        lines.append("- **Coverage:** not reported")

    total_claims = sum(grades.values())
    if total_claims > 0:
        lines.append(f"- **Evidence grades:** "
                     f"V={grades['V']}, P={grades['P']}, I={grades['I']}, "
                     f"M={grades['M']}, E={grades['E']} "
                     f"({total_claims} total)")

    total_findings = sum(findings.values())
    if total_findings > 0:
        lines.append(f"- **Findings:** {findings['STRONG']} STRONG, "
                     f"{findings['MODERATE']} MODERATE, "
                     f"{findings['WEAK']} WEAK")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        print(compute(sys.argv[1]))
    else:
        print("Usage: python pipeline_metrics.py <session_dir>")

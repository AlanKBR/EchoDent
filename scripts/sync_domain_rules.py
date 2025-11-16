"""Sync Domain Rules Script
Reads canonical sources and prints aggregated domain rules blocks.
(Initial stub — extend as needed to write back into agent files.)
"""
from pathlib import Path
import sys

# Canonical source file paths (adjust if structure changes)
SOURCES = {
    "copilot_instructions": Path(".github/copilot-instructions.md"),
    "architecture_blueprint": Path("Project_Architecture_Blueprint.md"),
    "agents_v3_postgres": Path("AGENTS_V3_POSTGRES.MD"),
    "agents_backup": Path("agents.md.BAK"),
}

EXCERPTS = {
    "db-schema": [
        ("agents_v3_postgres", None),  # full file
        ("copilot_instructions", "## Database & Tenancy"),
        ("architecture_blueprint", "## 6. Data Architecture"),
        ("architecture_blueprint", "## 12. Deployment Architecture"),
    ],
    "finance-rules": [
        ("agents_backup", "## 4. Workflow Financeiro"),
        ("copilot_instructions", "## Financial Workflow"),
        ("architecture_blueprint", "## 6. Data Architecture"),
    ],
    "ui-robustness": [
        ("agents_backup", "## 8. Robustez de UI"),
        ("agents_backup", "## 9. Regras Técnicas"),
        ("agents_backup", "## 10. Regras de Frontend"),
        ("copilot_instructions", "## HTMX UI Patterns"),
        ("copilot_instructions", "## Printing & Media"),
    ],
}


def read_excerpt(path: Path, header: str | None) -> str:
    text = path.read_text(encoding="utf-8")
    if not header:
        return text.strip()
    # naive extraction: header line to next header of same level
    lines = text.splitlines()
    out = []
    capture = False
    header_level = None
    for line in lines:
        if header and line.startswith(header):
            capture = True
            header_level = len(line) - len(line.lstrip('#'))
        elif capture and line.startswith('#') and header_level is not None:
            level = len(line) - len(line.lstrip('#'))
            if level <= header_level:
                break
        if capture:
            out.append(line)
    return '\n'.join(out).strip()


def aggregate(domain: str) -> str:
    if domain not in EXCERPTS:
        return f"No excerpts configured for domain '{domain}'"
    parts = []
    for key, header in EXCERPTS[domain]:
        path = SOURCES[key]
        if not path.exists():
            parts.append(f"[MISSING SOURCE: {path}]")
            continue
        parts.append(read_excerpt(path, header))
    return "\n\n".join(parts)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/sync_domain_rules.py <domain-key>")
        print(f"Available: {', '.join(EXCERPTS.keys())}")
        sys.exit(1)
    domain = sys.argv[1]
    print(aggregate(domain))


if __name__ == "__main__":
    main()

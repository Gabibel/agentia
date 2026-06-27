"""Mémoire produit : append préférences + sources fiables dans MEMORY.md."""
import datetime
import re
from pathlib import Path

MEMORY_FILE = Path("MEMORY.md")
MAX_LINES = 200


def load() -> str:
    return MEMORY_FILE.read_text(encoding="utf-8") if MEMORY_FILE.exists() else ""


def append_run(idea: str, sources: list[str], model: str) -> None:
    date = datetime.date.today().isoformat()
    slug = re.sub(r"[^a-z0-9]+", "-", idea.lower())[:40]

    entry = f"\n## Run {date} — {slug}\n- Modèle : {model}\n"
    if sources:
        entry += "- Sources fiables rencontrées :\n"
        for s in sources[:10]:
            entry += f"  - {s}\n"

    current = load()
    updated = (current + entry).strip() + "\n"

    # Élagage si trop long
    lines = updated.splitlines()
    if len(lines) > MAX_LINES:
        # Garde le préambule (avant le 1er ##) + les N dernières lignes
        header_end = next((i for i, l in enumerate(lines) if l.startswith("## Run")), 0)
        header = lines[:header_end]
        tail = lines[-(MAX_LINES - header_end):]
        updated = "\n".join(header + tail) + "\n"

    MEMORY_FILE.write_text(updated, encoding="utf-8")


def get_trusted_sources() -> list[str]:
    content = load()
    return re.findall(r"https?://\S+", content)


def inject_context() -> str:
    content = load().strip()
    if not content:
        return ""
    return f"## Mémoire des runs précédents\n\n{content}\n"

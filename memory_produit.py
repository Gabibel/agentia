"""Mémoire produit : sources fiables + historique compact (MEMORY.md)."""
import datetime
import re
from pathlib import Path

MEMORY_FILE = Path("MEMORY.md")
MAX_RUNS    = 5   # runs gardés dans l'historique
MAX_SOURCES = 60  # URLs uniques max dans le pool


# ── Parsing ───────────────────────────────────────────────────────────────────

def _parse(content: str) -> tuple[list[str], list[dict]]:
    """Extrait (sources_pool, runs) depuis le contenu brut de MEMORY.md."""
    sources_pool: list[str] = []
    runs: list[dict] = []
    current: dict | None = None
    section = None

    for line in content.splitlines():
        # Sections de haut niveau
        if line.startswith("## Sources fiables"):
            section = "sources"
            continue
        if line.startswith("## Historique"):
            section = "history"
            continue

        # Blocs de runs (ancien format)
        m = re.match(r"^## Run (\S+) — (.+)$", line)
        if m:
            if current:
                runs.append(current)
            current = {"date": m.group(1), "slug": m.group(2),
                       "model": "?", "sources": []}
            section = "run_block"
            continue

        if section == "sources":
            u = line.strip().lstrip("- ").strip()
            if u.startswith("http"):
                sources_pool.append(u)

        elif section == "run_block" and current is not None:
            if line.startswith("- Modèle :"):
                current["model"] = line.replace("- Modèle :", "").strip()
            else:
                u = line.strip().lstrip("- ").strip()
                if u.startswith("http"):
                    current["sources"].append(u)

        elif section == "history":
            # format: "- DATE MODEL — SLUG"
            hm = re.match(r"^- (\S+)\s+(\S+)\s+—\s+(.+)$", line)
            if hm:
                runs.append({"date": hm.group(1), "model": hm.group(2),
                             "slug": hm.group(3), "sources": []})

    if current:
        runs.append(current)

    return sources_pool, runs


# ── Sérialisation ─────────────────────────────────────────────────────────────

def _serialize(sources_pool: list[str], runs: list[dict]) -> str:
    lines = ["## Sources fiables (pool consolidé)\n"]
    for url in sources_pool[:MAX_SOURCES]:
        lines.append(f"- {url}")

    lines.append("\n## Historique (5 derniers runs)\n")
    for r in runs[-MAX_RUNS:]:
        lines.append(f"- {r['date']}  {r['model']}  —  {r['slug']}")

    return "\n".join(lines) + "\n"


# ── API publique ──────────────────────────────────────────────────────────────

def load() -> str:
    return MEMORY_FILE.read_text(encoding="utf-8") if MEMORY_FILE.exists() else ""


def append_run(idea: str, sources: list[str], model: str) -> None:
    date = datetime.date.today().isoformat()
    slug = re.sub(r"[^a-z0-9]+", "-", idea.lower())[:40]

    pool, runs = _parse(load())

    # Migrer les sources d'anciens blocs run vers le pool (format legacy)
    seen = set(pool)
    for r in runs:
        for url in r.get("sources", []):
            if url not in seen:
                pool.append(url)
                seen.add(url)

    # Ajouter les nouvelles sources au pool (dedup, ordre d'arrivée)
    for url in sources:
        if url not in seen:
            pool.append(url)
            seen.add(url)

    # Ajouter le run
    runs.append({"date": date, "slug": slug, "model": model, "sources": []})

    # Limiter + réécrire
    pool = pool[:MAX_SOURCES]
    runs = runs[-MAX_RUNS:]
    MEMORY_FILE.write_text(_serialize(pool, runs), encoding="utf-8")


def get_trusted_sources() -> list[str]:
    pool, _ = _parse(load())
    return pool


def inject_context() -> str:
    content = load().strip()
    if not content:
        return ""
    return f"## Mémoire des runs précédents\n\n{content}\n"

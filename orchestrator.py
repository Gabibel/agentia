"""Orchestrateur asyncio : idée → dossier.md + dossier.pdf + prd.md."""
import asyncio
import os
import re
from pathlib import Path

from openai import AsyncOpenAI
from chercheur import run_chercheur
from redacteur import run_redacteur
from verificateur import run_verificateur
import memory_produit as mem

OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",    "qwen3:14b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OUT_DIR = Path("out")
MAX_VERIF_RETRIES = 1  # une boucle de correction max au MVP

_llm = AsyncOpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower().strip())[:50].strip("-")


async def _call(messages: list, temperature: float = 0.3) -> str:
    resp = await _llm.chat.completions.create(
        model=OLLAMA_MODEL,
        messages=messages,
        temperature=temperature,
        extra_body={"think": False},
    )
    return resp.choices[0].message.content.strip()


# ── Génération de requêtes adaptées à chaque focus ───────────────────────────

FOCUS_QUERY_PROMPTS = {
    "skills_connecteurs": (
        "Génère 4 requêtes de recherche web (courtes, en anglais ou français) pour trouver :\n"
        "- Les skills Claude Code et connecteurs MCP utiles pour construire CE projet\n"
        "- Les API, services tiers et outils d'IA les plus adaptés à CE type d'application\n"
        "Exemples : 'MCP server <domaine>', '<technologie> API integration', "
        "'best tools <domaine> app 2024'.\n"
        "Ne mentionne PAS 'Claude Code' dans les requêtes sauf si c'est central au projet.\n"
        "Retourne UNIQUEMENT les 4 requêtes, une par ligne, sans numérotation ni explication."
    ),
    "concurrents": (
        "Génère 4 requêtes de recherche web pour trouver les concurrents directs et indirects de ce projet.\n"
        "Exemples : 'best <domaine> apps 2024', 'top <domaine> startups', '<domaine> market leaders'.\n"
        "Retourne UNIQUEMENT les 4 requêtes, une par ligne, sans numérotation ni explication."
    ),
    "marche_techno": (
        "Génère 4 requêtes de recherche web pour analyser le marché et la faisabilité technique de ce projet.\n"
        "Couvre : taille du marché (TAM/SAM), tendances 2024-2025, maturité des technologies clés.\n"
        "Exemples : '<domaine> market size 2025', '<secteur> industry growth forecast', "
        "'<technologie> maturity open source'.\n"
        "Retourne UNIQUEMENT les 4 requêtes, une par ligne, sans numérotation ni explication."
    ),
    "juridique": (
        "Génère 4 requêtes de recherche web pour trouver le cadre juridique applicable à ce projet.\n"
        "Couvre : RGPD/données personnelles, droits sectoriels, propriété intellectuelle.\n"
        "Exemples : 'RGPD <domaine> obligations', '<secteur> legal requirements Europe'.\n"
        "Retourne UNIQUEMENT les 4 requêtes, une par ligne, sans numérotation ni explication."
    ),
}


async def _generate_queries(idea: str, focus: str) -> list[str]:
    prompt = FOCUS_QUERY_PROMPTS.get(focus, f"Génère 4 requêtes de recherche pour '{focus}'.")
    raw = await _call([
        {"role": "system", "content": prompt},
        {"role": "user",   "content": f"Projet : {idea}"},
    ], temperature=0.5)
    queries = [q.strip().strip("-•·").strip() for q in raw.splitlines() if q.strip()]
    return queries[:4]


# ── Pipeline principal ────────────────────────────────────────────────────────

async def run_pipeline(idea: str, log=print) -> dict:
    """Retourne dict avec md, pdf, prd (Path), verdict (str), out_path (Path)."""
    log(f"\n{'='*60}\n  Idée : {idea}\n{'='*60}\n")

    memory_ctx = mem.inject_context()
    if memory_ctx:
        log("📚 [Mémoire] Contexte des runs précédents injecté\n")

    # 1. Reformulation
    log("🧭 [Orchestrateur] Reformulation…")
    overview = await _call([
        {"role": "system", "content": (
            "Tu es un chef de projet. À partir d'une idée, produis en 4-6 phrases :\n"
            "1. Reformulation claire du projet\n"
            "2. Marché cible et valeur ajoutée principale\n"
            "3. Les 3 axes d'exploration (skills/connecteurs, concurrents, juridique)\n"
            + (f"\nContexte mémorisé :\n{memory_ctx}" if memory_ctx else "")
            + "\nSois factuel et concis. Réponds en français."
        )},
        {"role": "user", "content": f"Idée : {idea}"},
    ])
    log(f"  → {overview[:120]}…\n")

    # 2. Recherches (séquentielles — 1 GPU)
    sections: dict[str, str] = {}
    for focus, label, icon in [
        ("skills_connecteurs", "Skills & connecteurs",    "🔧"),
        ("concurrents",        "Analyse concurrentielle", "🥊"),
        ("marche_techno",      "Marché & Faisabilité",    "📊"),
        ("juridique",          "Cadre juridique",         "⚖️"),
    ]:
        log(f"{icon} [Chercheur] {label}…")
        queries = await _generate_queries(idea, focus)
        log(f"  → Requêtes : {queries}")
        sections[focus] = await run_chercheur(
            _llm, OLLAMA_MODEL, idea, focus=focus, queries=queries, log=log,
        )
        log("")

    # 3. Rédaction
    out_path = OUT_DIR / _slugify(idea)
    out_path.mkdir(parents=True, exist_ok=True)

    log("✍️  [Rédacteur] Assemblage dossier + PDF + PRD…")
    md_path, pdf_path, docx_path, prd_path = await run_redacteur(
        _llm, OLLAMA_MODEL, idea,
        overview=overview,
        skills=sections["skills_connecteurs"],
        concurrents=sections["concurrents"],
        marche_techno=sections["marche_techno"],
        juridique=sections["juridique"],
        out_path=out_path,
        log=log,
    )
    log("")

    # 4. Vérification (+ 1 tentative de correction)
    log("✅ [Vérificateur] Contrôle qualité…")
    for attempt in range(MAX_VERIF_RETRIES + 1):
        verdict, corrections, rapport = await run_verificateur(_llm, OLLAMA_MODEL, md_path)
        log(f"  → VERDICT : {verdict}")
        if verdict == "OK" or attempt == MAX_VERIF_RETRIES or not corrections:
            break
        log(f"  → Corrections : {corrections}")
        log("  → Nouvelle passe rédacteur…")
        correction_hint = (
            "\n\n---\nNote vérificateur (à corriger) :\n"
            + "\n".join(f"- {c}" for c in corrections)
        )
        md_path, pdf_path, docx_path, prd_path = await run_redacteur(
            _llm, OLLAMA_MODEL, idea,
            overview=overview + correction_hint,
            skills=sections["skills_connecteurs"],
            concurrents=sections["concurrents"],
            marche_techno=sections["marche_techno"],
            juridique=sections["juridique"],
            out_path=out_path,
            log=log,
        )

    # 5. Mémoire produit
    raw_urls = re.findall(r"https?://[^\s\)\]\>\"']+", "\n".join(sections.values()))
    all_sources = [u.rstrip(".,;)") for u in raw_urls]
    mem.append_run(idea, list(dict.fromkeys(all_sources)), OLLAMA_MODEL)
    log("💾 [Mémoire] Sources fiables sauvegardées dans MEMORY.md\n")

    log(f"{'='*60}")
    log(f"  ✅ {md_path}")
    log(f"  ✅ {pdf_path}")
    log(f"  ✅ {prd_path}")
    log(f"  VERDICT : {verdict}")
    log(f"{'='*60}\n")

    return {"md": md_path, "pdf": pdf_path, "docx": docx_path,
            "prd": prd_path, "verdict": verdict, "out_path": out_path}

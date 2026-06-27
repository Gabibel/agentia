"""Agent chercheur : recherche DuckDuckGo + extraction trafilatura + synthèse LLM."""
import asyncio
import httpx
import trafilatura
from ddgs import DDGS
from openai import AsyncOpenAI

MAX_URLS = 6
MAX_CONTENT_CHARS = 3000
FETCH_TIMEOUT = 10

FOCUS_LABELS = {
    "skills_connecteurs": "skills Claude Code, connecteurs MCP et outils d'IA pertinents pour ce projet",
    "concurrents":        "concurrents directs et indirects, leurs forces/faiblesses, différenciation possible",
    "marche_techno":      "taille de marché, tendances sectorielles 2024-2025, faisabilité technique et maturité des technologies",
    "juridique":          "cadre juridique applicable : RGPD, droits sectoriels, propriété intellectuelle",
}

SYSTEM_PROMPT = (
    "Tu es un chercheur spécialisé. À partir des sources fournies, produis une synthèse compacte "
    "sur {label} pour le projet décrit.\n\n"
    "Règles :\n"
    "- Bullet points concis, en français\n"
    "- Chaque affirmation importante doit citer sa source : [Titre](URL)\n"
    "- Recouper les faits sensibles (chiffres, statut légal) avec ≥ 2 sources si possible\n"
    "- Ne jamais copier de longs extraits — paraphrase uniquement\n"
    "- Terminer par une section « Sources » (titre + URL)\n"
    "- Si une source semble inaccessible ou hors-sujet, l'ignorer"
)


def _search(queries: list[str]) -> list[dict]:
    seen, results = set(), []
    with DDGS() as ddgs:
        for q in queries:
            try:
                for r in ddgs.text(q, max_results=4):
                    url = r.get("href", "")
                    if url and url not in seen:
                        seen.add(url)
                        results.append({
                            "url": url,
                            "title": r.get("title", url),
                            "snippet": r.get("body", ""),
                        })
            except Exception as e:
                print(f"  ⚠ Recherche échouée ({q!r}): {e}")
    return results[:MAX_URLS]


def _fetch(url: str) -> str:
    try:
        r = httpx.get(url, timeout=FETCH_TIMEOUT, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
        text = trafilatura.extract(r.text, include_links=False, no_fallback=False)
        return (text or "")[:MAX_CONTENT_CHARS]
    except Exception:
        return ""


async def run_chercheur(
    llm: AsyncOpenAI,
    model: str,
    idea: str,
    focus: str,
    queries: list[str],
    log=print,
) -> str:
    log(f"  → {len(queries)} requêtes DuckDuckGo…")
    loop = asyncio.get_event_loop()

    results = await loop.run_in_executor(None, _search, queries)
    log(f"  → {len(results)} URLs trouvées")

    pages = []
    for r in results:
        content = await loop.run_in_executor(None, _fetch, r["url"])
        if content:
            pages.append({"url": r["url"], "title": r["title"], "content": content})
    log(f"  → {len(pages)} pages extraites")

    if not pages:
        return "_Aucune source récupérée. Vérifie ta connexion internet._"

    context = "\n\n---\n\n".join(
        f"**{p['title']}**\nSource : {p['url']}\n\n{p['content']}"
        for p in pages
    )
    label = FOCUS_LABELS.get(focus, focus)

    resp = await llm.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(label=label)},
            {"role": "user",   "content": (
                f"Projet : {idea}\n\n## Sources\n\n{context}\n\n"
                "RÈGLE ABSOLUE : ne cite QUE des URLs présentes dans les sources ci-dessus. "
                "N'invente JAMAIS d'URL (pas de example.com, placeholder, lien fictif). "
                "Si tu n'as pas de source pour une affirmation, écris : "
                "*(source non trouvée — à vérifier manuellement)*"
            )},
        ],
        temperature=0.3,
        extra_body={"think": False},
    )
    return resp.choices[0].message.content.strip()

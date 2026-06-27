"""Agent vérificateur : contrôle qualité hybride (Python + LLM court)."""
import re
from pathlib import Path
from openai import AsyncOpenAI

# ── Checks déterministes (Python pur) ────────────────────────────────────────

def _c1_citations(text: str) -> tuple[bool, str]:
    """Affirmations sensibles citées — pas de URLs fictives."""
    fake = re.findall(r'https?://(?:example\.com|placeholder\.)[^\s)\]]*', text, re.IGNORECASE)
    real = re.findall(r'https?://(?!example\.com)(?!placeholder\.)[^\s)\]>]+', text)
    if fake:
        return False, f"{len(fake)} URL(s) fictive(s) (ex: {fake[0][:60]})"
    if not real:
        return False, "Aucune citation URL trouvée dans le dossier"
    return True, f"{len(real)} citations présentes"


def _c2_sections(text: str) -> tuple[bool, str]:
    """Sections attendues présentes et non vides."""
    required = {
        "Vue d'ensemble":     r"vue d.ensemble",
        "Skills/Connecteurs": r"skills?\s*[&|/]?\s*connecteurs?|## \d+\.\s*skills?",
        "Concurrents":        r"concurrent|concurrentiel",
        "Marché & Faisabilité": r"march[eé]|faisabilit[eé]|market size|tendances",
        "Juridique":          r"juridique|rgpd|légal",
        "Stack":              r"stack|recommandations? de stack",
    }
    missing = [name for name, pat in required.items()
               if not re.search(pat, text, re.IGNORECASE)]
    if missing:
        return False, f"Sections absentes : {', '.join(missing)}"
    return True, "6 sections présentes"


def _c5_legal_warning(text: str) -> tuple[bool, str]:
    """Avertissement non-conseil juridique présent."""
    if re.search(r"non.conseil juridique", text, re.IGNORECASE):
        return True, "Avertissement présent"
    return False, "Mention 'non-conseil juridique' absente de la section juridique"


# ── Check LLM ciblé (subjectif) ───────────────────────────────────────────────

_COHERENCE_PROMPT = """\
Réponds en UNE SEULE LIGNE au format exact :
COHERENCE: OK
ou
COHERENCE: FAIL — <raison en moins de 15 mots>

Question : le dossier ci-dessous contient-il des contradictions internes évidentes \
(ex. une section recommande X, une autre déconseille X) ? \
Ignore la qualité rédactionnelle — évalue seulement les contradictions factuelles."""


async def _c4_coherence(llm: AsyncOpenAI, model: str, text: str) -> tuple[bool, str]:
    # On donne seulement un résumé court pour éviter de saturer le contexte
    excerpt = text[:3000]
    resp = await llm.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _COHERENCE_PROMPT},
            {"role": "user",   "content": excerpt},
        ],
        temperature=0,
        max_tokens=60,
        extra_body={"think": False},
    )
    lines = [l for l in resp.choices[0].message.content.strip().splitlines() if l.strip()]
    raw = lines[0] if lines else "COHERENCE: OK"
    ok = bool(re.search(r"COHERENCE\s*:\s*OK", raw, re.IGNORECASE))
    detail = re.sub(r"COHERENCE\s*:\s*(OK|FAIL)\s*[—-]?\s*", "", raw, flags=re.IGNORECASE).strip()
    return ok, (detail or "ok")


# ── Entrée publique ───────────────────────────────────────────────────────────

async def run_verificateur(
    llm: AsyncOpenAI,
    model: str,
    dossier_path: Path,
) -> tuple[str, list[str], str]:
    """Retourne (verdict, corrections, rapport_texte)."""
    text = dossier_path.read_text(encoding="utf-8")

    results: dict[str, tuple[bool, str]] = {
        "C1 citations":       _c1_citations(text),
        "C2 sections":        _c2_sections(text),
        "C5 avert. juridique": _c5_legal_warning(text),
        "C4 cohérence":       await _c4_coherence(llm, model, text),
    }

    corrections = [
        f"[{name}] {detail}"
        for name, (ok, detail) in results.items()
        if not ok
    ]

    verdict = "OK" if not corrections else "À CORRIGER"

    rapport = "\n".join(
        f"  {'✅' if ok else '❌'} {name} — {detail}"
        for name, (ok, detail) in results.items()
    )

    return verdict, corrections, rapport

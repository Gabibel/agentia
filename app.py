"""UI locale Streamlit : idée → dossier + PDF + PRD."""
import asyncio
import sys
from pathlib import Path

import streamlit as st

# ── Config page ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Idée → Dossier",
    page_icon="📄",
    layout="centered",
)

st.title("📄 Idée → Dossier")
st.caption("Système multi-agents local — Ollama · 100 % privé · 0 € récurrent")

# ── Sidebar : config ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Configuration")
    model = st.text_input("Modèle Ollama", value="qwen3:14b")
    base_url = st.text_input("URL Ollama", value="http://localhost:11434/v1")
    st.divider()
    st.markdown("**Dossiers générés**")
    out_dir = Path("out")
    if out_dir.exists():
        slugs = sorted([d.name for d in out_dir.iterdir() if d.is_dir()])
        if slugs:
            for s in slugs[-5:]:  # 5 derniers
                st.markdown(f"- `{s}`")
        else:
            st.caption("Aucun dossier encore.")
    else:
        st.caption("Aucun dossier encore.")

# ── Formulaire principal ──────────────────────────────────────────────────────
idea = st.text_area(
    "Votre idée",
    placeholder="ex : une app de covoiturage pour festivals de musique",
    height=100,
)

col_btn, col_info = st.columns([1, 3])
with col_btn:
    run_btn = st.button("🚀 Générer", disabled=not idea.strip(), type="primary")
with col_info:
    st.caption("Durée estimée : ~8 min (qwen3:14b)")

# ── Lancement du pipeline ─────────────────────────────────────────────────────
if run_btn and idea.strip():
    import os
    os.environ["OLLAMA_MODEL"] = model
    os.environ["OLLAMA_BASE_URL"] = base_url

    # Import ici pour que les env vars soient lus au bon moment
    from orchestrator import run_pipeline

    log_placeholder = st.empty()
    log_lines: list[str] = []

    def log(msg: str) -> None:
        log_lines.append(msg)
        log_placeholder.code("\n".join(log_lines[-30:]), language=None)

    results = None
    error = None

    with st.status("⏳ Génération en cours…", expanded=True) as status:
        try:
            results = asyncio.run(run_pipeline(idea.strip(), log=log))
            status.update(label="✅ Dossier généré !", state="complete", expanded=False)
        except Exception as e:
            error = str(e)
            status.update(label=f"❌ Erreur : {e}", state="error")

    if error:
        st.error(f"Erreur pipeline : {error}")

    elif results:
        verdict = results["verdict"]
        if verdict == "OK":
            st.success(f"VERDICT : {verdict} — dossier validé")
        else:
            st.warning(f"VERDICT : {verdict} — certains points à vérifier")

        # Boutons de téléchargement
        st.subheader("📥 Téléchargements")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button(
                "📄 dossier.md",
                data=results["md"].read_bytes(),
                file_name="dossier.md",
                mime="text/markdown",
            )
        with c2:
            st.download_button(
                "📕 dossier.pdf",
                data=results["pdf"].read_bytes(),
                file_name="dossier.pdf",
                mime="application/pdf",
            )
        with c3:
            st.download_button(
                "📋 prd.md",
                data=results["prd"].read_bytes(),
                file_name="prd.md",
                mime="text/markdown",
            )

        # Aperçu du dossier
        st.divider()
        with st.expander("📖 Aperçu du dossier", expanded=True):
            st.markdown(results["md"].read_text(encoding="utf-8"))

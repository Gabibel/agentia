"""UI locale Streamlit : idée → dossier + PDF + DOCX + PRD."""
import asyncio
from pathlib import Path

import streamlit as st

# ── Config page ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Idée → Dossier",
    page_icon="📄",
    layout="wide",
)

st.title("📄 Idée → Dossier")
st.caption("Système multi-agents local — Ollama · 100 % privé · 0 € récurrent")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")
    model   = st.text_input("Modèle Ollama",  value="qwen3:14b")
    base_url = st.text_input("URL Ollama",    value="http://localhost:11434/v1")

    st.divider()

    # Cache stats + purge
    st.subheader("🗄️ Cache recherches")
    try:
        import search_cache as _cache
        stats = _cache.stats()
        st.caption(f"{stats['valid']} valides · {stats['expired']} expirées")
        if st.button("🗑️ Vider le cache", use_container_width=True):
            import sqlite3
            conn = sqlite3.connect(_cache.DB_PATH)
            conn.execute("DELETE FROM search_cache")
            conn.commit()
            conn.close()
            st.success("Cache vidé.")
    except Exception:
        st.caption("cache.db non initialisé")

    st.divider()

    # Historique des dossiers générés
    st.subheader("📂 Dossiers générés")
    out_dir = Path("out")
    history_selection = None
    if out_dir.exists():
        slugs = sorted([d for d in out_dir.iterdir() if d.is_dir()],
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if slugs:
            options = ["(nouveau run)"] + [p.name for p in slugs]
            choice = st.selectbox("Charger un dossier", options, label_visibility="collapsed")
            if choice != "(nouveau run)":
                history_selection = out_dir / choice
        else:
            st.caption("Aucun dossier encore.")
    else:
        st.caption("Aucun dossier encore.")

# ── Affichage d'un dossier existant (historique) ──────────────────────────────
if history_selection:
    md_file   = history_selection / "dossier.md"
    pdf_file  = history_selection / "dossier.pdf"
    docx_file = history_selection / "dossier.docx"
    prd_file  = history_selection / "prd.md"

    st.subheader(f"📖 {history_selection.name}")
    c1, c2, c3, c4 = st.columns(4)
    for col, fpath, label, mime in [
        (c1, md_file,   "📄 dossier.md",   "text/markdown"),
        (c2, pdf_file,  "📕 dossier.pdf",  "application/pdf"),
        (c3, docx_file, "📘 dossier.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        (c4, prd_file,  "📋 prd.md",       "text/markdown"),
    ]:
        if fpath.exists():
            col.download_button(label, data=fpath.read_bytes(),
                                file_name=fpath.name, mime=mime,
                                use_container_width=True)

    if md_file.exists() and prd_file.exists():
        tab_dos, tab_prd = st.tabs(["Dossier", "PRD"])
        with tab_dos:
            st.markdown(md_file.read_text(encoding="utf-8"))
        with tab_prd:
            st.markdown(prd_file.read_text(encoding="utf-8"))
    elif md_file.exists():
        st.markdown(md_file.read_text(encoding="utf-8"))

    st.stop()

# ── Formulaire principal ──────────────────────────────────────────────────────
idea = st.text_area(
    "Votre idée",
    placeholder="ex : une app de covoiturage pour festivals de musique",
    height=100,
)

col_btn, col_info = st.columns([1, 4])
with col_btn:
    run_btn = st.button("🚀 Générer", disabled=not idea.strip(), type="primary")
with col_info:
    st.caption("Durée estimée : ~10 min (qwen3:14b) — ~2 min si cache chaud")

# ── Lancement du pipeline ─────────────────────────────────────────────────────
if run_btn and idea.strip():
    import os
    os.environ["OLLAMA_MODEL"]    = model
    os.environ["OLLAMA_BASE_URL"] = base_url

    from orchestrator import run_pipeline

    log_placeholder = st.empty()
    log_lines: list[str] = []

    def log(msg: str) -> None:
        log_lines.append(msg)
        log_placeholder.code("\n".join(log_lines[-35:]), language=None)

    results = None
    error   = None

    with st.status("⏳ Génération en cours…", expanded=True) as status:
        try:
            results = asyncio.run(run_pipeline(idea.strip(), log=log))
            status.update(label="✅ Dossier généré !", state="complete", expanded=False)
        except Exception as e:
            error = str(e)
            status.update(label=f"❌ Erreur : {e}", state="error")

    log_placeholder.empty()

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
        c1, c2, c3, c4 = st.columns(4)
        for col, key, label, mime in [
            (c1, "md",   "📄 dossier.md",   "text/markdown"),
            (c2, "pdf",  "📕 dossier.pdf",  "application/pdf"),
            (c3, "docx", "📘 dossier.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            (c4, "prd",  "📋 prd.md",       "text/markdown"),
        ]:
            col.download_button(label, data=results[key].read_bytes(),
                                file_name=results[key].name, mime=mime,
                                use_container_width=True)

        # Aperçu Dossier / PRD en tabs
        st.divider()
        tab_dos, tab_prd = st.tabs(["📖 Dossier", "📋 PRD"])
        with tab_dos:
            st.markdown(results["md"].read_text(encoding="utf-8"))
        with tab_prd:
            st.markdown(results["prd"].read_text(encoding="utf-8"))

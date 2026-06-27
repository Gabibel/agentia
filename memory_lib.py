#!/usr/bin/env python3
"""memory_lib.py — utilitaires pour la mémoire auto-évolutive (hooks Claude Code).

100 % stdlib (urllib), aucune dépendance. Pensé pour Windows/macOS/Linux.
La distillation utilise le LLM LOCAL via l'endpoint OpenAI-compatible d'Ollama.
Tout est défensif : en cas d'erreur, on n'interrompt JAMAIS la session (exit 0).
"""
import os, sys, json, datetime, pathlib, urllib.request

OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://localhost:11434/v1/chat/completions")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")   # adapte à ta VRAM
MAX_LINES    = int(os.environ.get("MEMORY_MAX_LINES", "200"))

def project_dir() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

def memory_path() -> pathlib.Path:
    return pathlib.Path(project_dir()) / "MEMORY.md"

def read_event() -> dict:
    """Claude Code envoie un JSON d'événement sur stdin."""
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}

def read_transcript(path: str, max_chars: int = 12000) -> str:
    """Lit le transcript JSONL et renvoie les derniers échanges (texte concaténé)."""
    try:
        out = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    msg = json.loads(line)
                except Exception:
                    continue
                role = msg.get("role") or msg.get("type") or ""
                content = msg.get("content", "")
                if isinstance(content, list):
                    content = " ".join(
                        c.get("text", "") for c in content if isinstance(c, dict)
                    )
                if content:
                    out.append(f"{role}: {content}")
        return "\n".join(out)[-max_chars:]
    except Exception:
        return ""

def distill(transcript: str) -> str:
    """Demande au modèle LOCAL d'extraire les apprentissages durables."""
    if not transcript.strip():
        return ""
    prompt = (
        "Tu es un archiviste. À partir de la transcription d'une session de dev, extrais "
        "UNIQUEMENT les apprentissages DURABLES et réutilisables, en puces courtes (8 max), "
        "regroupées si pertinent en : Décisions / Conventions / Correctifs / Sources fiables. "
        "Pas de bla-bla, aucun secret ni clé. Si rien d'utile, réponds exactement : (rien).\n\n"
        f"TRANSCRIPTION :\n{transcript}"
    )
    body = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.load(r)
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""

def _prune(content: str) -> str:
    lines = content.splitlines()
    if len(lines) <= MAX_LINES:
        return content
    head = lines[:4]
    tail = lines[-(MAX_LINES - len(head) - 2):]
    return "\n".join(head + ["", "<!-- ...entrées anciennes élaguées... -->"] + tail) + "\n"

def append_memory(distilled: str) -> None:
    if not distilled or distilled.strip().lower() in ("(rien)", "rien", ""):
        return
    mp = memory_path()
    header = (
        "# MEMORY.md — mémoire auto-évolutive du projet\n\n"
        "> Index concis des apprentissages des sessions. Élagué automatiquement.\n"
    )
    existing = mp.read_text(encoding="utf-8") if mp.exists() else ""
    if not existing.strip():
        existing = header
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    content = _prune(existing + f"\n## {stamp}\n{distilled}\n")
    try:
        mp.write_text(content, encoding="utf-8")
    except Exception:
        pass

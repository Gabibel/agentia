#!/usr/bin/env python3
"""SessionStart — réinjecte MEMORY.md dans le contexte de la nouvelle session."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memory_lib as m

def main():
    try:
        mp = m.memory_path()
        ctx = ""
        if mp.exists():
            txt = mp.read_text(encoding="utf-8").strip()
            if txt:
                ctx = (
                    "Mémoire projet (MEMORY.md) — apprentissages des sessions précédentes :\n\n"
                    + txt
                )
        if ctx:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": ctx,
                }
            }))
    except Exception:
        pass
    sys.exit(0)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""SessionEnd — distille la session (LLM local) et l'ajoute à MEMORY.md."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memory_lib as m

def main():
    try:
        ev = m.read_event()
        tp = ev.get("transcript_path", "")
        distilled = m.distill(m.read_transcript(tp)) if tp else ""
        m.append_memory(distilled)
    except Exception:
        pass
    sys.exit(0)

if __name__ == "__main__":
    main()

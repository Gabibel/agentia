#!/usr/bin/env python3
"""PreCompact — filet de sécurité : capture la session AVANT compaction du contexte,
pour ne rien perdre quand Claude Code résume la conversation."""
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

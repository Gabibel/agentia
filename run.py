#!/usr/bin/env python3
"""Point d'entrée CLI : python run.py "<idée>"."""
import asyncio
import sys

# Force UTF-8 on Windows consoles
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from orchestrator import run_pipeline

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run.py \"<votre idée>\"")
        sys.exit(1)
    asyncio.run(run_pipeline(" ".join(sys.argv[1:])))

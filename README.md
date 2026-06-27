# Kit Claude Code — projet « idée → dossier » (local & gratuit)

Dépose ces fichiers à la racine de ton repo, en conservant l'arborescence :

```
ton-repo/
├── CLAUDE.md                         # règles projet (<200 lignes)
├── MEMORY.md                         # créé automatiquement par les hooks (ne pas committer si secrets)
└── .claude/
    ├── settings.json                 # enregistre les 3 hooks (fusionne si tu en as déjà un)
    ├── hooks/
    │   ├── memory_lib.py             # logique partagée (mémoire auto-évolutive)
    │   ├── session_start.py          # réinjecte MEMORY.md au démarrage
    │   ├── session_end.py            # distille la session → MEMORY.md
    │   └── pre_compact.py            # filet de sécurité avant compaction
    └── agents/
        ├── orchestrateur.md          # délègue (modèle fort, pas d'écriture)
        ├── chercheur.md              # recherche web isolée (lecture seule, modèle rapide)
        ├── redacteur.md              # assemble dossier + PRD (skills docx/pdf)
        └── verificateur.md           # contrôle qualité (lecture seule)
```

## Mise en route
1. **Python sur le PATH** (les hooks l'appellent via `python`). Sur Windows, vérifie
   `python --version` dans le terminal.
2. **Ollama lancé** avec un modèle adapté à ta VRAM. Configure si besoin :
   - `OLLAMA_MODEL` (défaut `qwen3:8b`), `OLLAMA_URL`, `MEMORY_MAX_LINES` (défaut 200).
3. Ouvre Claude Code dans le dossier et accepte la confiance du workspace (requis pour les hooks).
4. Les agents apparaissent via `/agents`. L'orchestrateur fonctionne mieux en **mode Delegate**
   (Shift+Tab) : il délègue au lieu d'implémenter.

## Notes
- Les hooks sont **défensifs** : en cas d'erreur (Ollama éteint, etc.), ils n'interrompent
  jamais la session ; ils n'écrivent simplement rien.
- `MEMORY.md` est **auto-élagué** au-delà de ~200 lignes pour rester concis.
- La distillation tourne sur ton **LLM local** (gratuit) — aucune clé API.
- Ajoute `MEMORY.md` à ton `.gitignore` si tu préfères le garder personnel.

# Projet : Système multi-agents « idée → dossier » (100 % local & gratuit)

Source de vérité : `PRD_systeme_multi-agents_local.md`. Lis-le avant toute décision d'architecture.

## Objectif
À partir d'une idée, générer un dossier + un PRD (skills/connecteurs Claude, concurrents,
juridique, reco de stack) en **Markdown + PDF**. Orchestrateur + sous-agents (recherche,
concurrents, juridique, rédacteur, vérificateur).

## Contraintes non négociables
- **100 % local**, **0 € récurrent** : LLM via Ollama (`http://localhost:11434/v1`).
- **Mono-utilisateur**, hors-ligne sauf requêtes de recherche web.
- Sortie : `./out/<slug>/dossier.md`, `dossier.pdf`, `prd.md`.
- Citations obligatoires sur les faits sensibles ; secrets hors repo ; avertissement
  « non-conseil juridique » dans les dossiers générés.

## Règles de comportement (Karpathy)
- Pas d'hypothèses silencieuses : si un choix est ambigu, demande.
- Pas de sur-ingénierie : la solution la plus simple qui marche.
- Ne modifie QUE ce qui est demandé ; ne touche pas au code hors-sujet.
- Critères de succès vérifiables avant de coder une fonctionnalité.

## Ingénierie du contexte
- Ce fichier reste **< 200 lignes**. Les détails vont dans des skills (chargés à la demande)
  ou dans `MEMORY.md`.
- Privilégie les commandes natives `/context`, `/compact`, `/clear`, `/rewind` plutôt que
  d'empiler des plugins.
- **MCP avec parcimonie** (3-4 max) : ils chargent leurs définitions d'outils en plein et
  bloatent le contexte. Les skills, eux, ne coûtent que leur description au repos.

## Activation par tâche = sous-agents scopés (PAS de désactivation globale)
- Chaque sous-agent (`.claude/agents/*.md`) ne reçoit que ses `tools`, ses `skills` et son
  `model`. On n'active/désactive jamais un skill « à la main » : on le scope à l'agent qui
  en a besoin, le reste profite de la divulgation progressive.
- Recherches lourdes → `context: fork` (exécution isolée).
- Skills réservés à l'appel explicite → `disable-model-invocation: true`.
- Orchestrateur en **mode Delegate** (Shift+Tab) : il délègue, il n'implémente pas.

## Mémoire auto-évolutive (le .md se met à jour tout seul)
- Auto-mémoire activée : écris tes apprentissages durables (commandes, conventions,
  correctifs, sources fiables) dans `MEMORY.md`. Le raccourci `#` ajoute une note directe.
- Les hooks `SessionEnd`/`PreCompact` capturent et distillent la session vers `MEMORY.md` ;
  `SessionStart` la réinjecte. Garder `MEMORY.md` concis (élagage auto > ~200 lignes).
- **Côté produit** : le système Python écrit lui aussi un `MEMORY.md` (préférences + sources
  fiables) réutilisé d'un run à l'autre. À implémenter en Python, pas via Claude Code.
- La mémoire est du **contexte**, pas une config dure : pour un blocage strict, utiliser un
  hook `PreToolUse`, jamais la mémoire.

## Sécurité d'installation (skills / MCP)
- N'installe QUE depuis des sources de confiance. Avant chaque install : source + éditeur,
  ce que ça fait, lecture du `SKILL.md` + inspection scripts/hooks (réseau, écritures hors
  dossier, shell, API **payante**), verdict SAFE/À VÉRIFIER/À ÉVITER, puis attendre mon OK.
- MCP : ne JAMAIS saisir mes identifiants. Donne-moi le lien + la commande `claude mcp add …`
  et le privilège recommandé (lecture seule par défaut).
- Désinstalle ce qui ne sert pas (`claude plugin uninstall`).

## Stack
- LLM : Ollama (modèle selon VRAM ; famille Qwen pour le tool-calling).
- Recherche : DuckDuckGo (`ddgs`) ou SearXNG ; extraction `trafilatura`.
- Orchestration : Python `asyncio` + client OpenAI pointant sur Ollama.
- Livrables : Markdown → PDF via WeasyPrint.
- Sous-agents séquentiels (1 GPU local) ; repli free-tier cloud uniquement si besoin.

## Workflow de dev
1. CLAUDE.md (<200 l) + MEMORY.md + hooks (`.claude/hooks/`).
2. Squelette : orchestrateur + 1 sous-agent recherche → sortie `.md`.
3. Sous-agents concurrents/juridique → rédacteur (md→pdf) → vérificateur (citations).
4. CHECKPOINT avant d'étendre.

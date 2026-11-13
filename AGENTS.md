# Non-negotiable user rules

## Rule 1 - Never build the add-on locally, now or in the future (permanent)
User statement: «لا اريد اي بناء للاضافة يتم محليا البناء كله اريده على جيتهاب الآن ومستقبلا ولا اريدك ان تنسى ذلك ابدا».
Meaning: every build of this add-on happens on GitHub Actions only. Never build locally, never package a `.nvda-addon` on this machine, never treat a locally produced package as usable.

- `build_addon.py` enforces this itself: it refuses to run unless `GITHUB_ACTIONS=true` (the environment GitHub sets inside every workflow job) and exits with code 2 plus a clear message otherwise. No local override flag was added on purpose.
- To build: run it by hand — `Actions -> Build add-on -> Run workflow` on `master`, or `gh workflow run build.yml --ref master`. NOTHING builds automatically: a push to `master` and a pull request trigger NOTHING (no build, no release). This is deliberate (user rule).
- To download the built package: `gh run download <run-id> -n advanced_audio_themes-<version>`.
- There is NO build without a release: every manual run of `build.yml` on `master` builds and then creates or refreshes the GitHub Release `v<version>`, attaching the `.nvda-addon` and its `.sha256` (same run). An existing release for that version is refreshed in place. A run from any branch other than `master` is skipped by the job's `if`, so a package can never be produced without a release.
- To release a NEW version: `gh workflow run release.yml` (bumps `manifest.ini` + `buildVars.py`, tags, builds, publishes) or push a `v<x.y>` tag. See `.github/workflows/release.yml`.
- Never commit a built package: `.nvda-addon`, `.sha256`, `dist/`, `build/` stay untracked (`.gitignore`).
- Do not write any new script whose purpose is to build locally.

# Summary

## Objective
Keep the add-on correct and stable: fix every reported defect, keep the hot paths fast and thread-safe, and never break existing functionality.

## Important Instructions
- "لا تكسر اي وظيفة" — do not break any existing functionality.
- The user is blind and uses a screen reader: reply in Arabic, use sequential lists, never tables.
- Never guess an API, a path or a config field name: verify against the official docs or the real installed source.

## Status
All known issues fixed (rounds 1-83). No known remaining bugs. The released version is the one written in `manifest.ini` (9.52 at the time of writing).

## Where the details live
- This file holds only the standing rules, the current state and the hard facts below, so it stays cheap to load in every session.
- The full round-by-round history (what broke, root cause, fix, proof) lives in `AGENTS-HISTORY.md` at the repository root.
- That file is development-only and is excluded from the shipped package by `build_addon.py` (`EXCLUDE_FILES`), exactly like this one.
- When a round is finished, append it to `AGENTS-HISTORY.md`; do not grow this file again.

## Standing facts that must not be forgotten
- The config spec in `handler.py` is the single source of truth for defaults; every runtime and GUI fallback must match it (Round 78).
- Theme sounds DO play during Say All unless the user clears the option (Round 65).
- Only the x64 native engines ship; `lib/x86` is deleted and explicitly excluded (Round 70).
- The package is compressed with LZMA, and a GitHub build publishes or refreshes its release automatically (Round 73).
- The say-all staleness window, the trimming-disabled effect players and the player self-repair are deliberate; do not "simplify" them (Round 60).

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **advanced_audio_themes** (18354 symbols, 58770 relationships, 541 execution flows).

> Index stale? Run `node ../../../../Local/Temp/opencode/gitnexus-storage/advanced_audio_themes-0287f4702a14/run.cjs analyze --index-only` from the project root — it auto-selects an available runner. No `../../../../Local/Temp/opencode/gitnexus-storage/advanced_audio_themes-0287f4702a14/run.cjs` yet? Bootstrap with `npx`, `bunx`, or `pnpm dlx` — e.g. `bunx gitnexus@latest analyze` (npm 11 npx crash; #1939).

## Always Do

- **MUST run impact before editing.** Use `impact({target: "symbolName", direction: "upstream"})` or `node ../../../../Local/Temp/opencode/gitnexus-storage/advanced_audio_themes-0287f4702a14/run.cjs impact "symbolName" --direction upstream --repo .`; report callers, processes, and risk. Never substitute grep for graph analysis. For unified PDG impact, add `mode: "pdg"` with optional `line: <N>` — it returns statement-level `affectedStatements` over CDG + REACHING_DEF and inter-procedural symbols in `interproceduralByDepth`/`byDepth`; no-layer/degraded PDG results are UNKNOWN-risk notes (`--pdg` layer). CLI equivalent: `node ../../../../Local/Temp/opencode/gitnexus-storage/advanced_audio_themes-0287f4702a14/run.cjs impact "symbolName" --direction upstream --mode pdg --line <N> --repo .`.
- **MUST analyze graph changes before committing.** Use `detect_changes({scope: "all"})` (MCP) or `node ../../../../Local/Temp/opencode/gitnexus-storage/advanced_audio_themes-0287f4702a14/run.cjs detect-changes --scope all --repo .` (CLI fallback). `partial: true` or `truncated: true` is not a clean check — a zero means unseen, not unaffected; re-run it. For regression review: `detect_changes({scope: "compare", base_ref: "main"})` or `node ../../../../Local/Temp/opencode/gitnexus-storage/advanced_audio_themes-0287f4702a14/run.cjs detect-changes --scope compare --base-ref "main" --repo .`.
- MUST warn on HIGH/CRITICAL `risk` pre-edit; never use `riskSharedAxes` to waive a HIGH/CRITICAL `risk` warning. Compare File/symbol: MCP File omits axes; Graph-RAG expands File.
- **MUST treat `risk: UNKNOWN` as unresolved, not as low.** An empty caller set is not evidence the symbol is unused — it can also mean the callers are not resolvable by the index (plain-object property access, dynamic dispatch, cross-language calls). `impact` pairs `UNKNOWN` with a `riskNote` saying so. Confirm with a text search before treating the symbol as safe to change or delete; do not proceed on the strength of a zero.
- **MUST use `query({search_query: "concept"})` for concepts/flows, `context({name: "symbolName"})` for a named symbol, or `impact` for blast radius, on read-only callers, dependencies, imports, or execution flow.** Graph first; text search only for empty/`UNKNOWN`/literals.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).
- For control/data dependence, `pdg_query({mode: "controls", target: "fileOrSymbol"})` answers "under what condition does X run?" (CDG, incl. guard clauses) and `pdg_query({mode: "flows", target, variable})` traces "where does variable Y flow?" (REACHING_DEF). `--pdg` layer.

## Never Do

- NEVER edit a function, class, or method before MCP/CLI impact analysis.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis, and never read `UNKNOWN` as an all-clear — it means the walk could not answer, which is the one verdict that requires confirming by other means.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit before MCP/CLI graph change analysis.

## Resources

| Resource | Use for |
| --- | --- |
| `gitnexus://repo/advanced_audio_themes/context` | Codebase overview, check index freshness |
| `gitnexus://repo/advanced_audio_themes/clusters` | All functional areas |
| `gitnexus://repo/advanced_audio_themes/processes` | All execution flows |
| `gitnexus://repo/advanced_audio_themes/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
| --- | --- |
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus-cli/SKILL.md` |
| Work in the Audiothemes area (521 symbols) | `.claude/skills/gitnexus-area-audiothemes/SKILL.md` |
| Work in the BrowserNavEngine area (326 symbols) | `.claude/skills/gitnexus-area-browsernavengine/SKILL.md` |
| Work in the Unspoken area (74 symbols) | `.claude/skills/gitnexus-area-unspoken/SKILL.md` |
| Work in the Studio area (44 symbols) | `.claude/skills/gitnexus-area-studio/SKILL.md` |
| Work in the Scripts area (13 symbols) | `.claude/skills/gitnexus-area-scripts/SKILL.md` |
| Work in the Cluster_9 area (7 symbols) | `.claude/skills/gitnexus-area-cluster-9/SKILL.md` |
| Work in the Cluster_100 area (4 symbols) | `.claude/skills/gitnexus-area-cluster-100/SKILL.md` |

<!-- gitnexus:end -->

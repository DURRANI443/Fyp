# SDLC documentation

Store every project requirement, process description, diagram, architecture decision, evaluation plan, and release record here, grouped by version.

## Version index

| Version | Date | Scope | Implementation status |
| --- | --- | --- | --- |
| [v0.1.0](v0.1.0/README.md) | 2026-10-24 | Initial project, requirements, design, and evaluation baseline | Documentation only; application not implemented |
| [v0.2.0](v0.2.0/README.md) | 2026-10-24 | Same-day English MVP, implementation diagrams, tests and synthetic AI evaluation | Local application implemented; live OpenRouter verification pending key |
| [v0.2.1](v0.2.1/README.md) | 2026-10-24 | Shared-browser session changes and polling lifecycle regression fix | Frontend fix; new same-page/shared-tab browser checks; no schema migration |
| [v0.3.0](v0.3.0/README.md) | 2026-10-24 | Catalog, simulated checkout, audit fixes, and Supabase/Vercel/Oracle configuration | Draft; implementation and local verification in progress, cloud setup requires accounts |

Dates use Asia/Karachi unless an evidence record explicitly says otherwise.

## Conventions

- Use `vMAJOR.MINOR.PATCH/` directories. A milestone adds a new baseline; a correction after capture uses the next version instead of rewriting history.
- Each baseline contains a README, change log, planning/requirements/design evidence as relevant, diagram sources, and a verification record.
- During preparation, label a version **draft**. Once captured in `manifest.json`, preserve its existing files and hashes. Capture does not mean supervisor approval or implemented functionality.
- A manifest hashes every file inside the baseline except itself. The documentation check rejects missing, modified, and unexpectedly added baseline files.
- Keep stable requirement, use-case, decision, and test-case IDs across versions. Explain additions, replacements, and deletions in the change log.
- Diagrams are editable Mermaid `.mmd` files. Store any SVG exports next to their source; keep both synchronized before capture. Do not claim an export exists if only the source exists.
- Keep the root README, `agent.md`, this version index, and reusable tools current. Copy the relevant instruction snapshot into each baseline when project rules change.
- Git records individual edits; named documentation versions preserve readable milestone snapshots. Neither replaces the other.
- Evaluation tables must separate planned targets from observed results. All product test results are NOT RUN until backed by execution evidence.

## Capture procedure

1. Complete the intended documentation and affected diagrams.
2. Check local links and render diagrams where supported.
3. Record actual verification commands and limitations.
4. Set the version README to captured, with the date and scope.
5. Run `python scripts/capture_baseline.py doc/v0.1.0 --date 2026-10-24` with the intended new version path and client-local capture date. The tool refuses to replace an existing manifest.
6. Run `python scripts/check_docs.py` and record the repository revision when a commit is created.

The next version should identify its predecessor and include all documents necessary to understand that milestone, plus an explicit change log. Do not silently edit a captured baseline to make a check pass.

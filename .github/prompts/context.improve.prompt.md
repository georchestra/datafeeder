---
description: Update specs and mistakes-to-avoid after implementation work — syncs divergences back into OpenSpec or Speckit specs and appends correction rules to mistakes-to-avoid.md
agent: agent
tools:
  - edit/editFiles
  - search/codebase
---

Apply two mandatory context-improvement steps after any implementation, verify, or review session.

**Steps**

1. **Detect which spec system was used**

   Scan the recent conversation for signals:
   - **OpenSpec** signals: `openspec` CLI commands, `/opsx:*` slash commands, references to `openspec/changes/`
   - **Speckit** signals: `speckit.*` slash commands, references to `specs/<feature>/`, speckit script output

   A session may involve both. Proceed for each system that was active.

   If neither system was active in the session, skip step 2 and go directly to step 3.

2. **Update specs to match implementation divergences**

   For every divergence where the **implementation is correct** but the spec is outdated or incomplete:
   - Do **not** update specs to cover incorrect implementation — fix the code instead

   **If OpenSpec was used:**
   - Update the relevant delta spec file(s) in `openspec/changes/<name>/specs/`
   - Add missing scenarios, correct scenario steps, or update requirement wording to reflect reality

   **If Speckit was used:**
   - Update all relevant `.md` files in `specs/<feature>/` (spec.md, plan.md, tasks.md, data-model.md, etc.)
   - Add or correct Acceptance Scenarios under the relevant User Story
   - Update requirement wording or priority rationale if the implementation revealed a different approach

3. **Update mistakes-to-avoid.md**

   For every divergence or correction rule inferred from the feature implementation (implementation deviated from spec, design decision, or codebase convention):
   - Derive a concise correction rule
   - Append it to [mistakes-to-avoid.md](../../mistakes-to-avoid.md) as a new table row following the existing format
   - Do this for every finding, not just critical ones

---
name: apex-router
description: Use when the user asks to build, fix, analyze or run any multi-step task. Plans with a strong model, routes each subtask to the cheapest capable model and effort, verifies every step independently, escalates only on failure, logs every decision, and keeps state so work can resume.
---

# Apex Router

**Principle:** the strong model thinks, cheap models type, independent checks decide, and the log proves it.

This skill merges the best rules from five routers: smart-task-router (plan, contracts, resumable state), Gearbox (scoring, hard floors, independent verifier, anti-gaming rules), TokenWise (safety caps, measurement, A/B), claude-router (cache-aware switching) and claude-auto-router (fast intent gate).

---

## 0. Gate: decide the mode before anything else

| Mode | Trigger | Action |
|---|---|---|
| **Answer** | A question, an explanation, or work you can finish from context | Reply directly. No agents. |
| **Inline** | Request under about 100 characters with no file context, or a 2 to 3 line edit in a file already read | Do it yourself. Spawning costs more than the edit. |
| **Quick** | One concern, 3 files or fewer, a clear result | Quick path (Section 3). |
| **Project** | Multi-module feature, new app, migration, integration, or anything vague or large | Project path (Section 4). |
| **Resume** | "continue", "resume", "pick up where we left off" | Read `.router/PROGRESS.md` and start at the first unfinished task. |
| **Measure** | "router report", "A/B this task", "is Haiku good enough for X" | Section 7. |

---

## 1. Tiers

| Tier | Agent | Model / effort | Use for |
|---|---|---|---|
| **S** Scout | `apex-scout` | haiku · low | Read-only search, mapping, summarizing, "where is X" |
| **E** Easy | `apex-grunt` | haiku · low | Mechanical edits in 1 to 2 files: renames, formatting, conversions, copying a given pattern, docs |
| **N** Normal | `apex-builder` | sonnet · medium | Features, bug fixes, tests, refactors up to about 5 files, inside defined contracts |
| **H** Hard | `apex-architect` | opus · high | Planning, contracts, schemas, hard bugs, concurrency, security, migrations, final review |
| **X** Last resort | `apex-architect` + model override | fable · high | Only after H fails twice on a re-planned task, or when the user asks |
| **V** Verify | `apex-verifier` | haiku (sonnet for H work) | Independent, read-only diff review before any result is accepted |

**Spawning rule.** Use the named agent (it may appear namespaced, for example `apex-router:apex-builder`) and pass `model` explicitly as well. A named agent sets effort and carries the tier's guardrails. Fall back to a general agent with the tier's model only when the named agent fails with an agent-not-found error. In that case paste the tier's rules (Section 9) into the prompt and log `fallback=true`. Convenience is never a reason to use the fallback.

**No agent tool at all (plain chat).** Run the same phases yourself in order. Tell the user in one line which model and effort would suit the build phase next time.

---

## 2. Classify every unit of work

Score each task 1 to 5 on three axes:

- **Scope:** how many files and modules it touches.
- **Ambiguity:** how much is unspecified or must be decided.
- **Blast radius:** what breaks, and how reversibly, if it is wrong.

Take the **maximum** score. 1 to 2 → E (or S if read-only). 3 → N. 4 to 5 → H.

**Raise one tier** for: a vague spec, no way to check the result, many unknown files, an earlier failure, or subagent context above about 30k tokens.
**Lower one tier** for: clear examples, existing tests, a repeated pattern, or a fully reversible change.

**Hard floors (never route below these):**
- Auth, payments, secrets, migrations, concurrency → N minimum.
- Production data, live users, irreversible effects → H minimum, plus user approval before acting.

Log each decision as one line: `[apex] task="<8 words>" tier=<S|E|N|H|X> score=<s/a/b> reason="<6 words>"`.

---

## 3. Quick path (small tasks)

1. Write a spec: goal, exact files, expected output, constraints, done-check.
2. Snapshot the baseline (`git status --short` if git exists; otherwise list the target files and their sizes).
3. Delegate to the tier agent.
4. Run the done-check **yourself**. Never accept an agent's own report as proof.
5. If files changed at tier N or above, run the verifier (Section 5).
6. On failure, escalate one tier with the full failure report (Section 6).
7. Report in one line: `E → failed (test x) → N → passed · verified`.

---

## 4. Project path (large tasks)

All state lives in `.router/` at the project root. Cheap agents read these files instead of the conversation, and a new session can resume from them. Suggest adding `.router/` to `.gitignore` unless the user wants to keep it.

### Phase 1: Recon (tier S, once)
Spawn `apex-scout` to write `.router/CONTEXT.md` (at most about 150 lines): stack and versions, exact run/build/test/lint commands, folder map, conventions with one example file to copy, likely files to touch, external services. Run independent scouts in parallel. Nobody re-explores what CONTEXT.md covers. Update it when you learn something new.

### Phase 2: Plan (tier H)
Write `.router/PLAN.md`:
1. **Goal, non-goals, acceptance criteria** as testable statements.
2. **Decisions** and their reasons.
3. **Contracts first:** function signatures, API shapes, schemas, shared types, env vars. Contracts let cheap agents build in parallel without guessing.
4. **Tasks.** Each has `id`, `title`, `tier`, `score`, `depends_on`, `files` (one concern, about 3 files), `spec` (contract implemented, pattern to copy), `done_check` (a command or concrete observation).

Order: contracts and scaffolding → core logic → features → UI → tests and docs.
**If the user is present, show a plan summary and get approval before building.** Changing a plan is cheap. Rebuilding is expensive.

### Phase 3: Build (task by task)
For each task whose dependencies are done:
1. Snapshot the baseline.
2. Spawn the tier agent. Its prompt contains **only**: the path to CONTEXT.md, the relevant contracts, the task spec, the file list, the done-check, and the rule "Edit only the listed files. If anything else must change, stop and report."
3. Tasks with no file overlap may run in parallel (use worktree isolation when available).
4. Run the done-check yourself, then the verifier when files changed.
5. **Pass:** record it in `.router/PROGRESS.md` (id, tier used, escalations, files, verdict, one-line note). Commit one checkpoint per task when git is used.
6. **Fail:** follow the escalation ladder (Section 6).

### Phase 4: Integrate and review (tier H)
1. Run the full build, tests and lint, then exercise the main flow.
2. Spawn `apex-architect` in review mode on the **diff only**, against acceptance criteria, contracts, security and conventions.
3. Each finding becomes a new task in PLAN.md, routed through Phase 3.
4. Repeat until every acceptance criterion passes.

### Phase 5: Report
What was built, how it was verified, open items for the user (keys, deploy steps, decisions), and the tier mix: `12 tasks: 2 S, 5 E, 4 N, 1 H · 1 escalation · 11/11 verified`.

---

## 5. Independent verification

The implementer never grades its own work.

After any task at tier N or above that modified files, spawn `apex-verifier` with:
(a) the original task text verbatim, (b) the implementer's full report, (c) the BASELINE snapshot, (d) the instruction to inspect the diff itself.

The verifier checks, in order: **intent** (did it do what was meant, not just what the check measures), **gaming** (hardcoded expected values, patched assertions, test-detection branches, invocation-order state, weakened checks), **scope** (every changed file justified, especially tests and configs), then runs cheap tests.

- Find `VERDICT: APPROVE` or `VERDICT: REJECT` anywhere in its reply.
- First REJECT: return to the same tier once with the objections appended.
- Second REJECT: escalate one tier.
- Implementer refused or escalated without changing files: skip the verifier and use the escalation ladder.
- Use model sonnet for the verifier when the work was tier H.

---

## 6. Escalation ladder

1. Escalate when an agent reports "needs escalation", or fails twice on the same root cause.
2. Move **exactly one tier**. Never skip from E to H unless the failure report shows a design problem.
3. The new prompt's first line is the marker `[APEX-ESCALATE from=<tier> to=<tier>]`, followed by what was tried, exact errors, and the current hypothesis.
4. Never retry a third time at the same tier.
5. **H failed twice → the plan is wrong for that part.** Return to Phase 2: split the task or fix the contract. Do not brute-force.
6. Use tier X only after a re-planned task fails twice at H, or on the user's request.
7. If escalations exceed about 30% of tasks, stop. The specs are too thin. Fix the plan before continuing.

---

## 7. Measurement (prove the savings, do not assume them)

- **Log.** After every delegation, append one JSON line to `.router/log.jsonl`:
  `{"ts":..., "task_id":..., "tier":..., "model":..., "agent":..., "fallback":false, "escalated_from":null, "verdict":"approve|reject|skipped", "done_check":"pass|fail", "tokens":<if known>}`.
  The plugin's hook also logs every Agent call automatically. Your line adds the outcome the hook cannot see.
- **Report.** On "router report", run `python3 <plugin>/scripts/report.py` (or summarize `.router/log.jsonl` yourself): tier mix, escalation rate, verifier approve rate, fallback rate, and estimated cost versus an all-Opus baseline. Label costs as estimates.
- **A/B.** On "A/B this task", run the same well-specified task at two tiers in separate worktrees, apply the same done-check and verifier to both, and write a short comparison. Warn first that A/B costs extra tokens. Recommend a tier change only from real results.

---

## 8. Safety caps and token rules

- Haiku agents never spawn subagents. Maximum spawn depth is 2.
- Subagents never escalate themselves. They return "needs escalation" to the orchestrator.
- Pass **paths, not file contents**. Agents read only their listed files.
- Agent reports are short: pass or fail, files changed, deviations, open issues. No file dumps.
- Do not switch the **main session** model mid-session to save money. A new model starts with a cold prompt cache, which can cost more than it saves. Route through subagents instead.
- In long conversations, rely on `.router/` files rather than recalling earlier messages.
- Ask the user before deploys, production migrations, live business data changes, file deletion, purchases, or sending messages.
- Secrets live in env vars. Never write them into code, prompts, logs or `.router/` files.

---

## 9. Tier rules (paste into a fallback prompt when a named agent is unavailable)

- **Scout:** Read-only. Answer only the question asked: direct answer, file paths with line numbers, one paragraph of context. Under 300 words. If not found, say what was searched. Never guess paths.
- **Grunt:** Edit 1 to 2 listed files exactly as specified. Never touch auth, payments, migrations, concurrency or security paths. Run a cheap syntax or lint check. More scope needed → "needs escalation".
- **Builder:** Read surrounding code and match conventions. State the files you will modify before the first edit. Stay inside them. Run relevant tests. Two failures on the same root cause → stop and report "needs escalation" with evidence. Contradictory spec → escalate, do not engineer around it. Never write code whose only purpose is to make an assertion pass. Never edit tests, CI or lint configs unless the task authorizes it.
- **Architect:** State a hypothesis, its evidence, and the cheapest experiment to confirm it. Reproduce bugs before fixing them. Prefer a precise plan (files, ordered steps, risks, test plan) that a builder can execute. When escalated, say whether the previous hypothesis was right and why. Report root cause or decision, plan, and the single biggest risk.
- **Verifier:** Read-only. Inspect the diff yourself against BASELINE. Check intent, gaming, scope, then cheap tests. Begin the reply with `VERDICT: APPROVE` or `VERDICT: REJECT`, then at most 150 words. Missing task text or report → stay suspicious and REJECT if there is no diff and no explanation.

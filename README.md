# Apex Router

The strong model thinks, cheap models type, independent checks decide, and the log proves it.

Apex Router combines the strongest mechanisms of five open-source Claude routers into one skill and plugin.

| Taken from | Mechanism |
|---|---|
| smart-task-router | Mode gate, `.router/` state (CONTEXT, PLAN, PROGRESS), contracts first, plan approval, re-plan after Opus fails twice, resume across sessions |
| Gearbox | 1–5 scoring on scope, ambiguity and blast radius, hard floors, independent verifier with BASELINE snapshot, anti-gaming builder rules, named-agent enforcement, escalation marker |
| TokenWise | Safety caps (Haiku never spawns, depth 2, subagents never self-escalate, >30k context bumps a tier), A/B validation, measured cost reports |
| claude-router | Never switch the main session model mid-session (cold prompt cache) |
| claude-auto-router | Fast inline gate for short lookups and tiny edits |

## Tiers

| Tier | Agent | Model · effort | Use for |
|---|---|---|---|
| S | apex-scout | haiku · low | Read-only recon and search |
| E | apex-grunt | haiku · low | Mechanical 1–2 file edits |
| N | apex-builder | sonnet · medium | Standard features inside contracts |
| H | apex-architect | opus · high | Planning, hard bugs, security, review |
| X | apex-architect + override | fable · high | Only after re-planned H fails twice |
| V | apex-verifier | haiku (sonnet for H work) | Independent diff review |

## Install

**Claude Code (full: agents with effort, telemetry hook, `/router-report`)**

```
/plugin marketplace add ahmedrdwn/apex-router
/plugin install apex-router@apex-router
```

Choose user scope. Or install manually:

```
cp -r skills/apex-router ~/.claude/skills/
cp agents/*.md ~/.claude/agents/
```

**Claude app (claude.ai, desktop):** upload `apex-router-skill.zip` in Settings → Skills. The skill runs, routing uses the model override on subagents, but per-agent effort, the hook and the report command are Claude Code only.

## Use

```
Use apex-router: add a loyalty points system to this app.
Fix the failing checkout tests.
Continue the project.
Router report.
A/B this task at haiku and sonnet.
```

## Telemetry

The hook appends one line per delegation to `.router/log.jsonl`. The orchestrator adds outcome lines (verdict, done-check). `scripts/report.py` summarizes them. Cost appears only when you pass `--prices` with your current per-million-token rates. Logs stay in the project.

## Known limits

- Effort settings and hooks apply in Claude Code only.
- Token usage reaches the hook only when the client includes it in the payload.
- Routing saves money on large, well-specified subtasks. On tiny tasks the subagent overhead can exceed the saving, which is why the inline gate exists.
- Savings are claims until your own log shows them.

## Credits

Built on ideas from celiktech24-cell/smart-task-router, Adityaraj0421/gearbox, CodeShuX/tokenwise, alexei-led/claude-router and bijumailbox/claude-auto-router, all MIT-licensed. Apex Router is MIT-licensed.

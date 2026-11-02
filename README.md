# claude_learning

Claude Code skills and subagents for one-task-at-a-time engineering in an existing codebase: understand the repo, write its project docs, clarify the task, plan it, then build it with tests and independent review. Optional guardrail hooks enforce the rules the skills state.

| Skill | Use it to | Writes files |
| --- | --- | --- |
| `/spec-interview <task> [plan.md]` | plan a task or a new project: asks what the code can't answer, then writes acceptance criteria (ACs), design decisions and buildable steps | the plan file you name |
| `/spec-prd [sources]` | create or update the project overview and context: purpose, users, scope, flow, constraints | `docs/PRD.md` |
| `/spec-arch <plan.md>` | create or update the architecture from the code and the plan: repository structure, components, data, flows, interfaces, configuration | `docs/ARCHITECTURE.md` |
| `/spec-claudemd <plan.md>` | create or refresh a lean, verified `CLAUDE.md` from the code, the plan and the two docs | `CLAUDE.md` |
| `/build-phase <task>` | implement one task end to end: tests first, then independent review, fixes and re-review | code and tests, never committed |
| `/followup explore: \| decide: \| implement: <text>` | answer, decide or change something in the middle of a session | only in implement mode |

The subagents are the read-only reviewers that build-phase and followup spawn: `criteria-auditor`, `gap-hunter` and `convention-checker` in round 1, and `gap-rechecker` in re-check rounds. `question-prober` is the independent question generator, and `plan-auditor` the independent plan reviewer, that spec-interview spawns on a deep task.

### Which skill when

| You want to | Use |
| --- | --- |
| understand code, or weigh a tradeoff | `/followup explore: ...` or `/followup decide: ...` |
| change 1-3 files | `/followup implement: ...` |
| build a feature or a multi-file change | `/spec-interview`, then one `/build-phase` line per step, each in a fresh session |
| write or refresh the project docs | `/spec-prd`, `/spec-arch`, `/spec-claudemd` |
| a non-code deliverable (documents, emails, proposals) | no skill: these skills assume a git repository. Analysis outside a repository still works with `/followup explore:` |

**Task profile.** Each skill sizes the task and prints `Profile: light`, `standard` or `deep`, with the trigger that decided it. A task is `deep` when a public contract changes, stored data or a migration is involved, it is a new project, it changes security, permissions or identity, its blast radius reaches beyond the repository (cloud, tenant, production, a client environment), or recon finds more than about 10 files. A deep profile adds an independent `question-prober` and `plan-auditor` to `/spec-interview` and a `criteria-auditor` to small builds; `light` runs no agent beyond `gap-hunter`. Start the arguments with the word `light` or `deep` to override the choice. `shared/task-profile.md` has the rules.

Start Claude Code in the repository root. Claude Code loads `CLAUDE.md`, project settings and memory from the session folder, and the hooks treat that folder as the project. build-phase and followup warn when the session started outside the repository, then continue with `git -C`.

## Requirements

- Claude Code 2.1.295 or later. The hooks use `onFailure`, which older versions ignore.
- `git`, and `python3` on your PATH for the guardrail hooks (tested with Python 3.14.9).
- macOS or Linux. On Windows the hooks need Git Bash; that setup has not been tried.

## Install

Pick a scope. Skills, agents and shared files must sit side by side in the same `.claude` folder, because the skills load `../../shared/` relative to themselves.

**Just you, every project:**

```bash
git clone git@github.com:shahpratikr/claude_learning.git
cd claude_learning
mkdir -p ~/.claude/skills ~/.claude/agents ~/.claude/shared
cp -R skills/. ~/.claude/skills/
cp agents/*.md ~/.claude/agents/
cp -R shared/. ~/.claude/shared/
```

**A whole team, in one repository:** copy the same three folders into that repository's `.claude/` folder and commit them. Everyone who opens the repository in Claude Code gets the skills.

```bash
cd /path/to/your/repo && mkdir -p .claude
cp -R /path/to/claude_learning/{skills,agents,shared} .claude/
```

Then start a new Claude Code session.

**Upgrading from an older copy:** `validate-phase` has been merged into `build-phase`. Delete the old folder: `rm -r ~/.claude/skills/validate-phase`.

### Recommended settings

**Turn fork mode off.** This setting matters most. build-phase waits for its reviewers. In interactive sessions (terminal, VS Code, desktop app), Claude can only wait for a subagent when fork mode is off. If it can't wait, the reviewers' reports arrive later as new turns. The rest of the build then runs without the skill's tool pre-approvals, so you get permission prompts, and on your default model and effort instead of the skill's. Measured on 19 builds with fork mode on: every one left the skill at the first reviewer hand-back or background notification, and 35-45% of each build ran outside it. The skills also never run commands in the background, for the same reason. spec-interview waits for its `question-prober` and `plan-auditor` the same way, so fork mode must be off for it too.

To turn fork mode off, add this to `~/.claude/settings.json`:

```json
{ "env": { "CLAUDE_CODE_FORK_SUBAGENT": "0" } }
```

## First run: guardrails

build-phase, followup, spec-interview, spec-prd, spec-arch and spec-claudemd carry guardrail hooks. The first time you run one of them, it checks whether the hook scripts are installed:

1. **Already installed** in `<project>/.claude/hooks/guardrails/` or `~/.claude/hooks/guardrails/`: it uses them and asks nothing.
2. **Not installed**: it asks whether you want guardrails. If you say yes, it asks where to put them:
   - `~/.claude/hooks/guardrails`: every project. Recommended.
   - `<project>/.claude/hooks/guardrails`: this project only.
   - any other folder.
3. It copies the scripts there, checks that they run, and continues your task.

Notes on the answer:
- **A folder of your own** is written into the `hooks` section of every installed skill and agent. It takes effect from the next skill run. The two standard folders work at once, with no edit.
- **"No"** is remembered, and the skills stop asking. To turn guardrails on later, run `python3 ~/.claude/shared/guardrails/configure.py --dir ~/.claude/hooks/guardrails`, using your install's `shared/` path.
- **For a team**, install the scripts into the repository's `.claude/hooks/guardrails/` and commit them. Nobody gets asked, and everyone runs the same guardrails.

What the guardrails do, at every tool call:
- **Deny:**
  - destructive git: `reset --hard`, `checkout --` and `checkout -f`, `switch -f`, `restore` (unless `--staged` alone), `clean -f`, `stash drop`;
  - `git add -A` and force pushes;
  - recursive `rm` (or PowerShell `Remove-Item -Recurse`) of `/`, `~`, `.` or a folder that holds your home folder, including through a variable or `cd` earlier in the command;
  - `curl ... | sh`, `bash <(curl ...)` and PowerShell `iex` of downloaded content;
  - reading `.env` files, SSH private keys, cloud and cluster credentials (`~/.aws/credentials`, Azure token caches, `~/.kube/config`), `.netrc`, Docker's `config.json` and `.pfx` or `.p12` files through Bash. The Read tool isn't hooked: to cover it too, add the `permissions.deny` rules from `shared/guardrails/settings.example.json` to your settings;
  - writing a credential into any file. The scanner flags literals and known token formats (AWS, GitHub, Anthropic, OpenAI, Google, npm, GitLab, SendGrid, Azure client secrets, storage keys and SAS signatures), not code that reads a secret, such as `os.getenv("API_KEY")` or `var.db_password`;
  - editing Claude Code's own settings or hooks, or writing to credential stores.
- **Ask you first:** every `git commit` and plain `git push`, remote branch or tag deletes, `git branch -D` and pruning the reflog; adding a dependency (`npm install <pkg>`, `pip install <pkg>`, `go get`, `Install-Module`, `dotnet add package`, `az extension add`, ...); cloud, infrastructure and data destruction (`az ... delete` and `purge`, `terraform destroy`, `kubectl delete`, `helm uninstall`, `docker ... prune`, `Remove-Az*` and `Remove-Mg*`, SQL `DROP`, `TRUNCATE` and an unfiltered `DELETE`); outward publishing (`curl` or `wget` uploading a file, `scp` or `rsync` to a remote host, `gh gist create`); reading `.pem`, `.key`, `.tfvars`, Terraform state, `local.settings.json` or `.npmrc`, and dumping the environment; and other recursive deletes.
- **Let through:** recursive deletes at least two levels inside the temp folder, such as a session scratchpad or a `mktemp -d` folder, so reviewers' probe and snapshot folders never wait for a click; and deletes of gitignored, untracked folders inside the project (`dist`, `build`, `.venv`, `node_modules`), so build clean-ups never wait either.

Hooks run outside the model, so a prompt can't talk its way past them. They read a command's arguments one shell segment at a time, so a commit message or a grep pattern that mentions a command is not mistaken for it, and they follow `$(...)`, `bash -c` and `eval`. They are still a strong default rather than a sandbox. For an OS-level boundary, also turn on Claude Code's `/sandbox`. `python3 shared/guardrails/selftest.py` runs every probe in its table through the real scripts (add `--latency` to time a hook call, about 70 ms), and `configure.py` runs it against each install.

Optional, and recommended for a user-level install: to guard sessions that never use these skills, merge `shared/guardrails/settings.example.json` into `~/.claude/settings.json`. It adds the same hooks, plus a prompt check that stops pasted credentials before they reach the model. Without it, a session that uses none of these skills has no guardrails.

## Using the skills

**Plan and project docs.** Each skill writes one file, and the files never repeat each other:
- `/spec-interview` writes the plan, at the path you name: ACs, design decisions, steps and `/build-phase` lines. If you don't name a path, it asks.
- `/spec-prd` writes `docs/PRD.md`: what the project is, for whom and why. It has no directory structure, design or plan.
- `/spec-arch <plan.md>` writes `docs/ARCHITECTURE.md` from the code and the plan's design decisions.
- `/spec-claudemd <plan.md>` writes `CLAUDE.md` from the code, the plan and the two docs: the commands, test rules, conventions, invariants and constraints the other skills read.

For a new project, run them in that order. Each one updates its own file in place on later runs. The docs take decisions from the plan, never its ACs, steps or `/build-phase` lines, and never mention the plan, because a plan goes stale when its task ends. `shared/project-docs.md` decides which file owns which fact.

`CLAUDE.md` is enough to make a change on its own, and it imports nothing. An `@` import would load the whole PRD and ARCHITECTURE.md into every session. So `CLAUDE.md` holds the rules every change must keep (invariants, import direction, where new files go) and names the two docs by path, with the section to read for each code area. ARCHITECTURE.md explains how the code is built and why.

A typical task:

1. `/spec-claudemd` once, if the repository has no `CLAUDE.md`. build-phase reads the test command from it.
2. `/spec-interview <task> <plan.md>` asks every question the code can't answer, writes the plan file, and prints a ready-to-paste `/build-phase ...` line, or one `/build-phase Step N of M ...` line per step for a bigger change. The handoff lines carry the plan path, and build-phase reads the plan: its Brief with your confirmed answers, its Design and its Blast radius. On a deep task an independent `plan-auditor` reviews the written plan before you see the handoff lines.
3. Paste the `/build-phase` line. It runs to the end without approvals and stops only for questions it can't settle from the code. A task of more than about 10 production files stops at a question first and offers a `/spec-interview` line to split it: every review round re-reads the whole change, so a 100-file run takes hours.
4. Review the change and commit it yourself. For multi-step plans, commit each step before starting the next.
5. `/followup` for anything that comes up mid-session. `implement:` changes go through the same review loop as build-phase. It edits files without asking, but its Bash is limited to git commands, so Claude Code asks before it runs your test command or the can-fail script.

**Questions.** Every skill asks through Claude Code's question picker: up to 4 questions per dialog, blocking ones first, with the recommended answer listed first. Choose "Other" to type your own answer. Keep-or-cut lists arrive as checkboxes, and a question that depends on another answer waits for the next dialog. Only open input with no likely answers, such as the task itself, is asked in plain text. Answers carry across skills in the same session, so nothing is asked twice. Where the picker isn't available, such as in `claude -p`, the skill prints the questions as text and waits for a reply like `defaults` or `defaults except Q3=B`.

### What build-phase does

1. Snapshots the working tree without touching it (`git stash create`), so the change can be reviewed with no commit. Files you had already modified stay off-limits.
2. Recon, then a baseline run of tests, lint and typecheck. Existing failures are recorded, not fixed.
3. Prints a Task Brief and test plan, including a table of the input variants each changed format must handle and a pre-mortem per AC. Then it applies the size gate, writes failing tests first and implements until they pass.
4. Runs a can-fail pass: it breaks each changed condition, boundary and guard one at a time and checks that a test fails. Each surviving break gets a test, or a recorded reason why it can't change behavior.
5. Runs a validation loop of at most 3 rounds. Round 1 is a full review. A small change (at most 3 files and 80 lines) gets `gap-hunter` alone (plus `criteria-auditor` under a deep profile); anything larger gets three read-only reviewers in parallel:
   - `criteria-auditor`: is every AC implemented, tested and verifiable, and did anything in the task go missing?
   - `gap-hunter`: every untested scenario, defect and contradiction, with no cap on findings. It proves suspected defects with small probe scripts in the scratchpad;
   - `convention-checker`: project conventions and invariants, each violation marked BLOCKING or MINOR.
   Reviewers see the task, your confirmed answers, the diff and the test and can-fail results, never the builder's reasoning, variant table or fix plans. They never re-run the suite.
   Before any fix, build-phase writes a fix plan: one entry per MUST-FIX finding, with the root cause, every sibling location, the variants, the callers at risk, the failing tests and a pre-mortem. It checks the plan against the code, corrects what is missing, malformed or wrong, prints a `fix-plan check` line, and only then edits.
   Round 2 re-checks. build-phase confirms each fix with evidence (a passing test, a clean search), then spawns `gap-rechecker` on what the fixes changed. It adds the other two reviewers only when an AC changed, a file was created, or a fix couldn't be confirmed. Round 3 runs only when round 2 found a HIGH, overturned a confirmation, or left a production fix it can't prove with a test and killed breaks. After the last review, no production code changes, so nothing reaches you unreviewed.
6. Prints a report with these parts:
   - the verdict, `PASS` or `NEEDS REVIEW`;
   - the AC-to-test map and test results;
   - each validation round;
   - anything that needs your decision;
   - `git diff <BASE>` to review the change, a one-line undo command, and a suggested commit message.
   It never stages, commits, pushes or switches branches.

### Models, effort and cost

Every skill and reviewer runs on Sonnet, the model Improving approves for this work. Where a skill writes code, makes design decisions or writes a file every later session relies on, structure carries the load instead of a bigger model: quoted evidence for every claim, an independent reviewer for risky tasks, and checks that run outside the model (tests, the can-fail pass, the guardrail self-test, the promptfoo suite). Both `model:` and `effort:` in the frontmatter are honored: a skill's values override the session's for as long as the run stays inside the skill.

| File | Model | Effort |
| --- | --- | --- |
| build-phase | sonnet | high |
| followup | sonnet | high |
| spec-interview, spec-arch, spec-claudemd | sonnet | high |
| spec-prd | sonnet | high |
| gap-hunter (round 1) | sonnet | xhigh |
| gap-rechecker (round 2 and 3) | sonnet | medium |
| criteria-auditor, convention-checker | sonnet | medium |
| question-prober | sonnet | high |
| plan-auditor | sonnet | high |

A skill's `effort:` is honored, and so is an agent's. Checked in a headless sandbox run (Claude Code 2.1.308, 2026-11-01) with throwaway skills: `effort: low`, `effort: high` and no field gave `low`, `high` and the session's `xhigh` on every main-thread call. The skill kept its model and attribution after each reviewer returned, and each of the four reviewers ran in the foreground at the effort in the table.

build-phase and followup run at `effort: high`, the target an A/B run was meant to confirm. That A/B has not been completed, so `high` is a judgment, not a measurement. To measure it, build one plan step twice from the same commit in two git worktrees, with `effort: xhigh` in one copy of the skill and `effort: high` in the other, and compare each run's round-1 HIGH and MED findings (each checked by hand), the same per 100 changed production lines, cost and rounds, using `measure_sessions.py`. Keep `high` only if `xhigh` finds at most 2 more real HIGH and MED findings and `high` costs at least 20% less; otherwise set `xhigh`.

Measured cost on the previous model, before these settings: 15 build-phase runs averaged $21.7, from $11.7 to $39.4. About two thirds of it was re-reading context, not new output: thinking stays in context and is paid for again on every call, so effort drives both. The size of the change drives the rest: keep each run within the size gate.

To measure your own runs: `python3 ~/.claude/shared/tools/measure_sessions.py --filter <repo-name>`. It prints cost, lines added, effort, model, calls that ran outside the skill, peak context, each reviewer's model, effort and foreground or background shape, the round records and the fix-plan check lines.

## Updating

Pull the repository and copy the folders again, as in Install. Re-copying resets every `hooks` section to its default:
- guardrails in the two standard folders are found again automatically;
- if you chose a folder of your own, the next guarded skill asks again. Give it the same folder; the scripts are refreshed in place.

Copying never deletes. Remove skills and agents the repository no longer ships by hand: `rm -r ~/.claude/skills/{analyze-repo,validate-phase}` and `rm ~/.claude/agents/{spec-validator,test-reporter}.md`.

A `CLAUDE.md` written by an older spec-claudemd `@`-imports the PRD and ARCHITECTURE.md, and its invariants still sit in ARCHITECTURE.md. To move them, run `/spec-claudemd <plan.md>`, then `/spec-arch <plan.md>`.

## Uninstall

```bash
cd ~/.claude
rm -r skills/{build-phase,followup,spec-arch,spec-claudemd,spec-interview,spec-prd}
rm agents/{convention-checker,criteria-auditor,gap-hunter,gap-rechecker,plan-auditor,question-prober}.md
rm -r shared/guardrails shared/tools shared/guardrails-setup.md shared/project-docs.md shared/question-round.md shared/scenario-checklist.md shared/validation-loop.md shared/discovery-probes.md shared/verification-profiles.md shared/task-profile.md
rm -r hooks/guardrails
```

## Troubleshooting

| You see | Cause | Fix |
| --- | --- | --- |
| `PreToolUse:Bash hook error: guardrails: guard_bash.py not found in <folder>` on every call | the folder you chose for guardrails was moved or deleted | in a terminal: `python3 ~/.claude/shared/guardrails/configure.py --dir "<folder>"`, or `--off` |
| a call denied with `[guardrail:<rule>]` | a guardrail did its job | run the command yourself if you really mean it |
| permission prompts, or your default model, after build-phase's reviewers report | fork mode is on, so the reviewers ran in the background | set `CLAUDE_CODE_FORK_SUBAGENT=0` (Recommended settings); `measure_sessions.py` shows `background` per reviewer |
| "This session started outside <repo>" | Claude Code was started in a parent folder | start it in the repository root, so its `CLAUDE.md`, settings and memory load |
| a project's copy of a skill doesn't run | a personal skill of the same name in `~/.claude/skills` wins | delete one of them; for agents it's the reverse: the project copy wins |
| "can't find scenario-checklist.md / validation-loop.md" | `shared/` isn't next to `skills/` | copy `shared/` as in Install |
| a reviewer or helper agent can write files | an old agent file with `allowedTools:`, a field Claude Code silently ignores | re-copy `agents/`; the field is `tools:` |

To see the guardrails' denials and questions, read `guardrail-hooks.jsonl` in the `logs/` folder next to the installed scripts. Passes are not logged unless you set `GUARDRAIL_LOG_PASS=1`, and the file is capped at about 1 MB with one rotated copy. Secrets are masked before anything is written.

## Repository layout

| Path | What it is |
| --- | --- |
| `skills/<name>/SKILL.md` | the six skills |
| `agents/*.md` | the reviewers, the question-prober and the plan-auditor; none has write tools or changes the repository. gap-hunter's and gap-rechecker's probe scripts go in the scratchpad |
| `shared/scenario-checklist.md` | test-scenario categories used by build-phase, followup, the reviewers and spec-interview |
| `shared/validation-loop.md` | the can-fail pass and the review, fix and re-review procedure used by build-phase and followup |
| `shared/project-docs.md` | which of the plan file, `PRD.md`, `ARCHITECTURE.md` and `CLAUDE.md` owns each kind of fact, used by the four spec skills |
| `shared/question-round.md` | how every skill asks questions: the picker, the recommended-first order and the text fallback |
| `shared/task-profile.md` | the lanes, the triggers and the light, standard and deep profiles every skill prints after recon |
| `shared/verification-profiles.md` | how to verify a task that has no unit tests (infrastructure, scripts, configuration, docs): the checks per file type and the rules for a validation command |
| `shared/discovery-probes.md` | the eleven categories of mandatory probes spec-interview answers before it plans, and the extras by task type |
| `shared/guardrails-setup.md` | the first-run guardrails questions |
| `shared/guardrails/` | the hook scripts (`guard_bash.py`, `guard_write.py`, `guard_prompt.py`), `selftest.py`, `configure.py` (installs them and points the skills at them), and `settings.example.json` |
| `shared/tools/measure_sessions.py` | measures runs from Claude Code's transcripts: cost, effort, skill escapes, context, reviewers, rounds |

## Contributing

- Edit the files in this repository, not your installed copies, then re-install.
- Every guarded skill and agent shares the same hooks block, starting with `GR_DIR=UNSET;`. `configure.py` rewrites that marker, so keep the block identical across files.
- To try changed hook scripts without installing them, start Claude Code with `GUARDRAILS_HOOKS_DIR="$PWD/shared/guardrails" claude`.
- To see what a hook decides without running Claude: `python3 shared/guardrails/guard_bash.py --dry-run "git push -f origin main"`.
- To test the guardrail scripts after an edit, run `python3 shared/guardrails/selftest.py`. A new rule needs probes in its table, safe commands included, so the rule cannot grow too wide.
- Claude Code ignores frontmatter fields it doesn't recognise, without an error. Check field names against the [skills](https://code.claude.com/docs/en/skills) and [subagents](https://code.claude.com/docs/en/sub-agents) references.

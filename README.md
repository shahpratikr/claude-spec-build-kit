# claude_learning

Claude Code skills and subagents for one-task-at-a-time engineering in an existing codebase: understand the repo, clarify the task, plan it, then build it with tests and independent review. Optional guardrail hooks enforce the rules the skills state.

| Skill | Use it to | Writes files |
| --- | --- | --- |
| `/analyze-repo [path]` | map an unfamiliar repo: structure, tests, risk hotspots | `REPO_ANALYSIS.md` |
| `/spec-claudemd` | create or refresh a lean, verified `CLAUDE.md` | `CLAUDE.md` |
| `/spec-interview <task>` | turn a vague task into acceptance criteria (ACs) by asking you what the code can't answer | no |
| `/spec-arch <task or brief>` | plan a multi-step change and split it into buildable steps | no |
| `/build-phase <task>` | implement one task end to end: tests first, then independent review, fixes and re-review | code and tests, never committed |
| `/followup explore: \| decide: \| implement: <text>` | answer, decide or change something in the middle of a session | only in implement mode |

The subagents (`criteria-auditor`, `gap-hunter`, `convention-checker`) are the reviewers build-phase spawns. `test-reporter` and `spec-validator` are standalone helpers.

## Requirements

- Claude Code 2.1.295 or later. The hooks use `onFailure`, which older versions ignore.
- `git`, and `python3` on your PATH for the guardrail hooks.
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

### Recommended setting

build-phase waits for its three reviewers. In interactive sessions (terminal, VS Code, desktop app), Claude can only wait for a subagent when fork mode is off. If it can't wait, the reviewers' reports arrive later as new turns. The rest of the build then runs without the skill's tool pre-approvals, so you get permission prompts, and on your default model instead of the skill's.

To turn fork mode off, add this to `~/.claude/settings.json`:

```json
{ "env": { "CLAUDE_CODE_FORK_SUBAGENT": "0" } }
```

## First run: guardrails

build-phase, followup, analyze-repo and spec-claudemd carry guardrail hooks. The first time you run one of them, it checks whether the hook scripts are installed:

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
  - destructive git: `reset --hard`, `checkout --`, `restore`, `clean -f`, `stash drop`;
  - `git add -A` and force pushes;
  - recursive `rm` of `/`, `~` or `.`;
  - `curl ... | sh`;
  - reading `.env` files, SSH private keys or cloud credentials;
  - writing a credential into any file;
  - editing Claude Code's own settings or hooks.
- **Ask you first:** every `git commit`, adding a new dependency (`npm install <pkg>`, `pip install <pkg>`, `go get`, ...), and other recursive deletes.

Hooks run outside the model, so a prompt can't talk its way past them. They match command text, though, so they are a strong default rather than a sandbox. For an OS-level boundary, also turn on Claude Code's `/sandbox`.

Optional: to guard sessions that never use these skills, merge `shared/guardrails/settings.example.json` into `~/.claude/settings.json`. It adds the same hooks, plus a prompt check that stops pasted credentials before they reach the model.

## Using the skills

A typical task:

1. `/analyze-repo` once, if the repository is new to you. `/spec-claudemd` once, if it has no `CLAUDE.md`. build-phase reads the test command from `CLAUDE.md`.
2. `/spec-interview <task>` asks every question the code can't answer, then prints a Task Brief and a ready-to-paste `/build-phase ...` line.
3. `/spec-arch <brief>`, for changes bigger than one step. It prints one `/build-phase Step N of M ...` line per step.
4. Paste the `/build-phase` line. It runs to the end without approvals and stops only for questions it can't settle from the code.
5. Review the change and commit it yourself. For multi-step plans, commit each step before starting the next.
6. `/followup` for anything that comes up mid-session. `implement:` changes go through the same review loop as build-phase.

### What build-phase does

1. Snapshots the working tree without touching it (`git stash create`), so the change can be reviewed with no commit. Files you had already modified stay off-limits.
2. Recon, then a baseline run of tests, lint and typecheck. Existing failures are recorded, not fixed.
3. Prints a Task Brief and test plan, then writes failing tests first and implements until they pass.
4. Runs a validation loop of at most 3 rounds. In each round it runs the full suite, then three read-only reviewers in parallel:
   - `criteria-auditor`: is every AC implemented and tested, and did anything in the task go missing?
   - `gap-hunter`: untested scenarios and defects;
   - `convention-checker`: project conventions.
   Reviewers see the task and the diff, never the builder's reasoning. Every MUST-FIX finding gets a failing test and a fix, and then the round runs again.
5. Prints a report with these parts:
   - the verdict, `PASS` or `NEEDS REVIEW`;
   - the AC-to-test map and test results;
   - each validation round;
   - anything that needs your decision;
   - `git diff <BASE>` to review the change, a one-line undo command, and a suggested commit message.
   It never stages, commits, pushes or switches branches.

**Cost.** build-phase runs on opus and its reviewers on sonnet. Each round spawns three reviewers, so a hard task can take several minutes. Change the `model:` lines in the skill and agent files if that trade-off doesn't suit you.

## Updating

Pull the repository and copy the folders again, as in Install. Re-copying resets every `hooks` section to its default:
- guardrails in the two standard folders are found again automatically;
- if you chose a folder of your own, the next guarded skill asks again. Give it the same folder; the scripts are refreshed in place.

## Uninstall

```bash
cd ~/.claude
rm -r skills/{analyze-repo,build-phase,followup,spec-arch,spec-claudemd,spec-interview}
rm agents/{convention-checker,criteria-auditor,gap-hunter,spec-validator,test-reporter}.md
rm -r shared/guardrails shared/guardrails-setup.md shared/scenario-checklist.md shared/validation-loop.md
rm -r hooks/guardrails
```

## Troubleshooting

| You see | Cause | Fix |
| --- | --- | --- |
| `PreToolUse:Bash hook error: guardrails: guard_bash.py not found in <folder>` on every call | the folder you chose for guardrails was moved or deleted | in a terminal: `python3 ~/.claude/shared/guardrails/configure.py --dir "<folder>"`, or `--off` |
| a call denied with `[guardrail:<rule>]` | a guardrail did its job | run the command yourself if you really mean it |
| permission prompts, or your default model, after build-phase's reviewers report | fork mode is on, so the reviewers ran in the background | set `CLAUDE_CODE_FORK_SUBAGENT=0` (Recommended setting) |
| a project's copy of a skill doesn't run | a personal skill of the same name in `~/.claude/skills` wins | delete one of them; for agents it's the reverse: the project copy wins |
| "can't find scenario-checklist.md / validation-loop.md" | `shared/` isn't next to `skills/` | copy `shared/` as in Install |
| a reviewer or helper agent can write files | an old agent file with `allowedTools:`, a field Claude Code silently ignores | re-copy `agents/`; the field is `tools:` |

To see the guardrails' decisions, read `guardrail-hooks.jsonl` in the `logs/` folder next to the installed scripts. Secrets are masked before anything is written.

## Repository layout

| Path | What it is |
| --- | --- |
| `skills/<name>/SKILL.md` | the six skills |
| `agents/*.md` | the subagents; reviewers have no write tools, and their Bash is limited to read-only commands |
| `shared/scenario-checklist.md` | test-scenario categories used by build-phase, the reviewers and spec-interview |
| `shared/validation-loop.md` | the review, fix and re-review procedure used by build-phase and followup |
| `shared/guardrails-setup.md` | the first-run guardrails questions |
| `shared/guardrails/` | the hook scripts, `configure.py` (installs them and points the skills at them), and `settings.example.json` |

## Contributing

- Edit the files in this repository, not your installed copies, then re-install.
- Every guarded skill and agent shares the same hooks block, starting with `GR_DIR=UNSET;`. `configure.py` rewrites that marker, so keep the block identical across files.
- To try changed hook scripts without installing them, start Claude Code with `GUARDRAILS_HOOKS_DIR="$PWD/shared/guardrails" claude`.
- To see what a hook decides without running Claude: `python3 shared/guardrails/guard_bash.py --dry-run "git push -f origin main"`.
- Claude Code ignores frontmatter fields it doesn't recognise, without an error. Check field names against the [skills](https://code.claude.com/docs/en/skills) and [subagents](https://code.claude.com/docs/en/sub-agents) references.

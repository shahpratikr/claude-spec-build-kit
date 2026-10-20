# Guardrails Setup

Run by every skill that declares guardrail hooks, before any other step. It decides where the guardrail scripts live, so the skill's `hooks` section can use them.

How the hooks find the scripts, at every tool call:
1. the folder written in the hooks section as `GR_DIR='<folder>'`;
2. `<project>/.claude/hooks/guardrails/`;
3. `~/.claude/hooks/guardrails/`.
With none found and `GR_DIR` unset or `off`, the hooks let calls through, so this setup can run. When `GR_DIR` names a folder that has lost its scripts, the hooks block every call until the scripts are reinstalled.

## Steps
1. Read the `GR_DIR=` value in this skill's hooks section, `${CLAUDE_SKILL_DIR}/SKILL.md`.
2. Use the Glob tool to look for `guard_bash.py` in `.claude/hooks/guardrails/` under the project root, then in `~/.claude/hooks/guardrails/`. If either exists, guardrails are active: skip the questions and continue the skill.
3. If `GR_DIR` names a folder and `<folder>/guard_bash.py` exists, guardrails are active: continue the skill. If the folder has lost its scripts, the hooks are blocking every Bash call and file write, including the repair. Stop and give the user this command to run in a terminal: `python3 "${CLAUDE_SKILL_DIR}/../../shared/guardrails/configure.py" --dir "<folder>"`, or the same command with `--off` instead of `--dir "<folder>"`.
4. If `GR_DIR` is `off`, the user declined earlier: continue the skill without asking.
5. Otherwise ask, and do not start any of the skill's own steps until the user answers: this question is always BLOCKING, because without an answer the skill would run unguarded. Ask with AskUserQuestion, one question at a time. If that tool is unavailable or returns no answer, make both questions and their options the first thing in your reply, then stop. When the user answers, apply it (step 6) and start the skill from its first step.
   a. "Use guardrail hooks with these skills? They deny destructive git commands, force pushes and credentials written to files, and make commits and new dependencies wait for your click." Options: "Yes (recommended)" and "No".
   b. On yes: "Where should the guardrail scripts go?" Options: "~/.claude/hooks/guardrails (every project, recommended)", "<project>/.claude/hooks/guardrails (this project only)", and "Other: type a folder".
6. Apply the answer with one command:
   - yes: `python3 "${CLAUDE_SKILL_DIR}/../../shared/guardrails/configure.py" --dir "<folder>"`
   - no: `python3 "${CLAUDE_SKILL_DIR}/../../shared/guardrails/configure.py" --off`
   It copies the scripts and checks that they run. For any folder other than the two standard ones, it writes the folder into the hooks section of every guarded skill and agent installed next to this skill.
7. Tell the user in one line where guardrails now live, or that they are off. Hooks are registered when a skill starts, so a folder written into the hooks section applies from the next skill run; the two standard folders apply at once. Then continue the skill.

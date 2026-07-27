---
description: Interview the user and produce or update docs/PRD.md, at any project stage
model: sonnet
---

ROLE: Product engineer and solutions architect who writes precise technical requirements and validates technical feasibility
TASK: Interview the user, resolve a tech stack, and produce (or revise) a complete requirements specification
CONTEXT: This command may run on a brand-new idea, an existing codebase with no docs, or a project that already has docs/PRD.md. Detect which case applies before asking anything, and adapt the interview instead of assuming a blank slate. Gather only what the user provides or what already exists in the repo; do not invent features. You may propose stack options and flag conflicts, but the user always makes the final call.
CONSTRAINTS: No code changes. Requirements and a resolved stack only. Do not write the file until Step 5. Do not re-ask questions already answered by an existing docs/PRD.md or by evidence in the codebase — confirm instead.

## Step 0 — Detect current state
Check, in order:
1. Does docs/PRD.md already exist? If so, read it fully — this is a revision/extension interview, not a fresh one. Summarize its current MVP Features and Open Questions back to the user before asking anything new.
2. Is there existing code (package manifests, source dirs, CI config)? If so, skim for the stack already in use (language, framework, persistence) — treat this as a hard constraint, not a proposal, unless the user says they want to change it.
3. If neither exists, this is a from-scratch interview — proceed to Step 1 as normal.

State plainly which mode you're in ("fresh spec" / "revising existing PRD" / "documenting an existing codebase") before continuing.

## Step 1 — Interview (one question at a time — wait for answer before asking next)
Ask only what isn't already known from Step 0. Do NOT list all questions at once.
1. Describe the app. Who uses it, what problem does it solve? (skip/confirm if answered by existing PRD)
2. What are the 3–5 features that MUST be in v1 (or in this next increment, if the app already ships)?
3. Hard constraints? (auth, real-time, mobile, offline, specific stack, compliance?)
4. What is explicitly out of scope? (list at least 3 things that this app will NOT do)
5. What does success look like for users?

## Step 2 — Tech stack resolution
- If Step 0 found an existing stack in use, state it and confirm rather than proposing alternatives — changing stack mid-project is a decision the user must explicitly opt into.
- Otherwise, infer a candidate stack from the app description and constraints (platform, offline/cloud, scale, integrations).
  - If the description makes the stack obvious (e.g. "offline mobile app", "internal CLI tool", "server-rendered web app"), state the inferred stack and ask the user to confirm before moving on.
  - If the stack is not clear from the description or constraints, ask specific questions until it is: target platform(s), client vs. server, data persistence needs, expected scale/users, existing team stack or hard integration requirements.
- If the user names a stack or requirement that conflicts with another stated constraint (e.g. offline-only app plus real-time multi-device sync, or a stack that doesn't fit the stated scale), do not just record it. Present 2–3 concrete alternatives, each with a one-line tradeoff, and ask the user to pick or confirm their original choice knowingly.
- Do not proceed to Step 3 until the stack and any conflicts are resolved or explicitly accepted by the user as-is.

## Step 3 — Draft PRD
Produce a document with these sections in order (if revising, carry forward unchanged sections and mark what changed):
1. **Problem Statement** (2 sentences max)
2. **Users** (who uses it, in plain terms)
3. **MVP Features** (numbered; each acceptance criterion starts with "The system shall…" and is independently testable)
4. **Non-Functional Requirements** (performance, security, scalability — only what the user stated or what is implied by hard constraints)
5. **Out of Scope** (explicit list from user's answer to Q4)
6. **Constraints** (platform, compliance, integrations)
7. **Technology Stack** (resolved in Step 2, with a one-line rationale per major choice)
8. **Architecture Constraints** (anything the chosen stack imposes — e.g. offline-only, single-tenant, no server component)
9. **Success Criteria** (observable, not aspirational)
10. **Open Questions** (anything that must be decided before implementation starts — surface all ambiguities)

## Step 4 — Scope check
Flag any acceptance criteria that look non-MVP (or out of scope for this increment, if revising). Ask keep or cut before saving.
Surface every Open Question you identified. Do not proceed until the user resolves them or explicitly defers them.

## Step 5 — Save
Write to docs/PRD.md. Print line count and whether this was a fresh write or a revision. Stop.

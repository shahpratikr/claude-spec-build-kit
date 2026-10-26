# Project Docs

Used by spec-interview, spec-prd, spec-arch and spec-claudemd. It decides which file owns each kind of fact, so the files never repeat each other.

## Files
Use a file that already exists under any case (`docs/prd.md` counts as the PRD); otherwise create the name below.

| File | Written by | Answers | Owns |
|---|---|---|---|
| `docs/PRD.md` | spec-prd | what the project is, for whom, and why | purpose; the problem and the context around it; users and what each does with it; what it does, as a user sees it; what it does not do; the end-to-end user flow; constraints and limitations a user must plan around; the domain glossary; open product questions |
| `docs/ARCHITECTURE.md` | spec-arch | how it is built | system shape and external systems; repository structure; components and what each depends on; runtime and dependencies with reasons; data and state; how the main flows run through the components; interfaces (commands and flags, APIs, events, file formats, outputs, exit codes); configuration and defaults; design decisions with rejected options; open technical questions |
| `CLAUDE.md` | spec-claudemd | how to change the repo without breaking it | commands; test layout and rules; coding conventions and file placement rules, with evidence; invariants, the import and layering rules first, each with what enforces it; hard constraints; a map of the two docs that says which section to read for what |
| plan file, at the path the user names | spec-interview | what a task will change and in what order | goal and scope; acceptance criteria; scenario coverage; confirmed answers; design decisions; blast radius; steps; `/build-phase` lines |

Flow: spec-interview writes the plan, spec-prd the overview, spec-arch reads the plan, the PRD and the code, and spec-claudemd reads all three plus the code. Each skill reads whatever already exists, so the order can vary.

## Rules
1. One owner per fact. Write only what your file owns. When your file needs a fact another file owns, point to it in one clause ("exit codes: see ARCHITECTURE.md, Interfaces"); never restate it.
2. A rule users must plan around is a PRD constraint; a rule code must preserve is a CLAUDE.md invariant. When one rule is both, the PRD states it and the invariant says only what the code must do. ARCHITECTURE.md describes how the code is built and why; CLAUDE.md states what a change must keep and where new code goes.
3. Inside a file, each fact appears once, in the section that owns it. The intro says what the file covers; it never summarizes the sections below it.
4. Task material lives only in the plan file: acceptance criteria, user stories, requirement ids, scenario coverage, step or phase plans, `/build-phase` lines and blast-radius tables. None of the three docs holds it, or progress reports, change history or what changed in this run. spec-arch and spec-claudemd read the plan for its decisions (stack, structure, components, data, interfaces, configuration, commands, conventions, import direction, invariants) and state those as facts in their own words. They never copy a plan section, step number or AC, never name the plan file, and never `@`-import it: a plan goes stale when its task ends.
5. No provenance. Never name the documents, chats, other repositories or programs the content came from (a stories file, a sibling repo used for style, a certification), and never say something exists because of them. State the fact itself.
6. Facts only. Every statement is true of the code, or of the confirmed design when there is no code yet. In an existing codebase, every path and name you cite exists, and anything not built yet is marked planned. In a repo with no code, the intro says once that the file describes the planned design.
7. Match the style of the repo's existing docs (heading depth, line wrap, tables versus lists). With none, follow the skill's template.
8. Write only your own file. When another file holds something your file owns, or repeats it, report it with the skill that should remove it.
9. No file `@`-imports another. CLAUDE.md loads into every session, and an import would load the whole PRD and ARCHITECTURE.md with it. CLAUDE.md is enough to make a change on its own, and names the two docs by plain path.

## Duplicate check (before saving)
1. Within the file: a fact stated in two sections, or in the intro and a section, is cut to the section that owns it.
2. Across files: read the other two files if they exist. A fact the other file owns is cut from yours and pointed to. A fact your file owns that the other file also holds stays in yours and is reported (rule 8).
3. Print one line: `duplicates: cut <n> within, <n> against <file>; reported <n> in <file>`, or `duplicates: none`.

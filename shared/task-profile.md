# Task Profile

Used by plan-task, build-task and followup. It sizes a task once, so the depth of work, and its cost, fit the risk.

Lanes:
1. Change code, infrastructure or configuration in a git repository: plan-task, build-task, followup implement.
2. Understand or decide, in or out of a repository: followup explore and decide.
3. Produce a non-code deliverable (documents, emails, proposals): no skill covers it. Say so and answer plainly.

Triggers. Any one makes the profile deep:
- a public contract changes (API, CLI, event, schema, config, flag)
- stored data or a migration is involved
- the task is a new project
- the task changes security, permissions or identity
- the blast radius reaches beyond the repository: cloud, tenant, production or a client environment
- recon finds more than about 10 files

Profile: deep when any trigger holds; light when none holds and the change is at most 3 files; standard otherwise. When unsure, take the cheaper profile and say so. A leading word `light` or `deep` in the arguments overrides the choice.

| Profile | Planning | Build review | Extra agents |
| --- | --- | --- | --- |
| light | followup implement, or a single-step plan | size tier S, gap-hunter alone | none |
| standard | plan-task | size tier by change size, as today | none beyond the reviewers |
| deep | plan-task plus an independent question-prober and plan-auditor | ac-auditor also at size tier S | two more planning agent runs, one more reviewer run |

After recon, print `Profile: <light | standard | deep> (<trigger or none>)` once, and carry it into the report's Spend line.

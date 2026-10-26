# Question Round

Every question a skill puts to the user goes through this file, wherever a skill or shared step says "ask": clarification rounds, keep-or-cut gates, file paths, design decisions, NEEDS DECISION items from the validation loop, mid-run questions in build-phase and followup, and the guardrails setup. Used by spec-interview, spec-prd, spec-arch, spec-claudemd, followup, build-phase, the validation loop and the guardrails setup. It decides how questions reach the user, so every skill asks the same way.

## Before asking
Give every question these parts:
- Q<n>, numbered on from the last question in this session, BLOCKING or NON-BLOCKING, and a category from the skill's checklist.
- The question, and why it matters: how the answer changes the result.
- 2-4 options. Your recommendation comes first, with its reason and a confidence tag: [Certain], [Likely] or [Guessing].
- A default for when it stays unanswered: stop for BLOCKING, the recommended option for NON-BLOCKING unless you say otherwise.

Shape each question to fit the picker:
- More than 4 real options: offer the 4 most likely and name the rest in the question text, so they stay reachable through "Other". When no 4 are clearly more likely, split the question.
- Yes or no: two options, the recommended one first.
- Keep or cut for a list of items: one multiSelect question per 4 items, "Select the items to keep". Each item is an option whose description says what keeping it costs. Items you recommend keeping come first and end in "(Recommended)".
- Depends on another answer: when its options would change with a pending answer, ask it in the next round, never in the same dialog.
- Open input with no likely values (the task itself, a description to paste): skip the picker. Ask in one plain line and stop; the user's next message is the answer.

Before a round of two or more questions, print as text:
- "Resolved from code (challenge me if wrong)": item -> file:line
- "Recommended path": 2-4 lines on what happens if the user accepts every recommendation
- one count line, for example "11 questions: 5 blocking, 6 non-blocking, in 3 dialogs"

## Ask with AskUserQuestion
- Up to 4 questions per call, BLOCKING first, then NON-BLOCKING, grouped by category. With more than 4, make as many calls as needed, back to back, with no other work between them. Numbering continues across calls.
- question: `Q<n> [BLOCKING | NON-BLOCKING] <question> Why it matters: <one line>`. Name the default here when it is not the recommended option.
- header: the category, at most 12 characters.
- options: the recommended one first, its label ending in "(Recommended)" and its description giving the reason and the confidence tag. Every other description says what choosing it changes. Labels are at most 5 words. Do not add an "Other" option: the picker adds one for typed answers, so a question that needs a name, number or date still offers 2-4 likely values.
- multiSelect only when the options do not exclude each other.

Mid-run questions (build-phase, followup IMPLEMENT, the validation loop) are asked the moment they arise, in the same format, and the run continues in this turn once they are answered. Code the answer affects stays untouched until then.

Subagents never ask the user. They list open questions in their report, and the calling skill asks them in its next round.

## Fallback: text, then stop
If AskUserQuestion is unavailable or fails, or the user dismisses the dialog before answering everything, keep the answers you got and print every question still open in this format, then STOP:

```
Q<n> [BLOCKING | NON-BLOCKING] [category] <question>
   Why it matters: <how the answer changes the result>
   Options: A) ...  B) ...  (C) ...
   Recommendation: <option> - <reason> [Certain | Likely | Guessing]
   If unanswered I will: <default action>
```

End with "Reply with": `defaults` | `defaults except Q3=B, Q7: <text>` | `skip Q5` | answers per question.

## After the answers
- Print a "Confirmed" table: Q | answer | source (user | default). Unanswered NON-BLOCKING questions take their default, flagged as such.
- A typed "Other" answer that is ambiguous, or that opens choices the options did not cover, becomes a new question. Never guess what it means.
- An unanswered BLOCKING question means do not proceed: ask only those again.
- If the answers open new ambiguity, ask only the new questions, the same way. Never re-ask an answered question. Repeat until no BLOCKING question is open, then continue the skill.
- Answers hold for the rest of the session. A later round or a later skill reuses them and does not ask again.

# Question Round

Used by spec-interview (Steps 1 and 3), followup (Step 2 and decisions mid-work), spec-arch (keep or cut) and build-phase (blocking questions). It decides how questions reach the user, so every skill asks the same way.

## Before asking
Give every question these parts:
- Q<n>, numbered on from the last question in this session, BLOCKING or NON-BLOCKING, and a category from the skill's checklist.
- The question, and why it matters: how the answer changes the result.
- 2-4 options. Your recommendation comes first, with its reason and a confidence tag: [Certain], [Likely] or [Guessing].
- A default for when it stays unanswered: stop for BLOCKING, the recommended option for NON-BLOCKING unless you say otherwise.

Then print as text:
- "Resolved from code (challenge me if wrong)": item -> file:line
- "Recommended path": 2-4 lines on what happens if the user accepts every recommendation
- one count line, for example "11 questions: 5 blocking, 6 non-blocking, in 3 dialogs"

## Ask with AskUserQuestion
- Up to 4 questions per call, BLOCKING first, then NON-BLOCKING, grouped by category. Make the calls back to back, with no other work between them.
- question: `Q<n> [BLOCKING | NON-BLOCKING] <question> Why it matters: <one line>`. Name the default here when it is not the recommended option.
- header: the category, at most 12 characters.
- options: the recommended one first, its label ending in "(Recommended)" and its description giving the reason and the confidence tag. Every other description says what choosing it changes. Labels are at most 5 words. Do not add an "Other" option: the picker adds one for typed answers, so a question that needs a name, number or date still offers 2-4 likely values.
- multiSelect only when the options do not exclude each other.

## Fallback: text, then stop
If AskUserQuestion is unavailable, fails or comes back with no answers, print every open question in this format, then STOP:

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
- An unanswered BLOCKING question means do not proceed: ask only those again.
- If the answers open new ambiguity, ask only the new questions, the same way. Never re-ask an answered question. Repeat until no BLOCKING question is open, then continue the skill.

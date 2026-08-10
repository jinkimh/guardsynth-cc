# Repository Instructions

These behavioral guidelines reduce common coding-agent mistakes. Merge them
with project-specific instructions when needed. They intentionally favor
caution over speed; use judgment for trivial tasks.

## 1. Think Before Coding

Do not assume or hide confusion. Surface assumptions and tradeoffs before
implementing:

- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them instead of choosing silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop, name what is confusing, and ask.

## 2. Simplicity First

Write the minimum code that solves the requested problem. Do not add speculative
work:

- Add no features beyond what was asked.
- Do not introduce abstractions for single-use code.
- Do not add flexibility or configurability that was not requested.
- Do not add error handling for impossible scenarios.
- If 200 lines could be 50, rewrite and simplify.
- Ask: "Would a senior engineer say this is overcomplicated?" If so, simplify.

## 3. Surgical Changes

Touch only what the task requires, and clean up only changes introduced by the
task:

- Do not improve adjacent code, comments, or formatting.
- Do not refactor code that is not broken.
- Match the existing style, even if you would choose a different style.
- Mention unrelated dead code instead of deleting it.
- Remove imports, variables, and functions made unused by your own changes.
- Do not remove pre-existing dead code unless asked.
- Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

Define verifiable success criteria and iterate until they are satisfied.
Translate requests into concrete checks, for example:

- "Add validation" becomes "Write tests for invalid inputs, then make them pass."
- "Fix the bug" becomes "Write a test that reproduces it, then make it pass."
- "Refactor X" becomes "Ensure tests pass before and after."

For multi-step tasks, state a brief plan in this form:

1. `[Step]` -> verify: `[check]`
2. `[Step]` -> verify: `[check]`
3. `[Step]` -> verify: `[check]`

Strong success criteria support independent execution. If the criteria are weak
or amount only to "make it work," clarify them before implementation.

These guidelines are working when diffs contain fewer unnecessary changes,
solutions avoid needless complexity, and clarifying questions happen before
implementation rather than after mistakes.

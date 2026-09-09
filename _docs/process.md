# Process

Work is tracked as GitHub issues in
[cancinoray/shared-household-manager](https://github.com/cancinoray/shared-household-manager/issues),
one at a time. The issues mirror the tasks in `_docs/backlog.md`.

## Ground rules

- One issue at a time, in roughly the order given by `_docs/backlog.md`.
  Respect the dependency table there before picking the next one.
- The role working a step reads the issue's acceptance criteria before
  starting it and again before ending it.
- The engineer commits regularly, using the existing `Task #<n>: <summary>`
  style for commit subjects.
- Do not put GitHub closing keywords (`Closes #<n>`, `Fixes #<n>`) in commit
  messages. Commits land straight on `main`, so a keyword would auto-close the
  issue before QA has passed it. The orchestrator closes issues explicitly
  (see Lifecycle, step 6).

## Roles

Each role runs as a subagent with its own brief:

- **PM** — grooms an issue before anyone implements it. Follows
  `_docs/team/pm.md`.
- **Engineer** — implements one groomed issue. Follows
  `_docs/team/software-engineer.md`.
- **QA** — checks the result against the acceptance criteria and posts a
  PASS/FAIL verdict. Follows `_docs/team/qa-engineer.md`.

## Orchestrator

The main session is the orchestrator. It launches the PM, the engineer, and QA
as subagents and hands the issue from one to the next. It does not groom,
implement, or test itself.

## Lifecycle

1. Pick the next open issue from the backlog (`_docs/backlog.md` order, with
   its dependencies already closed).
2. PM grooms it — rewrites it to `_docs/task-template.md` with checkable
   acceptance criteria.
3. Engineer implements it, writes tests, commits, and leaves the issue open
   with a comment describing what they did.
4. QA verifies it against the acceptance criteria and posts `## QA: PASS` or
   `## QA: FAIL` as an issue comment, including the test command and its
   result.
5. On FAIL, go back to step 3 with the QA comment as the input. If the FAIL is
   about the acceptance criteria themselves, go back to step 2.
6. On PASS, the orchestrator closes the issue from the command line:

   ```sh
   gh issue close <number> --comment "QA PASS — <link to the QA comment>"
   ```

7. Repeat until the backlog is empty.

## Rules

- Never skip step 2. An issue is not ready to implement until a PM has groomed
  it.
- The engineer does not close the issue and does not use closing keywords in
  commits.
- QA does not change code. Its only output is a PASS/FAIL comment.
- Only the orchestrator closes an issue, and only after QA has posted PASS.

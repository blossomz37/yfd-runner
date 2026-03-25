# AGENTS.md

## Purpose
This file defines how agents should operate in this repository: how to orient, what to read first, how to scope work, when to ask, how to validate changes, and how to leave a clean handoff.

## Core operating principles
- Work in small, testable, reviewable units.
- Treat specs and project documentation as authority.
- Keep changes tightly scoped to the requested task.
- Surface uncertainty early.
- Prefer clear answers over performative narration.
- Stop loops early and report cleanly.

## Authority and context
Before making changes, review the repo’s authority documents and local conventions.

Priority order:
1. `AGENTS.md`
2. `README.md`
3. `SPEC/` and related spec or backlog documents
4. Project configuration files
5. Existing code patterns in nearby files

Rules:
- Treat spec documents as constraints.
- If the spec says something is deferred, leave it deferred.
- If the spec is silent on a meaningful decision, ask before inventing.
- If documentation and code disagree, flag the conflict explicitly.

## Broad order of operations
1. **Orient**
   - Check `git status`, recent commits, and any uncommitted changes.
   - Determine what state the previous session left behind.

2. **Read authority documents**
   - Read `README.md`, `SPECS/`, backlog notes, and any session or handoff docs.
   - Build against current assumptions, not stale ones.

3. **Validate current state**
   - Run the relevant tests, lint checks, and startup commands before planning new work.
   - Confirm whether the codebase is currently clean or already broken.

4. **Plan the work unit**
   - Define one bounded task with a clear done signal.
   - Example done signals: tests pass, endpoint returns expected shape, UI renders correctly, bug is reproduced and fixed.

5. **Check parallelism boundaries**
   - Parallelize only when tasks touch separate directories or clearly separate systems.
   - Keep tightly coupled areas single-threaded.
   - Avoid concurrent edits to shared files, config, schemas, or shared state modules.

6. **Execute**
   - Make the change.
   - Prefer existing patterns over new abstractions unless the task requires them.

7. **Test and repair**
   - Run relevant tests, lint, type checks, and real usage checks.
   - Fix failures in a controlled loop.

8. **Commit**
   - Make one clean commit per logical change.
   - Use a precise commit message.
   - Do not bundle unrelated work.

9. **Update authority documents**
   - If the work changes behavior, scope, API surface, workflow, or assumptions, update the relevant docs.

10. **Write handoff if ending**
   - Record:
     - what was done
     - what remains incomplete or broken
     - what should happen next

## Scope control
Scope discipline is mandatory.

Rules:
- Complete the requested task before starting adjacent work.
- Treat adjacency as a note, not permission.
- Log discovered follow-up work for later instead of folding it into the current task.
- Keep one commit focused on one logical change.
- Do not expand scope silently.

Ask before:
- adding a new endpoint
- changing a data model or schema
- introducing a new dependency
- changing architecture
- changing public API behavior
- modifying specs or backlog in a way that changes project direction
- implementing a feature mentioned in docs but not requested in the current task

When checking in, be brief and concrete:
- “The spec mentions X, but the current task is Y. Should I include X now or stay focused on Y?”

## Communication style
- Lead with the answer, then explain.
- Be direct and concise.
- Match the user’s register and technical depth.
- Flag uncertainty honestly.
- Report facts, decisions, and blockers clearly.
- Do the work; avoid narrating your process.

Preferred style:
- “I found the validation bug. It comes from X. I fixed it in Y and added a test.”

Avoid:
- filler enthusiasm
- long preambles before the conclusion
- bluffing
- “Let me think”
- “I will now”
- play-by-play narration

## Parallelism and subagents
Use subagents only when task boundaries are clean.

Safe parallelism:
- separate directories
- separate features with no shared files
- backend/frontend split with minimal coupling

Unsafe parallelism:
- shared config files
- shared schemas or types
- shared state modules
- tightly coupled core files
- overlapping ownership of the same files

Rule:
- If two agents may write to the same file, keep the work single-threaded.

## Validation rules
Before considering work complete:
- run the relevant test suite or targeted tests
- run linting and formatting as appropriate
- run type checks where applicable
- verify real behavior when relevant
- confirm the requested task is actually complete

Favor targeted validation first, then broader validation as needed.

## Loop safeguards
Agents do not reliably self-detect wasted motion. Use structural safeguards.

### Retry caps
- Max 3 repair attempts per failing check.
- If still failing after 3 attempts, stop and report the unresolved issue.

### Repeated edit detection
- Max 2 edits to the same file for the same reason.
- If a third edit would partially revert the earlier state, stop and flag a likely contradiction.

### Duplicate error detection
- If the same command returns the same error twice, do not run it a third time unchanged.
- Change approach or stop and report.

### Tool-call awareness
Use tool calls as a practical loop heuristic.
- If a small task is consuming far more tool calls than expected, pause and reassess.
- If progress is unclear after extended tool use, report status and proposed next step.

### Scope expansion prevention
- No opportunistic extra work after the assigned task is complete.
- After commit and verification, stop.
- Record follow-up items instead of starting them.

### Contradiction detection
- If two instructions, checks, or configs conflict, stop and surface the conflict.
- Do not oscillate between incompatible states.

## Commit discipline
- One logical change per commit.
- Keep commits reviewable.
- Do not mix refactor, feature work, and incidental cleanup in one commit unless the task explicitly requires it.
- Verify before commit when possible.
- After commit, run post-commit verification if that is part of the repo workflow, then end the work unit.

## Documentation updates
Update docs when the work changes:
- behavior
- API surface
- setup steps
- workflow
- assumptions
- file structure
- known limitations

Potential update targets:
- `README.md`
- files under `SPECS/`
- backlog or task docs
- handoff/session summary docs

## Handoff format
If ending the session, leave a short handoff with:
- **Done:** completed work
- **Open:** unresolved issues, failures, or risks
- **Next:** the recommended next task
- **Notes:** any context the next agent should know before starting

## Default decision rule
When in doubt:
1. reread the local docs
2. prefer the narrower scope
3. validate current state
4. ask before making impactful decisions
5. leave the repo in a clean, understandable state
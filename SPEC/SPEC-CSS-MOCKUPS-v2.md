# YFD Studio Mockup Revision Brief

Purpose: concrete punch list for the current revision of `SPEC-CSS-MOCKUPS.html`

Status:

- Option C-focused mockup v2 implemented
- Options A and B reduced to compact reference cards
- four primary Option C screens now define the working direction

## Goal

The next pass should stop behaving like an unresolved three-way comparison and start behaving like a focused product mockup for the selected direction:

- `Option C: Hybrid Editorial Console`

The revised mockups should:

- stay grounded in the actual repo structure
- emphasize review and authoring workflows over dashboard spectacle
- preserve operational clarity without drifting into generic SaaS admin patterns
- show how prompts, outputs, validation, and run state coexist in one coherent system

## Keep from Gemini

- command palette as a first-class utility surface
- run cards with clear status, chapter, and progress cues
- chapter-step execution matrix as the core run-status view
- persistent right-side inspector/context rail
- split template editor with source on the left and live preview on the right
- restrained warm-neutral shell with stronger structure in operational zones

## Reject or Tone Down

- the dark KPI-heavy `Pipeline Pulse` card
- broad nav breadth with placeholder screens
- generic mock data that does not match repo naming
- visually loud motion or status glow
- any layout where telemetry outranks reading and review

## Priority Changes to `SPEC-CSS-MOCKUPS.html`

### 1. Make Option C the center of gravity

Status: complete

- keep Options A and B only as compact reference summaries, or move them below the main selected mockups
- give most of the page real estate to `Option C`
- update the intro so the page no longer reads like an unresolved comparison

### 2. Replace generic Option C content with real product flows

Status: complete

Replace the single abstract Option C screen with focused slices:

1. Runs dashboard
2. Run detail / chapter review
3. Template editor + preview
4. Validation failure / rerun state

### 3. Make run detail review-first, not KPI-first

Status: complete

- keep the execution matrix near the top
- make the center panel primarily about output review
- demote metrics and logs into secondary panels
- reserve the largest reading surface for rendered output, diff, candidate compare, or validation feedback

Target hierarchy:

1. current chapter and step
2. current output
3. validation / review state
4. available next actions
5. supporting operational details

### 4. Use repo-grounded labels and files

Status: complete

Use real names from this repo:

- templates: `01-plan.j2`, `02-draft.j2`, `04-edit-style.j2`, `05-edit-craft.j2`, `06-final.j2`
- run ids such as `partial_ch2_20260319`
- directories:
  - `yfd-runner/templates/`
  - `yfd-runner/models/`
  - `yfd-runner/state/`
  - `yfd-runner/rendered/`
  - `yfd-runner/output/`

Avoid invented labels that make the mockup feel detached from the workspace.

### 5. Increase review-surface realism

Status: complete

Show actual review UI, not just inspector summary text:

- rendered-output reading surface
- candidate compare, diff, or validation annotations
- actions:
  - `Approve`
  - `Rerun`
  - `Add steering note`
  - `Branch run`
  - `Open rendered prompt`

### 6. Reduce nav breadth unless a screen is actually designed

Status: complete

For mockup purposes, prioritize:

- `Runs`
- `Templates`
- `Models`
- `Outputs`

Include `Intake` only if a real worksheet or dossier import screen is mocked.

## Implemented Screen Set for Mockup V2

### A. Runs Dashboard

Implemented:

- command palette hook
- active run cards
- quick actions for create and resume
- repo-grounded run ids and step labels

Must include:

- run cards
- status chips
- chapter/step summaries
- create run / resume run action
- command palette entry point

Should not include:

- oversized KPI widgets

### B. Run Detail / Chapter Review

Implemented:

- execution matrix
- large review surface for candidate output
- validation summary and next actions
- secondary operational log panel

Must include:

- chapter execution matrix
- selected chapter and step context
- large reading surface for current candidate output
- validation summary
- actions: approve, rerun, add note, branch

Logs are useful here, but they should remain visually secondary.

### C. Template Editor + Preview

Implemented:

- repo-grounded template names
- source and preview split
- rendered context and save state
- selected run and step indicators

Must include:

- left source pane
- right rendered preview pane
- template identity and save state
- preview / diff / save actions
- context indicators tied to the selected run and step

### D. Validation Failure / Recovery

Implemented:

- failure reason summary
- offending output snippet
- rendered prompt reference
- recovery actions including rerun, force, and manual inject

Must include:

- failed validation summary
- failure reason category
- offending output or snippet
- actions:
  - `Rerun`
  - `Force`
  - `Inject manual content`
  - `Inspect rendered prompt`

## Visual Rules

- keep the shell calm and slightly warm-neutral
- keep document and output surfaces brighter and roomier than operational panels
- use serif sparingly for major titles or reading surfaces only
- use monospace only where it improves file, token, step, or template legibility
- use state color for meaning, not decoration

Avoid:

- bright blue as the dominant identity
- a dark hero metrics card dominating the page
- decorative empty-state design that distracts from core workflows

## Mapping from Current `SPEC-CSS-MOCKUPS.html`

Keep and evolve:

- Option C sidebar/navigation structure
- Option C editor + inspector split
- review rail concept

Replace:

- Option C generic “Output Inspector” summary copy
- Option C abstract stat row
- any copy that explains the concept instead of demonstrating the workflow

Compress or demote:

- full-size Option A and Option B treatment

## Acceptance Criteria

The next mockup pass is successful if:

- a new viewer can tell quickly that Option C is the selected direction
- the main screens feel like a tool for prompts, runs, outputs, and review
- the run-detail screen gives more space to reading and decision-making than to telemetry
- the template editor looks grounded in the actual repo structure
- the mockups are specific enough to drive implementation priorities

## Remaining Follow-Up

- if needed, add a dedicated Intake mockup rather than implying it in navigation
- if implementation starts soon, derive a component inventory from the new HTML screens
- if the screens expose token or spacing gaps, update `SPEC-CSS.md` to capture them explicitly

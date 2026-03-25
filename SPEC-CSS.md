# YFD Studio — CSS / Visual System Spec

**Purpose:** High-level styling directions for the YFD Studio web app  
**Status:** Direction selected, pending token-level specification  
**Scope:** Visual system, layout language, component styling approach, and implementation baseline

---

## 1. What This Document Is

This document now locks the high-level visual direction for v1.

It records the selected styling direction for YFD Studio and keeps the rejected alternatives for reference so the product can:
- feel polished and intentional
- support dense writing-tool workflows
- stay readable during long sessions
- avoid looking like a generic admin dashboard

The goal is to give implementation a clear visual baseline before detailed token and component work begins.

---

## 2. Product Context

YFD Studio is not a marketing site. It is a working tool for:
- editing prompts
- editing model configs
- importing story dossiers
- inspecting runs
- reviewing outputs
- managing long-running generation loops

That means the CSS system needs to optimize for:
- information density
- calm long-session readability
- clear status signaling
- strong editor ergonomics
- predictable component behavior

---

## 3. Design Goals

- Make the app feel editorial and technical at the same time.
- Support heavy text workflows without visual fatigue.
- Keep navigation and progress state obvious.
- Make “safe to continue / warning / failed / pending review” instantly legible.
- Ensure the app works well on laptop screens first, with tablet support second.

---

## 4. Core Visual Requirements

Any CSS direction should support:
- three-pane layouts on desktop
- stacked layouts on narrow screens
- code/editor surfaces distinct from reading surfaces
- durable typography for long Markdown/YAML/Jinja sessions
- consistent spacing and sizing tokens
- light motion only where it helps orientation
- explicit color tokens for job state, validation state, and review state

---

## 5. Considered Styling Directions

Selected direction: `Option C: Hybrid Editorial Console`

The other options remain here as contrast, so the decision stays legible.

### Option A: Editorial Workbench

Character:
- restrained
- text-first
- premium but quiet
- closer to a writing studio than a dashboard

Visual traits:
- warm neutrals rather than stark grayscale
- strong serif or literary accent headings paired with a practical UI sans
- soft borders, low-glare panels, layered paper-like surfaces
- modest color used mainly for state and focus

Strengths:
- fits the writing-product identity well
- makes long-form content feel important
- avoids “internal tool” blandness

Risks:
- can become too soft or precious
- may under-signal technical controls if not balanced carefully

Best use:
- if the product wants to feel like a serious authoring environment first

### Option B: Precision Control Room

Character:
- crisp
- technical
- denser
- oriented around operations and traceability

Visual traits:
- cooler neutrals
- sharper borders and segmentation
- compact status chips and structured panels
- grid-forward layout with explicit hierarchy

Strengths:
- ideal for progress monitoring and dense metadata
- easier to make states and controls unambiguous
- naturally fits prompt/model/run management

Risks:
- can slide into generic ops-dashboard styling
- may feel too cold for a creative-writing tool

Best use:
- if the product emphasizes pipeline control and inspection over authoring atmosphere

### Option C: Hybrid Editorial Console

Character:
- balanced
- technical underneath, editorial on the surface
- probably the strongest default direction

Visual traits:
- calm neutral base
- elevated content panes for writing and reading
- more structured sidebars and control panels
- subtle visual distinction between authoring, review, and execution areas

Strengths:
- fits both prompt engineering and manuscript workflow
- allows technical controls without losing warmth
- most adaptable as the product grows

Risks:
- requires discipline to avoid becoming visually inconsistent
- needs a clear token system so “editorial” and “console” do not clash

Best use:
- if the app needs to serve both creative and operational use cases equally well

---

## 6. Selected Initial Direction

Chosen direction: `Option C: Hybrid Editorial Console`

Decision recorded: `March 24, 2026`

Reasoning:
- YFD Studio needs stronger operational clarity than a pure writing app
- but it also needs more atmosphere and readability than a typical internal tool
- the product has both editor surfaces and run-control surfaces, so a hybrid system is the safest long-term choice

Practical interpretation:
- content panes should feel calm and reading-friendly
- sidebars, inspectors, and status rails should feel structured and precise
- typography should make prompts and prose feel deliberate, not generic

Implementation implications:
- the app shell should read as a quiet technical frame, not a decorative canvas
- authoring and reading surfaces should feel slightly elevated from the shell
- operational surfaces should use tighter spacing and clearer segmentation than document surfaces
- state color should be explicit and disciplined, with hierarchy coming mainly from layout, tone, and typography

---

## 7. CSS Implementation Options

### Option 1: Tailwind + CSS Variables

Approach:
- use Tailwind for layout, spacing, and utility-level composition
- use CSS variables for design tokens
- keep complex component styling in co-located CSS modules where needed

Strengths:
- fast implementation
- easy consistency if tokenized well
- good for iterative product work

Risks:
- can become noisy if utilities are overused
- easy to lose visual cohesion without a strong token layer

Best use:
- best default if speed and flexibility matter most

### Option 2: CSS Modules + Design Tokens

Approach:
- use CSS modules for component styling
- define a global token system in root variables
- keep layout and component styling more explicitly authored

Strengths:
- cleaner visual authorship
- easier to reason about component appearance
- avoids utility-class sprawl

Risks:
- slower to build and iterate
- requires more upfront discipline

Best use:
- if visual polish and maintainability are prioritized over speed

### Option 3: Tailwind for Layout, Modules for Surfaces

Approach:
- Tailwind handles grid, flex, spacing, breakpoints
- CSS modules handle panel styles, typography systems, and special components
- tokens live in global CSS variables

Strengths:
- good compromise between speed and design control
- likely the best fit for this product

Risks:
- two styling systems require clear rules
- team must stay consistent about what belongs where

Best use:
- recommended implementation path for v1

---

## 8. Token Categories

The CSS system should define tokens for at least:
- color
- typography
- spacing
- radius
- shadow
- border
- motion
- z-index
- editor sizing
- status state colors

### Suggested state token groups

- `success`
- `warning`
- `error`
- `info`
- `running`
- `pending`
- `review_required`
- `approved`
- `rejected`

---

## 9. Layout System

### Primary desktop layout

Preferred structure:
- left sidebar for navigation and run selection
- main workspace for editors, prompts, or outputs
- right inspector rail for metadata, validation, and actions

This layout matches the product’s actual needs:
- navigation is persistent
- the main content gets the largest area
- metadata and actions remain visible without dominating the page

### Narrow-screen behavior

On smaller widths:
- collapse right rail into tabs or drawers
- keep left nav collapsible
- stack editor and preview panes vertically

### Panel behavior

Panels should support:
- sticky headers
- independent scroll regions
- clear resizing affordances if implemented
- strong visual distinction between editable and read-only regions

---

## 10. Surface Types

The app will likely need a small number of clearly distinct surface types.

### App shell surface

Used for:
- navigation
- sidebars
- top-level framing

Should feel:
- stable
- low-noise
- structurally clear

### Editor surface

Used for:
- Jinja templates
- YAML model configs
- worksheet text
- manual output edits

Should feel:
- precise
- low distraction
- clearly interactive

### Reading surface

Used for:
- rendered prompts
- chapter outputs
- edit reports
- dossier previews

Should feel:
- comfortable for long reading
- more document-like than control-like

### Status / control surface

Used for:
- run state
- warnings
- actions
- progress details

Should feel:
- compact
- explicit
- operational

---

## 11. Typography Options

### Option A: UI Sans + Editorial Serif Accent

Example direction:
- UI: a practical sans
- headings or document titles: a literary serif
- editors remain monospaced where appropriate

Strengths:
- strong identity
- helps distinguish product chrome from document content

Risks:
- can become overdesigned if serif use is too broad

### Option B: Refined Sans-Only System

Example direction:
- one primary sans with strong weight and size discipline
- monospace for code/editor contexts

Strengths:
- simpler
- cleaner
- easier to scale

Risks:
- may feel more generic unless the rest of the system is strong

### Recommendation

Start with:
- one strong sans for the application UI
- one monospace for editor surfaces
- optional restrained serif only for large section titles or manuscript-facing headings

This keeps the system controlled while preserving the option for more editorial character later.

---

## 12. Color Strategy Options

### Option A: Warm Neutral Base

Character:
- softer
- more author-facing
- easier on the eyes for long reading

Good for:
- Hybrid Editorial Console
- editorial surfaces

### Option B: Cool Neutral Base

Character:
- sharper
- more technical
- clearer operational feel

Good for:
- Precision Control Room
- denser monitoring surfaces

### Recommendation

Use a warm-neutral or near-neutral base, then reserve stronger colors for:
- active focus
- running jobs
- warnings
- validation errors
- review-required states

Avoid relying on saturated color as the main source of hierarchy.

---

## 13. Motion and Interaction

Motion should be minimal and purposeful.

Use motion for:
- panel entrance
- status transitions
- loading/progress continuity
- expanding inspectors or drawers

Avoid:
- decorative motion loops
- aggressive hover animation
- long easing on high-frequency interactions

A writing tool benefits more from stability than spectacle.

---

## 14. Component Families That Need Consistency

The first CSS pass should define reusable patterns for:
- buttons
- icon buttons
- tabs
- chips and badges
- alerts
- form fields
- dropdowns
- command rows
- cards/panels
- split panes
- table/grid rows
- diff blocks
- editor headers
- status timelines

The biggest visual risk is inconsistent treatment between:
- “editing” components
- “reviewing” components
- “running” components

These should be unified by shared tokens and panel rules.

---

## 15. Accessibility and Usability Baselines

Any chosen CSS direction should maintain:
- strong text contrast
- visible focus states
- keyboard-friendly controls
- readable line length in prose views
- scalable text without layout breakage
- color-independent status communication where possible

Status should not rely on color alone. Shape, label, and iconography should reinforce meaning.

---

## 16. Chosen Baseline

The implementation baseline is:

- visual direction: `Hybrid Editorial Console`
- implementation model: `Tailwind for layout + CSS modules for surfaces/components`
- token system: global CSS variables
- typography: strong sans + monospace, serif only as a restrained accent
- color base: warm neutral with explicit state tokens

This is the best balance of:
- speed
- polish
- maintainability
- product fit

---

## 17. Open Questions

- Should the app support both light and dark themes in v1, or launch with one mode only?
- How much visual distinction should there be between prompt-editing and manuscript-reading surfaces?
- Should the right rail feel like an inspector drawer or a permanent control column?
- How much of the visual character should come from typography versus panel styling?
- Do we want resizable panes in v1 or fixed responsive breakpoints only?

---

## 18. Suggested Next Step

Now that the direction is chosen, the next CSS deliverable should be one of:
- a design-token spec
- a wireframe + layout spec
- a component inventory with states

The best next step is probably a design-token spec, because it would force the visual system into something implementable.

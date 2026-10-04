# Frontend design system

## Product direction

The interface is designed as a calm evidence workspace rather than a generic AI chat. The visual
hierarchy gives source management, answer reading, and citation verification distinct but connected
areas. Warm neutral surfaces reduce glare during long-form reading, restrained emerald communicates
primary action and readiness, and the warm evidence accent is reserved for citations.

## Typography

Typography is locale-aware at the route layout:

- English uses the Inter variable font.
- Persian uses the Vazirmatn variable font, a mature open-source Persian UI typeface with clear
  numerals, punctuation, and multiple interface weights.
- `next/font` downloads both fonts at build time and self-hosts the emitted assets. Browsers do not
  depend on Google Fonts or another public font CDN at runtime.
- The active locale applies only its font variable. Mixed-direction user content still uses
  `dir="auto"` at content boundaries.

Persian has its own heading, body, and reading line heights. Letter spacing is never tightened for
Persian because Arabic-script shaping needs natural connections and word rhythm.

## Foundations

The global stylesheet owns semantic tokens for:

- canvas, surface, text, border, action, evidence, feedback, and status colors;
- a restrained fluid type scale;
- a four-pixel spacing grid;
- control, card, panel, and pill radii;
- low-elevation panel, composer, and overlay shadows;
- control heights, readable measures, workspace dimensions, motion, and focus treatment.

Feature styles consume these semantic tokens. Raw color values and ad-hoc elevation do not belong in
feature modules. This keeps contrast fixes and visual changes centralized.

## Layout rules

Navigation, product introduction, authentication, account controls, and the document workspace share
one `78rem` content grid. The hero is intentionally compact so the primary task remains visible on a
desktop viewport. Authentication uses a balanced copy/form composition, while the active workspace
uses a stable source column and a flexible answer column.

At tablet widths, the workspace and onboarding compositions become single-column. On small screens,
large outer panel decoration is removed so content uses the available width; evidence becomes a fixed
full-viewport dialog. Logical CSS properties preserve the same spatial system for RTL and LTR.

## Interaction and accessibility

- Interactive controls share minimum heights and visible two-layer focus treatment.
- Hover, active, pending, disabled, error, and success states remain visually distinct.
- Status never depends on color alone.
- Motion is short and functional and is disabled when reduced motion is requested.
- Form labels remain visible; placeholder text is supplementary.
- Reading widths and line heights are tuned separately from compact UI metadata.

Visual changes require Persian and English checks at desktop and mobile widths. Automated lint,
type-check, test, and production-build gates remain mandatory but do not replace visual inspection.

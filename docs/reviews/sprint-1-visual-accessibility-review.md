# Sprint 1 visual and accessibility review

- Date: 2026-09-24
- Browser: installed Google Chrome, headless DevTools device emulation
- Pages: `/fa` and `/en`
- Data state: active collection, ready TXT source, completed grounded answer, citation button,
  open evidence dialog

## Viewport matrix

| Locale | Viewport | `lang` / `dir` | Client width | Scroll width | Result |
|---|---:|---|---:|---:|---|
| Persian | 1440 × 1000 | `fa` / `rtl` | 1440 | 1440 | Pass |
| English | 1440 × 1000 | `en` / `ltr` | 1440 | 1440 | Pass |
| Persian | 390 × 844 | `fa` / `rtl` | 390 | 390 | Pass |
| English | 390 × 844 | `en` / `ltr` | 390 | 390 | Pass |

The mobile evidence panel initially inherited the workspace's absolute position, so opening a
citation after scrolling could place its header outside the viewport. The final implementation uses
a full-viewport fixed dialog on mobile, keeps the close control visible, supports Escape, traps its
single focusable control, and restores focus to the citation trigger.

## Contrast evidence

Calculated WCAG contrast ratios for final semantic token pairs:

| Pair | Ratio |
|---|---:|
| Primary text / surface | 16.21:1 |
| Secondary text / surface | 6.38:1 |
| Tertiary text / surface | 4.76:1 |
| White / action | 6.76:1 |
| Citation text / citation-soft | 7.26:1 |
| White / citation | 6.36:1 |
| Success text / success-soft | 6.49:1 |
| Warning text / warning-soft | 6.73:1 |
| Danger text / danger-soft | 6.80:1 |
| Info text / info-soft | 7.39:1 |

All normal-text pairs exceed WCAG 2.2 AA's 4.5:1 requirement. Focus uses a two-layer ring that is
visible against both the ivory canvas and controls. Statuses include text and a dot; color is not the
only signal.

## Interaction checks

- Collection restoration and change action remain clear in both directions.
- Drag/drop has an equivalent labeled file button.
- Upload exposes a labeled progressbar, percentage, and cancel action.
- Processing/failed/ready states use live regions and actionable localized copy.
- Chat stays disabled until a ready source exists.
- Enter submits and Shift+Enter inserts a line break.
- Streaming status, stop, retry, abstention, citations, and evidence source/page are distinct.
- Mixed Persian/English filenames and email/code fragments use `dir="auto"` where content direction
  can differ from page direction.
- Reduced-motion media rules disable spinner/transition motion.

This is a focused engineering review, not a full third-party assistive-technology certification.
VoiceOver/NVDA user testing remains appropriate before public beta.

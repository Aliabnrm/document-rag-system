# Sprint 2 visual design review

- Date: 2026-09-26
- Runtime: local Next.js development server in the Codex in-app browser
- Locales: Persian and English
- States: sign-in, authenticated empty account, collection onboarding, and active empty collection

## Viewport and typography checks

| Locale | Viewport | State | Result |
|---|---:|---|---|
| Persian | 1280 × 720 | sign-in and active collection | Pass |
| English | 1280 × 720 | sign-in, onboarding, and active collection | Pass |
| Persian | 390 × 844 | sign-in and full active collection | Pass |
| English | 390 × 844 | sign-in and onboarding | Pass |

The browser-computed Persian stack begins with `Vazirmatn` and the English stack begins with `Inter`.
At the 390px mobile override, the Persian document workspace had no horizontal page overflow. The
temporary viewport override was reset after inspection.

## Issues found and resolved

- The previous five-rem display heading dominated the desktop viewport. The final display scale is
  restrained and fluid, with a smaller Persian mobile override.
- Navigation, hero, account controls, and workspace previously used competing widths. They now share
  one content grid and logical inline alignment.
- Authentication copy and controls felt disconnected. They now form one balanced desktop composition
  and a direct single-column mobile flow.
- English authentication tab labels wrapped on mobile. Concise `Register` and `Reset` labels keep all
  three actions on one line without reducing the touch target.
- Panel radii and shadows were visually heavy. Smaller semantic radii and low-elevation shadows keep
  boundaries clear without making every area look like a floating card.
- Workspace actions previously formed a loose vertical group on desktop. They now share one compact
  action row and return to a readable stacked layout on mobile.
- Mixed-direction collection names and descriptions now establish their own direction.

## Responsive behavior

Desktop uses a stable source column and flexible question/answer column. Tablet moves those areas into
one column and allows document rows to use a two-column intermediate layout. Mobile removes redundant
outer card decoration, keeps controls at accessible heights, places evidence in a viewport dialog, and
preserves task order: account, collection, sources, then questions.

## Accessibility retained

The refactor preserves the existing WCAG 2.2 AA semantic color pairs, visible two-layer focus rings,
keyboard controls, labels, live regions, reduced-motion behavior, text-based statuses, and logical RTL
properties. This review is visual and engineering-focused; assistive-technology user testing remains a
recommended public-release activity.

Measured contrast for the changed foundation tokens remains above WCAG 2.2 AA: primary text on the
surface is `16.52:1`, secondary text is `6.95:1`, tertiary text is `4.88:1`, and white text on the
primary action is `7.33:1`. Existing evidence and status pairs remain between `6.36:1` and `7.39:1`.

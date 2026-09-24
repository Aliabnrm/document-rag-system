<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Document Q&A frontend rules

These rules specialize the repository contract for `frontend/`. Preserve the generated Next.js block above and consult the relevant installed Next.js guide before changing framework behavior.

## Source structure and boundaries

- Keep route files focused on routing, layout, metadata, and page composition.
- Put user capabilities under `src/features/<feature>/`; keep shared visual primitives under `src/components/ui/` and shared infrastructure under clearly named modules.
- Default to Server Components. Add `"use client"` at the smallest interactive boundary and document why state must be client-side when it is not obvious.
- Backend business rules, authorization, retrieval, prompt construction, and provider access never live in the frontend.
- Consume the backend through one typed API boundary. Validate unknown responses, normalize transport errors, and support cancellation.
- Represent remote state explicitly: idle, pending, success, empty, partial/streaming, and failure.

## Bilingual behavior

- All user-visible copy lives in localization messages; never hard-code English or Persian inside a component.
- Support `/fa` and `/en`, with correct `lang`, `dir`, metadata, number formatting, and locale-preserving navigation.
- Build with CSS logical properties so RTL is structural rather than a collection of overrides.
- Test mixed-direction content such as Persian prose containing filenames, URLs, numbers, citations, and code.
- Error text is actionable and user-safe in both languages.

## Design system and visual direction

The interface should feel calm, credible, precise, and approachable for non-technical users. Use progressive disclosure and one clear primary action per view. Avoid dashboard clutter, decorative AI gradients, excessive cards, and animation that competes with reading.

The existing ivory, charcoal, emerald, and warm citation accent are the baseline direction. Convert them into semantic tokens rather than scattering raw values:

```text
canvas/surface       warm neutral backgrounds
text/secondary       high-contrast charcoal hierarchy
brand/action         restrained emerald for primary actions and focus
citation/accent      warm accent for evidence references
success/warning/error/info  accessible semantic feedback
```

- Define color, typography, spacing, radius, shadow, motion, and breakpoint tokens centrally.
- Do not add arbitrary hex colors, pixel spacing, shadows, or component variants inside feature components.
- Verify normal text, large text, controls, focus rings, disabled states, and status colors against WCAG 2.2 AA. Color never carries meaning alone.
- Use a restrained radius and shadow scale. Visual hierarchy comes from spacing, typography, contrast, and alignment.
- Prefer readable line lengths, generous whitespace, and stable layouts while content streams.
- Motion is brief and functional; respect `prefers-reduced-motion`.

## Interaction requirements

- Every interactive element works with keyboard and exposes an accessible name and visible focus.
- Upload has drag/drop and button alternatives, validation, progress, cancellation where possible, processing stages, retry, and recovery guidance.
- Chat distinguishes user text, grounded answer, citations, streaming progress, insufficient evidence, retryable error, and disconnected state.
- Citation interaction identifies document and page and preserves reading context when opening evidence.
- Mobile layouts keep the question composer, status, and evidence access usable without horizontal scrolling.

## Verification

- Test user behavior and public component contracts; avoid snapshots as the primary proof.
- Add focused tests for locale routing, validated API responses, upload state, stream reduction, citations, and error recovery.
- Visually inspect affected screens in Persian and English at mobile and desktop widths.
- Run:

```bash
pnpm lint && pnpm typecheck && pnpm test && pnpm build
```

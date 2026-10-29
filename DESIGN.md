# DESIGN.md: Prompt Receipt

Single source of truth for how this project looks. The README and every asset in `assets/` follow it.

## Idea

The skill gives you an itemized bill for a chat. So the whole identity is a **thermal-paper receipt**: warm paper, mono type, dashed rules, one red stamp for the grade. Calm and a little funny, never alarming. The tool shames nobody; the design should feel like a shop receipt, not a warning dialog.

## Colour

Warm neutrals plus three signal colours. Every text pair below passes WCAG AA (4.5:1); ratios measured with the WCAG relative-luminance formula.

| Token | Light (paper) | Night | Used for | Contrast on its background |
|---|---|---|---|---|
| `paper` | `#F6F1E7` | `#15130F` | page and card background | n/a |
| `paper-edge` | `#E3DAC6` | `#2A2620` | card border, perforation shadow | decorative |
| `receipt` | `#FFFDF8` | `#1E1B16` | the receipt slip itself | n/a |
| `ink` | `#1D1B17` | `#F1EBDD` | titles, key numbers | 15.3:1 / 15.6:1 |
| `ink-muted` | `#5F594D` | `#B5AD9C` | captions, labels | 6.2:1 / 8.3:1 |
| `stamp` | `#B8321B` | `#FF7A5C` | cost share, grade stamp, kicker | 5.3:1 / 7.2:1 |
| `saved` | `#1B7048` | `#5FD29A` | "better prompt", rewrites | 5.4:1 / 9.9:1 |
| `warn` | `#8F5A0A` | `#E8B04A` | "what was missing" | 5.1:1 / 9.5:1 |

Rules
- Red means **cost**. Green means **the fix**. Amber means **what was missing**. Never swap them.
- Max one red element per region. The stamp is the loudest thing on a page.
- Assets ship with their own paper background, so they read the same in GitHub light and dark mode.

## Type

| Role | Family stack | Size | Weight |
|---|---|---|---|
| Title | `ui-sans-serif, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif` | 68 / 40 | 800 |
| Receipt text | `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` | 13 to 15 | 400, 700 for totals |
| Kicker | mono, caps, 3px tracking | 14 | 700 |

System fonts only: no font files, so SVGs stay tiny and render everywhere.

## Shape and space

- Cards: 20px radius, 1px `paper-edge` border.
- Receipt slip: square top, **zigzag bottom edge** (14px teeth, 8px deep). This is the one signature shape.
- Dashed rule: `stroke-dasharray: 5 4`, 1px, `ink-muted` at 55% opacity.
- Stamp: 3px ring, rotated about -14 degrees, no fill.
- Spacing steps: 8, 16, 24, 32, 64.

## Voice

Plain words, short sentences. Say what a prompt was missing and what to type instead. "Estimate" beats false precision. No jargon without a one-line explanation.

## README layout

1. Banner, badges, one-line pitch
2. What you get (table)
3. Example receipt (image)
4. Install and use
5. How it works (flow image)
6. What it flags (collapsible)
7. Honesty and privacy
8. Design language (palette image)

## Assets

| File | What |
|---|---|
| `assets/banner.svg` | hero, 1200x360 |
| `assets/receipt-example.svg` | full sample review, from the bundled `vague-fix-chat` test chat |
| `assets/how-it-works.svg` | four-step flow |
| `assets/palette.svg` | the tokens above as swatches |

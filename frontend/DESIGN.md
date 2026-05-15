# Frontend Design System

The cream canvas runs continuously through every section — there are no decorative dividers, no shaded section bands; only the 1px hairline beneath section eyebrows and footer column rules separate content blocks.

## Elevation & Depth

| Level | Treatment | Use |
|---|---|---|
| 0 — Flat | No border, no shadow | Default for canvas-on-canvas blocks, hero text, body sections |
| 1 — Hairline border | 1px solid {colors.hairline} | Marketing cards, pricing tier cards, doc sidebar items, footer column rules |
| 2 — Hairline soft | 1px solid {colors.hairline-soft} | In-card row divider between adjacent rows |
| 3 — Inverted dark code block | {colors.surface-dark} fill | Code samples inside doc cards — the system's only "elevated" surface uses color, not shadow |

The system has no drop-shadow elevation in marketing or product chrome. Cards sit flat on cream with thin olive borders. The single inverted moment is the dark code-block surface used inside doc article body cards.

### Decorative Depth
Depth comes entirely from illustration and the pastel callout band system, not from CSS effects:
- Hand-drawn hedgehog mascots — characters in various costumes (lab coat, terminal, lounge chair, magnifying glass, hammock, hat) scattered across pages as marginalia. Always rendered as flat color illustrations, never photographs.
- Pastel callout banners — {component.banner-tip-blue} / -green / -red / -purple soft tinted side-rail panels inside doc articles, each prefixed with an emoji icon (💡 ✅ ⚠️ 📘) and carrying tip/warning/note copy.
- Code blocks — full-width dark olive-charcoal panels on {colors.surface-dark} with white code text. The system's most cinematic surface, used inside white doc cards.
- Outline product icons in the doc sidebar — small rounded-square mini-illustrations (chart icon, funnel, session-replay icon) mark each major product section.

## Shapes

### Border Radius Scale

| Token | Value | Use |
|---|---|---|
| {rounded.none} | 0px | Sub-nav strip, footer, doc sidebar, primary nav — flat structural surfaces |
| {rounded.xs} | 2px | Inline <code> chips, micro-rule highlights |
| {rounded.sm} | 4px | Inline buttons, form inputs, micro chips |
| {rounded.md} | 6px | Marketing cards, pricing cards, doc cards, code blocks, every standard CTA |
| {rounded.lg} | 8px | Tab top corners (`6px 6px 0 0` on active tab) and rare large containers |
| {rounded.full} | 9999px | Pill chips and pill-style CTAs ("Get started — free" sticky CTA in nav) |

The radius vocabulary clusters around 4–6px for nearly everything; the only fully-rounded element is the pill-style sticky nav CTA and inline pill chips.

### Photography Geometry
There is no photography. Visual elements are limited to:
- Hedgehog character illustrations — flat-color cartoon hedgehogs ranging from ~80px (in-card mascot) to ~240px (hero illustration). Always at native aspect, never cropped to a frame.
- Outline product icons in the doc sidebar — 20–24px rounded-square illustrations.
- Inline emoji at 14–16px inside callout banners (💡 ✅ ⚠️ 📘) — used as functional iconography rather than decoration.
- Section illustrations on the home page — small hedgehog vignettes paired with each "Understand product usage" / "Build sticky habits" / "Test before launch" feature row.

## Components

> No hover states documented per system policy. Each spec covers Default and Active/Pressed only.

### Buttons

`button-primary` — the universal PostHog CTA
- Background {colors.primary} (yellow-orange), text {colors.on-primary} (deep olive), type {typography.button-md}, padding 8px 16px, height 40px, rounded {rounded.md}.
- Used for "Get started — free" (sticky top-nav CTA), "Sign up", "Try it free", "Subscribe" — every primary action.
- Pressed state lives in button-primary-pressed — background drops to {colors.primary-pressed}.

`button-secondary` — soft alternative on cream canvas
- Background {colors.surface-soft} (`#e5e7e0`), text {colors.ink}, type {typography.button-md}, padding 8px 16px, height 40px, rounded {rounded.md}.- "Talk to sales", "Read docs", "Watch demo" — second-tier actions paired with the yellow primary.

`button-tertiary` — ghost text button
- Background transparent, text {colors.ink}, type {typography.button-md}, padding 8px 12px, rounded {rounded.md}.
- Lowest-emphasis action: "See all docs →", "Browse all features".

`button-disabled`
- Background {colors.surface-soft}, text {colors.ash} — flat soft cream-gray.

### Tabs & Chips

`product-tab` + `product-tab-active` — major product section tabs
- Default: transparent background, text {colors.body}, type {typography.body-strong}, padding 8px 12px, rounded {rounded.md}.
- Active: background flips to {colors.surface-card} (white), text {colors.ink} — the tab card lifts off the cream canvas as the visual signal of selection.

`pill-tab` + `pill-tab-active` — compact filter pill
- Default: transparent background, text {colors.body}, type {typography.button-sm}, padding 6px 14px, rounded {rounded.full}.
- Active: background flips to {colors.ink}, text {colors.on-dark} — the chip flips fully inverted on selection.

`badge-uppercase` — text-only utility label
- Background transparent, text {colors.body} in {typography.utility-xs} (uppercase) — used as in-list category prefix ("FEATURE FLAG", "EXPERIMENT", "HEATMAP").

`badge-promo` — small inline pill chip
- Background {colors.accent-blue-soft}, text {colors.link-blue}, type {typography.caption-xs}, padding 2px 8px, rounded {rounded.full}.
- "New", "Beta", "Coming soon" pill labels overlaid on cards.

### Inputs & Forms

`text-input` + `text-input-focused`
- Default: background {colors.surface-card}, text {colors.ink}, 1px solid {colors.hairline}, type {typography.body-md}, padding 8px 12px, height 36px, rounded {rounded.md}.
- Focused: same surface; 2px solid {colors.accent-blue} border replaces the 1px hairline + a translucent {colors.focus-ring} outline.

`search-input` — utility search field (doc sidebar, "Ask PostHog AI")
- Same dimensions as text-input with a magnifier glyph at the left edge in {colors.mute}.

### Cards & Containers

`product-card` — marketing tile / feature card
- Container: background {colors.surface-card} (white), 1px solid {colors.hairline}, padding {spacing.xl} (24px), rounded {rounded.md}.
- Layout: small hedgehog illustration at top-left, {typography.heading-sm-mixed} title, {typography.body-sm} description, optional {component.button-tertiary} "Learn more →" link.

`doc-card` — doc article body card
- Container: background {colors.surface-doc} (`#fcfcfa` warm-white), 1px solid {colors.hairline}, padding {spacing.xl} (24px), rounded {rounded.md}.
- Carries article body sections, code blocks, callout banners, and tables inside doc pages.

`feature-tile` — small marketing feature tile
- Container: background {colors.surface-card}, 1px solid {colors.hairline}, padding {spacing.lg} (20px), rounded {rounded.md}.
- Used in 3-up or 4-up grids on home and workflows pages — paired with a small icon and a 1-line description.

`pricing-tier-card` — pricing plan card
- Container: background {colors.surface-card}, 1px solid {colors.hairline}, padding {spacing.xxl} (32px), rounded {rounded.md}.
- Layout: tier name in {typography.display-lg} (24px / 800 / -0.6px), large price + period, feature checklist with check-icon bullets, primary or secondary CTA at bottom.

`hedgehog-mascot-card` — feature card with margin-anchored hedgehog
- Same chrome as {component.product-card} but with a hand-drawn hedgehog illustration anchored in the right margin or top-right corner — the brand's signature card variant.

### Callout Banners

`banner-tip-blue` + `banner-tip-green` + `banner-tip-red` + `banner-tip-purple`
- Background {colors.accent-blue-soft} / {colors.accent-green-soft} / {colors.accent-red-soft} / {colors.accent-purple-soft}, text {colors.ink}, type {typography.body-md}, padding 16px 20px, rounded {rounded.md}.
- Each prefixed with an inline emoji icon (💡 / ✅ / ⚠️ / 📘) followed by an inline label and body copy.
- Only appear inside doc article body.The four-color callout family is the brand's information-architecture vocabulary for inline tips/warnings/info inside long-form documentation.

### Code

`code-block` — dark code sample inside doc card
- Container: background {colors.surface-dark} (deep olive-charcoal), text {colors.on-dark} in {typography.code-sm}, padding 16px 20px, rounded {rounded.md}.
- Syntax highlighting uses muted accent colors (blue for keywords, green for strings, purple for numbers) — never the bright accent colors used in callout banners.

`inline-code` — small inline <code> chip
- Background {colors.surface-soft}, text {colors.ink} in {typography.code-xs}, padding 2px 6px, rounded {rounded.xs} (2px).
- Used inside body prose to mark code snippets and identifiers.

### Navigation

`primary-nav`
- Background {colors.canvas} (cream — same as the page), text {colors.ink}, height 56px, type {typography.body-strong}, rounded {rounded.none}.
- Layout (desktop): PostHog wordmark + hedgehog logo at left, nav menu cluster ("Pricing · Docs · Community · Company"), right cluster with a search-glyph, "Login" link, and the always-yellow {component.button-primary} "Get started — free" pill anchored to the far right.

`sub-nav-strip` — secondary nav bar (under primary)
- Background {colors.surface-soft}, text {colors.body} in {typography.body-xs}, height 40px, rounded {rounded.none}.
- Sits directly below the primary nav on workflows / product pages with section anchor links and a contextual "Get started →" link at the right.

`doc-sidebar` — sticky doc-page left sidebar
- Background {colors.canvas}, text {colors.body} in {typography.body-xs}, width 240px, rounded {rounded.none}.
- Layout: search-input "Ask PostHog AI" at top, then a vertical list of section headers each with a small rounded outline-icon mini-illustration, then nested item links indented under the active header.

Top Nav (Mobile)
- Hamburger menu icon at left, PostHog wordmark + hedgehog at center, search + sticky yellow "Get started — free" CTA at right. Primary nav collapses into a full-height drawer that slides from the left.

### Footer

`footer-section`
- Background {colors.canvas}, text {colors.body} in {typography.body-xs}, padding 32px 24px, rounded {rounded.none}, with a 1px {colors.hairline} top rule.
- Layout: 6-column horizontal link grid (Product · Resources · Company · Community · Pricing · Legal), each column with a {typography.utility-xs} (uppercase) header and a vertical list of links in {typography.body-xs} {colors.body}.
- Bottom row: PostHog wordmark + small hedgehog illustration, copyright in {typography.caption-xs} {colors.mute}, social-icon row at far-right.

### Inline

`link-inline` — body-prose anchor link
- {colors.link-teal} (`#1078a3`) in body prose with no underline by default; underline appears on focus. The brand's primary inline link color.

## Do's and Don'ts

### Do
- Use {colors.canvas} (cream — `#eeefe9`) as the page body. Never substitute pure white as the canvas.
- Reserve {colors.primary} (yellow-orange) for the primary CTA pill only. The "Get started — free" treatment is the brand's anchor.
- Render the brand wordmark with the hedgehog illustration alongside it, not as a stand-alone wordmark. The hedgehog IS the brand identity.
- Use IBM Plex Sans Variable across every text role — body 400, emphasis 600/700, display 800.
- Stack content sections at {spacing.section} (80px) rhythm with no decorative dividers between them; let the cream canvas continue uninterrupted.
- Use {component.banner-tip-blue} / -green / -red / -purple only inside doc article body for tip/warning/note panels — keep marketing chrome out of the four-color callout family.
- Pair every code sample with the dark {component.code-block} surface; inline <code> chips use {component.inline-code} (cream surface-soft chip).
- Anchor a hedgehog mascot illustration in feature tile margins on home and workflows pages — the system's signature decoration.

### Don't
- Don't introduce drop shadows on cards. Cards sit flat on cream with thin olive borders only.- Don't add a second saturated chromatic CTA. Yellow-orange is the only loud color in the system.
- Don't replace the cream canvas with pure white or full-bleed dark hero bands. The cream is the brand.
- Don't use the four-color callout banner pastels (`{colors.accent-blue-soft}`, -green, -red, `-purple`) as marketing-card backgrounds. They belong to inline doc content only.
- Don't substitute the hedgehog illustration with a generic icon set. The character system is the brand.
- Don't use uppercase transform outside of {typography.heading-sm}, {typography.utility-xs}, and {typography.caption-xs}. Uppercase is reserved for eyebrows and footer category headers.
- Don't pad cards with 32px+ on all sides except for {component.pricing-tier-card}. Standard cards sit at 24px internal padding.

## Responsive Behavior

### Breakpoints

| Name | Width | Key Changes |
|---|---|---|
| ultrawide | 1920px+ | Content max-width holds at 1280px; outer gutters grow to ~80px |
| desktop-large | 1440px | Default — 4-up feature tile grid, 240px sticky doc sidebar visible |
| desktop | 1280px | Same layout with narrower outer gutters |
| desktop-small | 1024px | 4-up tiles collapse to 3-up; doc sidebar remains visible |
| tablet | 768px | 3-up tiles collapse to 2-up; doc sidebar collapses into a top accordion; primary nav becomes hamburger |
| mobile | 480px | Single-column everything; hero {typography.display-xl} scales 36px → ~28px |
| mobile-narrow | 320px | Section padding tightens to 32px |

### Touch Targets
All interactive elements meet WCAG AA (≥ 40×40px). {component.button-primary} and {component.button-secondary} sit at 40px height with 16px padding. {component.text-input} sits at 36px (just under AAA but above AA at this size). {component.pill-tab} is ~32–36px height with 14px padding extending to ~44px tappable via inline padding. Doc-sidebar items use 14px text with ~32px line-height + 6px vertical padding for ~44px tap rows.

### Collapsing Strategy
- Primary nav: desktop horizontal cluster → tablet hamburger drawer at 768px. The yellow "Get started — free" CTA stays visible at every breakpoint.
- Sub-nav strip: desktop horizontal anchor row → tablet horizontal scroll → mobile select dropdown.
- Marketing card grid: 4-up → 3-up → 2-up → 1-up at 1024, 768, and 480px; gutters drop from 16px to 12px on mobile.
- Pricing grid: 3-up → 2+1 → 1-up stacked at tablet and below.
- Doc layout: desktop 240px sidebar + 720px article → tablet sidebar collapses to a top accordion → mobile fully collapsed accordion.
- Footer: 6-up link columns → 3-up at tablet → 2-up at mobile.
- Section padding: {spacing.section} (80px) desktop → 64px tablet → 48px mobile.
- Hero headline: {typography.display-xl} (36px) at desktop, scaling to ~28px at mobile, line-height holding at 1.5.

### Image Behavior
The only "imagery" in the system is hand-drawn hedgehog illustrations rendered as inline SVG. They preserve their natural aspect at every breakpoint and scale via CSS width: auto; max-width: 100%. There is no responsive art-direction needed because there is no photography.

## Iteration Guide

1. Focus on ONE component at a time. Pull its YAML entry and verify every property resolves.
2. Reference component names and tokens directly (`{colors.primary}`, {component.button-primary-pressed}, `{rounded.md}`) — do not paraphrase.
3. Run npx @google/design.md lint DESIGN.md after edits — broken-ref, contrast-ratio, and orphaned-tokens warnings flag issues automatically.
4. Add new variants as separate component entries (`-pressed`, -disabled, `-focused`) — do not bury them inside prose.
5. Default body to {typography.body-md} (16px / 400 / 1.5); reach for {typography.body-strong} for emphasis; reserve {typography.display-lg} (24px / 800) strictly for marketing display moments.
6. Keep {colors.primary} scarce per viewport — at most one yellow-orange pill per fold.
7. When introducing a new component, ask whether it can be expressed with the existing card + 6px-radius + cream-canvas vocabulary before adding new tokens.The system's strength is that it almost never needs new ones.

## Known Gaps

- Mobile screenshots not captured — responsive behavior synthesizes PostHog's mobile pattern (hamburger drawer, single-column grid, doc sidebar accordion) from desktop evidence and the breakpoint stack.
- Hover states not documented by system policy.
- In-product app chrome (PostHog dashboard, charts, session replay player) not in the captured set — the marketing site is documented here, not the in-product analytics interface.
- Authenticated chrome (login modal, account dashboard, billing settings) not in the captured pages.
- Form validation states beyond the focused-state input not present in the captured surfaces.
- Marketing illustration set — the full library of hedgehog character poses is not enumerated here; specific poses (lab coat hedgehog, terminal hedgehog, hammock hedgehog) are noted as visible in screenshots but the full asset library is page-specific.

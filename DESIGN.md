---
name: Crux
description: An adaptive study companion whose session is a box of index cards, with what the tutor knows about you on the box's tabbed dividers.
colors:
  desk: "#e6e8ec"
  desk-dark: "#15171b"
  desk-deep: "#dfe2e7"
  desk-deep-dark: "#1b1d22"
  card: "#ffffff"
  card-dark: "#22252b"
  card-edge: "#cfd3da"
  card-edge-dark: "#2e323a"
  card-drop: "#c4c8d0"
  card-drop-dark: "#0b0c0e"
  card-learner: "#dbe6fb"
  card-learner-dark: "#1e2a44"
  card-learner-edge: "#b9cdf5"
  card-learner-edge-dark: "#2f4470"
  surface-raised: "#fbfaf7"
  surface-raised-dark: "#1f2126"
  ink: "#1b1b1a"
  ink-dark: "#ecebe6"
  ink-learner: "#1d4fc4"
  ink-learner-dark: "#8fb0ff"
  ink-marker: "#d8433a"
  ink-marker-dark: "#ff6a5e"
  ink-marker-text: "#b8352c"
  ink-marker-text-dark: "#ff6a5e"
  ink-marker-text-hover: "#94271f"
  ink-marker-text-hover-dark: "#c9463b"
  chart-bar-past: "#5a78c2"
  chart-bar-past-dark: "#5570ad"
  pencil: "#63635e"
  pencil-dark: "#a3a39c"
  rule: "#cbd6e3"
  rule-dark: "#262a33"
  rule-strong: "#aebccf"
  rule-strong-dark: "#363b47"
  accent-strong: "#1d4fc4"
  accent-strong-dark: "#3b63d6"
  accent-hover: "#173fa0"
  accent-hover-dark: "#a9c2ff"
  btn-fill-hover: "#173fa0"
  btn-fill-hover-dark: "#2f52b8"
  accent-soft: "#e0e7f4"
  accent-soft-dark: "rgba(143, 176, 255, 0.14)"
  accent-ring: "rgba(29, 79, 196, 0.35)"
  accent-ring-dark: "rgba(143, 176, 255, 0.45)"
  text-on-accent: "#ffffff"
  tab-focus: "#b8352c"
  tab-focus-dark: "#ff6a5e"
  tab-gaps: "#8a5a00"
  tab-gaps-dark: "#e6b450"
  tab-mastered: "#1f7a3f"
  tab-mastered-dark: "#5fcf8a"
  tab-level: "#63635e"
  tab-level-dark: "#a3a39c"
  tab-ink: "#ffffff"
  tab-ink-dark: "#141518"
  success-text: "#1d733b"
  success-text-dark: "#5fcf8a"
  error-text: "#b8352c"
  error-text-dark: "#ff6a5e"
typography:
  display:
    fontFamily: "Familjen Grotesk, system-ui, sans-serif"
    fontSize: "2.25rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Familjen Grotesk, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Familjen Grotesk, system-ui, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  session-topic:
    fontFamily: "Familjen Grotesk, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  subhead:
    fontFamily: "Familjen Grotesk, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 600
    lineHeight: "28px"
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Atkinson Hyperlegible Next, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.647
    letterSpacing: "normal"
  contents:
    fontFamily: "Atkinson Hyperlegible Next, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: "28px"
    letterSpacing: "normal"
  caption:
    fontFamily: "Atkinson Hyperlegible Next, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.647
    letterSpacing: "normal"
  label:
    fontFamily: "Atkinson Hyperlegible Next, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.647
    letterSpacing: "normal"
  mono:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: "28px"
    letterSpacing: "normal"
rounded:
  none: "0"
  control: "4px"
  tab: "5px"
  card: "6px"
spacing:
  card-pad-top: "0.55rem"
  card-pad-x: "0.9rem"
  card-pad-bottom: "0.7rem"
  card-gap: "0.75rem"
  divider-gap: "0.9rem"
  section-gap: "1.5rem"
  page-gap: "1.75rem"
  pitch: "28px"
components:
  card-tutor:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.card}"
    padding: "0.55rem 0.9rem 0.7rem"
  card-learner:
    backgroundColor: "{colors.card-learner}"
    textColor: "{colors.ink-learner}"
    typography: "{typography.body}"
    rounded: "{rounded.card}"
    padding: "0.55rem 0.9rem 0.7rem"
  card-check:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.card}"
    padding: "0.55rem 0.9rem 0.7rem"
  card-composer:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink-learner}"
    typography: "{typography.body}"
    rounded: "{rounded.card}"
    padding: "0.55rem 0.9rem"
  divider-tab:
    backgroundColor: "{colors.tab-focus}"
    textColor: "{colors.tab-ink}"
    typography: "{typography.label}"
    rounded: "5px 5px 0 0"
    padding: "0.15rem 0.6rem"
  divider-body:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink-learner}"
    typography: "{typography.body}"
    rounded: "0 6px 6px 6px"
    padding: "0.4rem 0.7rem"
  status-banner:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.caption}"
    rounded: "0 0 6px 6px"
    padding: "0.4rem 0.75rem"
  settings-tab:
    backgroundColor: "{colors.desk}"
    textColor: "{colors.pencil}"
    typography: "{typography.caption}"
    rounded: "6px 6px 0 0"
    padding: "0.5rem 1rem"
  settings-tab-active:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
  settings-sheet:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "0 6px 6px 6px"
    padding: "1.5rem 2rem 2rem"
  settings-section:
    backgroundColor: "{colors.desk-deep}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "1rem 1.25rem 1.25rem"
  sidebar-row-current:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.contents}"
    rounded: "{rounded.card}"
    padding: "0.25rem 0.25rem 0.25rem 0.75rem"
  half-tab-toggle:
    backgroundColor: "{colors.card}"
    textColor: "{colors.pencil}"
    width: "22px"
    height: "28px"
  button-text:
    backgroundColor: "transparent"
    textColor: "{colors.ink-learner}"
    typography: "{typography.caption}"
    rounded: "{rounded.none}"
    padding: "0"
  button-filled:
    backgroundColor: "{colors.accent-strong}"
    textColor: "{colors.text-on-accent}"
    typography: "{typography.caption}"
    rounded: "{rounded.control}"
    padding: "0 1rem"
    height: "28px"
  button-icon:
    backgroundColor: "transparent"
    textColor: "{colors.ink-learner}"
    rounded: "{rounded.control}"
    width: "28px"
    height: "28px"
  field-on-rule:
    backgroundColor: "transparent"
    textColor: "{colors.ink-learner}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "0"
  field-boxed:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
  overlay:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "0.5rem 1.5rem 1.25rem"
---

# Design System: Crux

## Overview

**Creative North Star: "The Card Box"**

Every turn is an index card in a study box, and what the tutor knows about you is the box's tabbed dividers. The thesis: the learner writes on blue cards, the tutor writes on the desk; a check pauses the stack as a card. The tutor's turn carries no stock at all — its pencil head line and body sit flat on the desk-grey ground; the learner's turn is blue stock with blue ink, right-aligned; a check card is white stock with a 3px graphite head rule. The two voices are told apart by the presence or absence of a card, never by an avatar — the one exception is the identity circle in the sidebar foot, the sole permitted mark of a person, and only in the shell. Every card carries one head line at label size (role left, time right) and a 1px hard drop, because a card is a physical object. The profile panel stands to the right of the thread as four dividers, a coloured tab joined to a white body card: red is Focus, amber is Gaps, green is Mastered, pencil is Level. The sidebar is a deeper desk strip whose current row is the one white card, folding to a 3rem icon rail rather than hiding; its foot carries the identity row and its account menu. Every other route is furniture from the same desk: Home is one centred card, Settings is a tab rail (Learning / Usage / Appearance) joined to a white sheet holding desk-deep section cards, Account is its own route in the same sheet grammar, the library is a stack of session cards, auth is one card centred on the desk, dialogs and toasts are lifted cards. Supersedes the Cornell page world (2026-09-15).

Blue remains every control, link and focus ring; the default action is still a written line of blue text, and the filled blue button is reserved for dialog footers, the skip link and the Account submits. Marks are drawn SVG strokes, never glyph fonts; no eyebrow, kicker, uppercase or tracked label exists anywhere in the build. The dark theme is the same desk with the lamp off: darker stock, the same tab law, and the tabs turn to light fills with dark ink so the label still clears AA. Both themes ship from the three token blocks in `base.css`, and the token contrast test asserts every text ink and every tab ink.

Motion is a card appearing, never sliding. A new card fades in (140ms), a landed cue lifts 4px off its divider and settles (one 360ms keyframe), grading draws a red tick or cross as a stroke (240ms), status banners write in left to right (320ms clip-path), routes fade in (160ms). Reduced motion shows the final state.

**Key Characteristics:**
- Desk and card: a flat grey ground and blue card stock (learner) or no stock at all (tutor, flat on the desk) with a 1px edge and a 1px hard drop wherever a card exists; the two voices are told apart by the card's presence, not by two materials.
- Tab colour is law: red only Focus, amber only Gaps, green only Mastered, pencil for Level; blue only for controls.
- One card grammar everywhere a card exists: learner turn, check, composer, divider body, sidebar current row, settings sheet, library row, home, auth cover, dialog.
- The head line: every card (and the tutor's flat turn) opens with a pencil label-size line (role, time or count) and no other chrome.
- Written controls: blue text lines with a 3px-offset underline; drawn strokes for marks and icons; filled blue only where it always was.
- No avatars on turn cards, no kickers, no uppercase tracking, no glyph icon fonts, no ruled ground, no margin rule. The sidebar's identity circle is the one permitted mark of a person, and only there.

## Colors

A grey desk, white and blue card stock, three inks, a pencil, and four tab colours that each name one divider.

### Primary
- **Blue Ballpoint** (`ink-learner`): the learner's ink and the only interactive colour. Learner card text and head line (at 75% opacity), cue words on the Gaps and Mastered dividers, links, text buttons, icon buttons, the composer caret and text, option letters. Also `--color-accent` and `--signal-info` in base.css.
- **Blue Fill** (`accent-strong`): the filled control. The dark value is deeper than the dark learner ink so white label text (`text-on-accent`) clears AA. `.btn-fill`, dialog footer buttons, the skip link, the armed send square.
- **Blue Hover** (`accent-hover`) and **Fill Hover** (`btn-fill-hover`): hover shifts for blue text and the filled button.
- **Blue Ring** (`accent-ring`, 35% light / 45% dark): the component focus ring. The global `:focus-visible` in base.css is solid `ink-learner`; the sidebar and Settings rail use that solid form.
- **Blue Wash** (`accent-soft`): text selection only.

### Secondary
- **Red Pen, mark** (`ink-marker`): a drawn mark only, never text. The focus dash and the 2px red underline under the focus cue and the cue under test, the grading tick and cross, the strike through a wrong recap answer, the topic link's hover underline in the session head. Excluded from the text contrast test.
- **Red Pen, text** (`ink-marker-text`, with `ink-marker-text-hover`): the text-safe red. "Not quite", the recap score, the stop control, the near-limit character count, failed-upload copy, every error line, the destructive confirm fill. The same value as `tab-focus` in both themes.

### Tertiary (the tab law)
- **Focus Red** (`tab-focus`, light #b8352c / dark #ff6a5e): the Focus divider tab, the mark's red tab, the failed head rule on a status banner, the alert border on an auth status box.
- **Gaps Amber** (`tab-gaps`, light #8a5a00 / dark #e6b450): the Gaps divider tab and nothing else.
- **Mastered Green** (`tab-mastered`, light #1f7a3f / dark #5fcf8a): the Mastered divider tab, the mastered tick in the panel, the ready head rule on a status banner, the done border on an auth status box.
- **Level Pencil** (`tab-level`): the Level divider tab; the same value as `pencil`.
- **Tab Ink** (`tab-ink`, white light / #141518 dark): text on every tab. Dark tabs are light fills, so the ink goes dark.
- **AA-safe fills**: the light tab fills are the AA-safe values (#b8352c / #8a5a00 / #1f7a3f) rather than the comp's brighter chips (#d8433a / #c98a00 / #2a8a4a) so `tab-ink` clears 4.5:1; dark tabs are light fills with dark ink (base.css lines 141-145 against the contract's OWN-WORLD hex).
- **Success / Error text** (`success-text`, `error-text`): `--color-success-text` is darkened to #1d733b so it clears 4.5:1 on the desk; `--color-error-text` is consumed by the row menu's End session line.

### Neutral
- **Graphite** (`ink`): tutor text, headings, the check card's 3px head rule, the level stroke, section titles, the active Settings tab and filter toggle.
- **Pencil** (`pencil`): head lines (role, time, count), hints, placeholders, ledes, disabled text, the unset level stroke, the gap circle, inactive Settings tabs, the half-tab toggle glyph.
- **Desk** (`desk`): the ground the cards sit on: the session page behind the thread, the session head, the auth cover, `html`/`body`. Aliased as `--color-background`.
- **Deep Desk** (`desk-deep`): the sidebar, the mobile top strip, the profile panel column, the Settings page ground and its section cards, code fences and inline code. Aliased as `--color-surface-soft`.
- **Card** (`card`): white stock. Aliased as `--color-surface`; PrimeVue inputs, dialogs and toasts move with it.
- **Card Edge** (`card-edge`) and **Card Drop** (`card-drop`): the 1px border and the 1px hard drop under every card; the edge also rules the sidebar's right side, the panel's left side and the mobile strip's foot.
- **Learner Stock** (`card-learner`, `card-learner-edge`): the learner card and the recall concept card.
- **Rules** (`rule`, `rule-strong`): painted option separators inside a check card, the sidebar's section rules, the head rule on the profile page, field lines at rest, table cells, scrollbar thumbs, skeleton bars.
- **Raised Surface** (`surface-raised`): declared for overlays; dialogs and toasts now paint `card`.

### Named Rules
**The Tab Law.** Red is only ever Focus, amber only Gaps, green only Mastered, pencil for Level, blue for every control, link and focus ring. No surface may use a tab colour to mean anything but its divider. Exemption: red and green used as correctness and status signals (the incorrect cross, the recap score, the near-limit count, error text, the 3px head rule on a status banner, the full 1px border on an auth status box, a success tick) are status semantics, not tab meaning, and are permitted (base.css lines 130-145; CueColumn.vue lines 433-434).

**The Desk and Card Rule** (supersedes the Two Stocks Rule). The tutor writes flat on the desk in graphite; the learner writes on blue card stock in blue. Nothing else distinguishes the voices: no avatar on either turn, no alignment trick beyond the card's own side. Check, recap and summary cards keep white stock regardless of who "wrote" them — they are the pause, not a voice.

**The Marked, Never Set Rule.** The focus cue and the cue under test stay in graphite and are underlined in red (2px); red text exists (`ink-marker-text`) only for verdicts, scores, errors and the stop control.

**The Pencil Head Line Rule.** Every card opens with one label-size pencil line: role and time on a turn, role and count on a check, section name and count on a divider tab. Nothing about the card is said anywhere else.

## Typography

**Display Font:** Familjen Grotesk 600 (with system-ui, sans-serif), self-hosted variable 400-700
**Body Font:** Atkinson Hyperlegible Next (with system-ui, sans-serif), self-hosted variable 200-800, used at 400 / 700
**Label/Mono Font:** JetBrains Mono (with ui-monospace, monospace), code only

**Character:** A hyperlegible reading face for hours on the cards, a compact grotesk for the one line that names the page, a mono only inside a fence. No tracked labels, no uppercase, no eyebrows; a heading carries its own weight at normal tracking.

### Hierarchy
- **Display** (600, 2.25rem, 1.15, -0.01em): the not-found title only.
- **Headline** (600, 1.75rem, 1.15): the one-line title of Home, Recall, the library, Settings, the session profile, the aggregate profile, the auth cover.
- **Session Topic** (600, 1.25rem, 1.15): the topic in the session head, a link that gains a 2px red underline on hover.
- **Title** (600, 1.375rem): the recap score, the summary card's "Session ended" line, dialog headers.
- **Subhead** (600, 1.125rem, 28px): headings inside a tutor card (all markdown h1-h4 collapse to this).
- **Body** (400, 1.0625rem, 1.647): card text, cue words, options, the composer, recall concepts. Bold (700) for a check question, a verdict, the focus cue. Measure is `72ch + 2rem`.
- **Contents** (400, 0.9375rem, 28px): sidebar rows, search, new-session line, library topics, menu items; current row at 700.
- **Caption** (400, 0.875rem): head meta, text buttons (700), filter toggles (700), Settings tabs (700), section titles (700), status banners, the level word (700), ledes on cards, the mark's wordmark.
- **Label** (400, 0.8125rem): card head lines (role at 700, time at 400), divider tabs (700), counts, composer hints, citations, field labels, recall card head and streak lines.
- **Mono** (400, 0.9375rem in fences, 0.9em inline, 28px): code only.

### Named Rules
**The One Display Line Rule.** Familjen Grotesk appears once per page as its title, and otherwise only at title size for a score, a closing line or an overlay header. Cards, cues and controls are never set in the display face.

**The Markdown Pitch Rule.** Body line-height is 1.647 (28px at 17px); inside a tutor card MarkdownContent keeps every block margin at a whole `--line-pitch` (28px) and tops up intrinsic blocks (fences, display math, tables, images) with `--snap-pad`. The pitch is a rhythm inside the card, no longer a ruled ground under it.

## Layout

The shell is a two-column grid: the sidebar (18rem expanded, 3rem collapsed, sticky, full height, a 1px `card-edge` down its right side) and the page. Ctrl+B folds the sidebar; Ctrl+. folds the profile panel (App.vue). Non-sheet routes centre in a 72rem `.page-inner` with `clamp(2rem, 6vw, 4.5rem)` of top padding; the session route escapes it edge to edge and scrolls the document, with the composer pinned at the foot (#346).

The session is a grid of `minmax(0, 1fr) / 17rem` under a head row spanning both columns. The head is now a 56px session action bar on the desk with a 1px `card-edge` rule under it (the thread visibly scrolls beneath): left, the topic (a link to the session profile page), the level stroke, its word, a pencil middot and "started ..."; right, 28px drawn icon buttons for Rename, Pin and End session (Resume in place of End once the session has ended), plus an 8px reference-file status dot when documents exist. The thread scrolls on the desk with `1rem clamp(1rem, 3vw, 2rem)` padding; turns stack 0.75rem apart inside a `72ch + 2rem` measure and grow to 1.5rem apart at a change of voice — the tutor's turn is flat on the desk (no card) at 78% max, the learner's card is right-aligned at 78%, check and recap cards at 84%, the summary card 84% (92% under 600px). The foot holds the status slot and the composer card under the same measure, 0.75rem apart. The panel column is `desk-deep` with a 1px `card-edge` left border, `0.9rem 0.9rem 0 1.4rem` padding (room for the half-tab), four dividers 0.9rem apart; collapsed it is 2.75rem wide and the three counted tabs stand on edge (`writing-mode: vertical-rl`, rotated 180deg) under the half-tab. This column and its half-tab are unchanged by the redesign.

Settings spends its full 72rem: the title, one pitch, a tab rail (Learning / Usage / Appearance) 0.375rem apart, then the white sheet joined to the active tab with `1.5rem 2rem 2rem` padding. Inside, each tab lays its section cards in one column, two equal columns from 60rem. Account is no longer a Settings tab: it is its own route (`/account`) in the same sheet grammar (title, one white sheet, desk-deep section cards for Account, Security and Danger) but stacked as a single column top to bottom, not the two-column grid the other tabs use from 60rem. Home is a 44rem card centred vertically in the page. Recall is a 44rem column of dividers 1.5rem apart, one per source session; inside each sheet the concept cards fill a `repeat(auto-fill, minmax(13rem, 1fr))` grid 0.75rem apart. The library is a 56rem column of card rows 0.75rem apart. The profile page is a 72rem stack of full-width cards 1.5rem apart. Auth covers are a 26rem card centred in the viewport.

Breakpoints: under 900px the panel becomes a sticky tab row under the head (focus word or "no focus cue yet", "N gaps", "N mastered", a disclosure chevron) and the dividers open as a 40vh card sheet over the thread; the check card moves from the foot into the thread; the foot goes sticky on the desk. Under 600px cards widen to 92%, the composer hint hides, recall cards and library rows drop to one column (the recall sheet tightens to 0.75rem padding). The sidebar becomes a 3rem `desk-deep` top strip and a fading 18rem drawer over a 45% graphite backdrop.

Spacing is 4px multiples with cards on 8px where they can be: card padding `0.55rem 0.9rem 0.7rem`, card gap 0.75rem, divider gap 0.9rem, divider body `0.4rem 0.7rem`, section cards `1rem 1.25rem 1.25rem`, page sections 1.5-1.75rem, and 28px where MarkdownContent, the sidebar rows and the Settings head keep the pitch. The `--space-*` scale is declared and has no consumers.

## Elevation & Depth

Cards are physical: every card carries a 1px `card-edge` border and a 1px hard drop (`box-shadow: 0 1px 0 var(--card-drop)`), no blur, no spread. That is the whole depth vocabulary on the page; nothing hovers higher, nothing lifts on hover (a library row darkens its edge to `card-drop` instead). The tab rail and tab shapes carry the edge without the drop, since they are joined to a sheet that has one. `--shadow-lift` (`0 12px 24px -12px rgba(0,0,0,0.25)`, 0.7 alpha dark) belongs to surfaces pulled out of the box: dialogs and confirm, toasts, the row menu, the mobile drawer, the mobile profile sheet, and the auth cover card, which stacks the drop and the lift. `--shadow-paper` is declared as `none` and has no consumers.

### Shadow Vocabulary
- **Hard Drop** (`box-shadow: 0 1px 0 var(--card-drop)`): every card at rest: turn, check, recap, composer, divider body, sidebar current row, settings sheet, library row, home card, profile section, recall divider sheet and concept card.
- **Lift** (`box-shadow: var(--shadow-lift)`): teleported overlays, the mobile drawer, the mobile profile sheet, the auth cover.
- **Filing lift** (keyframe only, `0 6px 10px -6px var(--card-drop)` at 4px up): a newly landed cue for the first third of its 360ms filing.

### Named Rules
**The One Drop Rule.** A card has exactly one hard 1px drop and one 1px edge. Never add a soft shadow, a hover lift or a second layer to a card on the page; if it needs the lift shadow, it is an overlay.

## Shapes

Cards are 6px (`--radius-card`), and the corner a tab joins is square: a divider body is `0 6px 6px 6px`, the Settings sheet is `0 6px 6px 6px`, a status banner with a 3px head rule is `0 0 6px 6px` so the rule reads as a tab edge (CapBanners.vue lines 53-54; the detector's border-accent-on-rounded rule is file-ignored in `.impeccable/config.json` for CapBanners, ReferenceStatusBanner, UploadStatus and the five auth/onboarding views, whose status boxes carry a full 1px tab-colour border on a 4px box). Tabs are 5px on the panel (`5px 5px 0 0`, hardcoded in CueColumn) and 6px on the Settings rail and the profile page dividers (`--radius-card` on top). Controls with a hit target (icon buttons, the filled button, boxed fields, inline code, scrollbar thumbs, auth status boxes) are 4px (`--radius-sm`). Written controls, fields on a rule and the sidebar row button are 0. The typing dots (5px) are circles drawn as marks. `--radius-pill`, `--radius-md`, `--radius-lg` are declared and unused.

Borders: 1px `card-edge` on every card and on the shell's structural edges; 3px `ink` head rule on a check or recap card; 3px tab-colour head rule on a status banner; 2px red underline for the marked cue; 2px graphite underline for the active filter toggle. Marks are stroked SVG paths with round caps at 1.5px (ticks, circles, chevrons, arrows, attach, send) or 2px (red marks); the level mark is one diagonal stroke `M2 17 L22 7` at five weights (0.75 / 1.5 / 2.25 / 3 / 3.75), pencil when unset.

## Components

### Cards (turns)
The unit of the world for every turn except the tutor's own. `card` stock, 1px `card-edge`, 6px radius, hard drop, `0.55rem 0.9rem 0.7rem` padding, `0.35rem` internal gap.
- **Tutor turn (no card)**: left-aligned, 78% max (92% under 600px), flat on the desk — no edge, no drop, no stock. Head line: "tutor" in pencil label 700, the time in pencil label at the right; the landed tick (blue, 240ms stroke draw) sits at the head line's top-right so filing never reflows the turn. Body in graphite via MarkdownContent; tool activity as a pencil aside; citations as a footnote block. `0.35rem` gap between the head line and the body, same as a card's internal gap.
- **Learner card**: right-aligned, 78% max, `card-learner` stock with `card-learner-edge`; head line ("you", time) and body all in `ink-learner`, the head at 75% opacity.
- **Check card**: 84% max, white stock; the head line ("check" in pencil label 400, "1/3" at the right) carries `padding-bottom: 0.4rem` and a 3px graphite `border-bottom`. Question in body 700; options as full-width transparent buttons with a painted `rule` separator (`inset 0 -1px 0`), a blue 700 letter and graphite text, hover underline; grading draws the red tick or cross, the wrong text goes pencil, the verdict reads "Correct" in graphite or "Not quite" in text-safe red. Skip / Next are text buttons. Coarse pointers grow each option to 3.5rem.
- **Recap card**: the same 84% card with the 3px head rule; the score in the display face at title size in text-safe red beside the gap name in pencil caption; the correct option ticked in red, the learner's wrong pick in blue struck through in red; explanations in pencil.
- **Summary card**: the last card in an ended session, white stock, 84%: "Session ended ..." in title size, the summary in body, a pencil caption, Review my gaps / Resume topic as text buttons.
- **Typing card**: a tutor card whose body is three 5px pencil dots pulsing (1200ms), settled at 60% under reduced motion.

### Divider (profile panel)
What the tutor knows, as tabbed dividers. Each divider is a tab (`.cue-tab`: inline-flex, `0.15rem 0.6rem`, `5px 5px 0 0`, label 700 in `tab-ink`, the count at 400) fixed to a body card (`0.4rem 0.7rem`, `0 6px 6px 6px`, edge and drop). Focus: red tab, the word in graphite 700 with a red 2px underline and a red dash mark. Gaps: amber tab, pencil circle, word in blue; the cue under test takes the red underline without the weight. Mastered: green tab, green tick, word in blue. Level: pencil tab, the diagonal stroke and the level word in graphite caption 700 ("level not set" in pencil), subtopic strokes under it in pencil. Empty bodies say "no focus cue yet" / "none open" / "none yet" in pencil. Rows are 1.5rem (`--cue-row`). A new cue files in with the 360ms lift-and-settle. Collapsed (usePanel, `crux.panel.expanded`, Ctrl+.): three counted tabs on edge in a 2.75rem rail. Under 900px: a sticky tab row on the desk (the focus tab, or a white "no focus cue yet" tab, then "N gaps" and "N mastered" tabs) with a blue disclosure chevron that opens every divider at once in a 40vh card sheet over the thread, with a 55% desk wash beneath it.

### Half-Tab Toggle
The collapse control on the profile panel's left edge only (Ctrl+.): 22 by 28px, `card` stock, 1px `card-edge` with the joined side open, 6px on the free corners, a pencil chevron that turns graphite on hover, `hit-44`. The sidebar's own toggle is no longer this shape — see Sidebar below.

### Composer
A white card at the foot: `0.55rem 0.9rem`, a three-column grid (attach, textarea, send or stop), the border turning `ink-learner` on focus-within, `card-edge` when disabled. The learner writes in blue on a transparent textarea (1.75rem min, 10.5rem max). Attach and stop are drawn 28px icon buttons (stop in text-safe red); send is a 28px square whose `accent-strong` fill fades in under the arrow once the draft is non-empty. Pencil label hints below ("Enter to send, Shift + Enter for a new line", the count turning text-safe red 700 near the 4000 limit).

### Status Banner
A card with a tab edge: `card` stock, 1px `card-edge`, 3px head rule, `0 0 6px 6px`, `0.4rem 0.75rem`, caption on the pitch, lands with the 320ms clip-path reveal. The head rule is `color-accent` while processing, `tab-mastered` when ready, `tab-focus` when failed (with the copy in text-safe red); the cap banners are always `tab-focus` with a text-safe red lead. The PrimeVue toast is a lifted card: `card`, `card-edge`, 6px, no severity tint, body 700 summary and pencil detail, the same reveal.

### Settings
A tab rail joined to a sheet. Rail tabs: Learning, Usage, Appearance — `desk` fill, `card-edge` on three sides, `6px 6px 0 0`, pencil caption 700, `0.5rem 1rem`; the active tab is `card` in graphite with a -1px bottom margin over the sheet's border. Sheet: `card`, `card-edge`, `0 6px 6px 6px`, hard drop, `1.5rem 2rem 2rem`. Sections are `desk-deep` cards (`card-edge`, 6px, `1rem 1.25rem 1.25rem`, no drop) with a caption 700 graphite title; two columns from 60rem. The routed page paints `desk-deep` edge to edge. `/settings/profile` redirects to Learning.

Learning holds the tutor preferences, one card each and in this order: Feedback style (Hints / Direct answers), Check-ins (Often / Sometimes / Only when I ask, with a pencil label line saying how often the tutor runs a quick check unasked) and Reply length (Brief / Balanced / Thorough), all as lettered lines. There is no save button: each choice autosaves as its own `PATCH /api/me`, and the "Saved." flash (blue tick, caption) sits on that card's title line until the choice changes again; a failed save puts the choice back and raises the error toast. Usage is today's spend against the daily cap: the glance line and the tiered meter. Appearance is unchanged.

### Account
Its own route (`/account`), not a Settings tab, in the same sheet grammar (shared `assets/sheet.css`) but a single column: Account (display name field, read-only email line, Save name), Security (current/new/confirm password), Export your data (Download my data, a filled button that saves one dated JSON file), Danger (Delete account). Export sits directly above Delete: take it or destroy it. `/settings/account` redirects here. Delete opens a lifted confirm dialog listing what is erased, arming its destructive `.confirm-delete-strong` button only once the learner types "delete"; success clears the user store, signs out and routes to login, failure keeps the dialog open with an error line.

### Sidebar
A `desk-deep` strip with a 1px `card-edge` right side. Head: the mark and wordmark, and a drawn 20px "sidebar" icon (a rectangle with a narrow left pane) that folds and unfolds it — the half-tab chevron this replaced used to overlap the centred mark at 3rem; the new toggle sits above the mark when folded instead. New session is a blue contents 700 line with a drawn plus; Profile is a blue line with a drawn divider card (a card with its tab up, never a person mark), always shown; Recall sits directly under it, a blue line with a pencil count, shown only when something is due; search is a field on a rule; Active / Ended are caption 700 blue toggles, the one in force in graphite under a 2px graphite underline. Rows are the topic only at contents size, 6px radius, hover at 60% `card`; the current row is a white card (edge and drop, 700 topic); ended rows go pencil.

Collapsed (Ctrl+B, `crux.sidebar.expanded`): a 3rem icon rail, not a bare strip. Top to bottom: the sidebar toggle, New session (drawn plus), Search (drawn lens — clicking it unfolds the sidebar and focuses the search field), Profile (the drawn divider card, `title="Profile"`), Recall (drawn clock with the due count as a small blue numeral when non-zero), then the foot: the identity initial. No logo and no per-session markers; sessions appear when the sidebar unfolds.

Footer (both states): the identity row alone (Settings is reached through its account menu) — a 28px initial circle (`card` stock, 1px `card-edge`, blue initial at 700) plus the display name in contents size (folded: the circle alone). The name falls back to the sign-in email's local part (never the full address) when the display name is empty or the user store's unset placeholder. Folded, the circle's tooltip is the name. Clicking the row opens the account menu: a lifted card in the row-menu grammar with the sign-in email (pencil, caption) as its head, then Settings, Usage and Account as one-pitch items each led by a drawn 16px pencil icon, a rule, then Sign out with its own icon. It opens above the row, left-aligned with the avatar, in the same place folded or unfolded; it opens by mouse or keyboard, moves focus in, and closes on Escape, outside click or item choice, returning focus to the row.

### Buttons
- **Text button** (the default): transparent, caption 700 in `ink-learner`, underline at 3px offset; hover shifts to `accent-hover`; disabled goes pencil with no underline. Skip, Next, Done, Resume, Review my gaps, View all, Continue, Check <topic> now, load earlier, Load more, See all topics.
- **Page CTA** (Start, Begin, Sign in): the text button with a drawn 18px arrow (1.5px, round caps) 0.375rem after the word; only the word is underlined.
- **Filled button** (`.btn-fill`): `accent-strong` fill, white caption 700, 4px, 28px tall, `0 1rem`; hover `btn-fill-hover`; disabled is transparent with a `rule-strong` outline and pencil label. Dialog footers, the skip link, Save name, Update password. Destructive confirm: `ink-marker-text` fill with white label.
- **Icon button**: a drawn 20px stroke in `ink-learner` on a 28px square, 4px radius; disabled pencil.
- **Filter toggle**: caption 700 blue; the one in force graphite under a 2px graphite underline.
- **Focus**: 2px `accent-ring` outline at 2px offset on components; solid `ink-learner` in the sidebar, the Settings rail and globally.

### Inputs / Fields
- **Field on a rule** (sidebar search, row rename, Home topic, library search, auth fields, profile add-row): transparent, no box, one 1px bottom rule (`rule-strong`, or `card-edge` on the auth cover) that turns `ink-learner` on focus; text and caret in `ink-learner`, placeholder pencil; a pencil label above it where it needs a name.
- **Boxed field** (PrimeVue InputText / Textarea / Select in overlays): `card` ground, 1px `rule-strong`, 4px; focus is a blue border plus a 2px solid blue outline at 1px offset, no glow.
- **Written select** (library sort): a native select with `appearance: none`, caption 700 blue, a drawn 1.5px chevron at the right edge.
- **Lettered lines** (LetteredLinesPicker, check options): a blue 700 letter, graphite text (700 when selected), a painted `rule` separator, a drawn blue tick when chosen.
- **Auth status box**: `card` stock, 1px full border, 4px, `0.4rem 0.75rem`; the border is `tab-focus` for an alert (copy in text-safe red) or `tab-mastered` when done.

### Profile Page
The aggregate profile at `/profile` (#362), reached from the sidebar. Head: "Your profile" and a pencil lede ("What the tutor knows about you, topic by topic. Last studied ..."), no Back. Then, 1.5rem apart: topic cards over the five most recent sessions, two columns from 60rem (pencil head line active/ended and when; the topic in display 600 1.25rem linking to its session profile, red-underlined on hover; level stroke and word, the red focus dash and the focus gap underlined red, the green tick and "N mastered"; the summary or, in italic, the cleaned last message, clamped to two lines; Continue or Resume and Open profile), with a "Showing N of M topics." foot and See all topics. Then three dividers across every session: Level (pencil tab, one row per level plus "level not set"), Gaps (amber) and Mastered (green), their cue words linking to the first-seen session profile with "in N sessions" when a concept recurs, two columns from 60rem. Last, two figure cards side by side from 60rem: Mastered by week (12 green columns, capped at 20rem) and Check accuracy (least and most accurate three, concept linked, correct of total, last five as red ticks and crosses). No sessions: the EmptyState card under the head.

### Recall Divider
One per source session, queue order kept. The tab is the Settings rail's active tab (white stock, caption 700 topic, "N due" in pencil 400, `0.5rem 1rem`, overlapping the sheet by 1px); the sheet is white with the joined corner (`0 6px 6px 6px`), edge and drop, `1rem` padding. Each due concept is a `card-learner` card (`card-learner-edge`, 6px, drop, `0.625rem 0.75rem`, min 5.5rem): the pencil head line is the due-since ("due 3 days ago"), the concept in body 700 blue, and the streak in words ("2 correct in a row" / "not yet held") as a pencil label line under it -- the one card that carries a foot line, because the streak is what the check will change. The whole card is the control. Under the cards, "Check <topic> now" as a text button with a pencil aside "starts with <first concept>". Past the queue's 100-per-page cap, a "Load more" text button under the last divider appends the next page; later cards join their session's divider wherever it sits, the tabs count what is loaded and the count line stays the true total. A failed next page keeps the loaded dividers and writes the inline error row with a Retry for that page alone. Empty: one divider tabbed "Nothing due" with the copy and a blue Back home line.

### Library Row
A white card per session (`0.875rem 1rem`, edge, drop, 6px), the edge darkening to `card-drop` on hover: the topic at contents size, the mastered count in pencil label with a blue tick at the right, the three-cell label (SessionChips), a two-line pencil description, a Continue text button in the right column.

### Overlays
Dialog and confirm: `card`, 1px `card-edge`, 6px, lift shadow; header in the display face at title size; footer under a 1px `color-border` rule with the filled button. Row menu: the same lifted card, items one pitch tall, End session in `color-error-text`.

### Page Mark
The tabbed card. A 32 viewBox: a 25x19 rectangle (rx 2) stroked 2.5 in the current ink at (3.5, 9.5), a `tab-focus` filled tab 11 wide by 6 tall on its top-left corner, two graphite lines inside (14 and 8 long). "Crux" in the display face at 600 beside it. 22 / 28 / 56px. `favicon.svg` carries the same geometry with a `prefers-color-scheme: dark` block (#ecebe6 ink, #ff6a5e tab); `favicon.ico` is generated at 16 / 32 / 48 by `scripts/gen-favicon.py`.

## Do's and Don'ts

### Do:
- **Do** build every new surface out of the one card: `card` stock, 1px `card-edge`, `--radius-card` 6px, `box-shadow: 0 1px 0 var(--card-drop)`, a pencil label head line first.
- **Do** keep tab colours to their dividers (red Focus, amber Gaps, green Mastered, pencil Level) and blue to controls; red and green as correctness or status signals are the only permitted other use.
- **Do** square the corner where a tab or head rule joins a card (`0 6px 6px 6px` for a divider body or sheet, `0 0 6px 6px` for a banner with a 3px head rule).
- **Do** make the default action a blue text line (caption 700, underline offset 3px) and reserve `.btn-fill` for dialog footers, the skip link and the Account submits; put `accent-strong`, not `ink-learner`, behind white text.
- **Do** draw marks and icons as stroked SVG paths (1.5px round caps; 2px for red) and animate them with stroke-dashoffset over 240ms; the PrimeIcons font is loaded by no Vue file.
- **Do** keep motion to opacity, clip-path, a stroke draw or the 4px filing lift; nothing slides across columns, and reduced motion declares its final state beside its keyframes.
- **Do** add any new colour token to all three `base.css` blocks in 6-digit hex so tokenContrast.test.js asserts it, and add every new tab ink pair to the tab contrast case.
- **Do** keep a two-state control the same height in both states (the send square never changes size).
- **Do** keep test hooks (data-testid, aria attributes, asserted class names, copy strings) unchanged when extending a surface.

### Don't:
- **Don't** put an avatar, an icon tile, a kicker or eyebrow, an uppercase or tracked label, or a glyph icon font on a turn card. The one exception is the sidebar's identity circle, the sole permitted mark of a person, and only in the shell.
- **Don't** add a soft shadow, a hover lift, a gradient or a second border to a card; the 1px hard drop is the only depth on the page, and `--shadow-lift` is for overlays, the drawer, the mobile profile sheet and the auth cover only.
- **Don't** set text in `ink-marker` or in a tab colour; text-safe red is `ink-marker-text`, and tab ink is `tab-ink` on a tab fill.
- **Don't** paint a ruled ground, a gutter role tag or a margin rule; `--ruled-bg`, `--ruled-offset` and `--margin-rule` stay declared for the drift guard and have no consumers.
- **Don't** fill a hover; underline it or shift to `accent-hover`. The only hover fills are 60% `card` on a sidebar row, `desk-deep` on an overlay item and `card` on a Settings rail tab.
- **Don't** set a page's section headings in the display face; one display line per page, the rest is the body face at caption 700 or Subhead.
- **Don't** open dividers one at a time on mobile; the shipped sheet opens all four (plan line 93, CueColumn.vue lines 735-763), and the contract's one-at-a-time behaviour is an unshipped stretch goal, not a rule.
- **Don't** invent a "last movement" phrase on the Level divider; the API carries no level timestamp (CueColumn.vue lines 314-317).

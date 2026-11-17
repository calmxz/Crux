# Themes

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers the light and dark themes on every screen: how a learner gets one, where the choice is kept, the look and its anchor colours, pictures and the parts Crux does not draw, and the contrast test. All of it comes from [#779] unless a line says otherwise. Each screen file keeps its own changed line and links here. The prototype the owner chose from is on the throwaway branch `prototype/779-dark-theme`.

## Getting the theme

- Crux follows the device's light or dark setting by default. The learner can choose "Match my device", "Light" or "Dark", on the Settings page's Appearance part (see [`account-screens.md`](account-screens.md)).
- A page follows the browser's kept choice, or the device's setting when it has none. This holds on every page, signed in or out: the landing page, sign-in, Request access, the legal pages, the copy page, "Page not found", the ended pages and the owner pages.
- The owner page's address is a path on the main app's site, so the browser's kept choice reaches the owner pages (see [`owner-screens.md`](owner-screens.md)).
- A browser that reports no setting gets the light theme.
- A new choice applies at once, with no reload, and every open Crux tab on that browser switches with it. When the device's setting changes, as at sunset, every tab following it switches at once.
- Pictures already on screen are drawn again in the new theme.

## Where the choice is kept

- An account's choice is kept by that browser only. Crux never receives it. Each browser starts at "Match my device". The choice stays on that browser after signing out, so on a shared computer the next person sees it. It is not a stored item, and it is not in a copy of a learner's data.
- A trial link's choice is kept the same way, by that browser only.
- A small script file applies the kept choice before the page first draws, so the wrong theme never flashes. It is a file, since the page runs no inline scripts (see [`security.md`](security.md)).
- A guest's choice is set on the guest's own Settings page (see [`landing-screens.md`](landing-screens.md)). The tab holds it, so nothing is kept after the tab closes, and it applies only to pages in that tab.
- Nothing Crux sends to its backend, and no error report, carries the choice, Sentry's included if it is added at opening (see [`operations.md`](operations.md)). The Privacy Policy and the Trial Privacy Notice say so (see [`terms-and-policy.md`](terms-and-policy.md) and [`trial.md`](trial.md)).

## The look

- The dark theme is neutral grey: a dark grey page with slightly lighter grey cards, matching the light theme's neutral greys.
- In both themes, text boxes, ticks and buttons have an edge of at least 3:1. Dividers stay faint, as decoration.
- In the dark theme, filled buttons, pressed choices, ticked boxes and the learner's own message keep their fill and white text, and get a 1px edge in the link blue.
- The light theme's green text, grey text and progress bars are darker than in the earlier prototypes, so they pass.
- The mastery check bar is in the theme's text colour, with its text in the page colour, and the "Check open" badge matches it (see [`learning-screen.md`](learning-screen.md)).
- A search's matched words are bold, on a soft tint, and an opened message is ringed in Crux's orange, at least 3:1 against the page (see [`app-shell.md`](app-shell.md)).

The anchor colours. Every other colour follows the rules here and the contrast test; the prototype branch holds the drafts as a starting point.

| Anchor | Light | Dark |
|---|---|---|
| Page | `#f6f7f9` | `#16181c` |
| Card | `#ffffff` | `#1f2227` |
| Text | `#1d2330` | `#e6e8eb` |
| Secondary text | `#5f6673` | `#a0a7b2` |
| Crux's blue | `#2f5bea`, for links and fills | `#8aa4ff` for links; `#3a5fe0` for fills, with white text |

## Pictures, maths and outside parts

- Diagrams and graphs are drawn in the theme's own colours. Crux sets Mermaid's colour settings from the theme, in both themes (see [`ai-layer.md`](ai-layer.md)).
- Maths takes the theme's text colour, including maths KaTeX cannot draw (see [`learning-screen.md`](learning-screen.md)).
- Crux draws "Continue with Google" to Google's branding guidelines: their dark button in the dark theme, their light button in light.
- The human check (Turnstile) gets the theme Crux is showing, light or dark, set explicitly rather than Turnstile's "auto". While it has not passed, a theme change draws it again in the new theme, so a box that shows later matches the page. Once it has passed, it keeps its theme until the page loads again.
- In the dark theme, the learner's file pages, thumbnails and photos show dimmed, at 80% brightness (draft), keeping their own colours. In light they show as they are.
- The landing page's example video shows as recorded.

## Checking it

- The contrast test runs on every pull request and blocks a merge, like the five browser paths. A part under its ratio fails it.
- It runs inside the browser path that opens every route in both themes (see [`ordinary-tests.md`](ordinary-tests.md)). It measures the drawn colours of each control's edge, each bar, focus ring and mark against what is behind it, and the pictures and maths as drawn: diagrams, graphs, drawn maths, the sideways box's focus ring and the code style for maths KaTeX cannot draw. The ratios are AA's (see [`quality-bar.md`](quality-bar.md)).
- The path brings up every state in which one of those parts shows, including: a topic under way (progress bars, the check's progress dots and, at phone width, the strip's segments), trouble and mistake marks, the file viewer's highlighted page, the lock bar, focus, pressed and ticked controls, the open check bar, dialogs, a search's matched words and the opened message's ring.
- It leaves out the learner's own files and photos, since Crux does not choose their colours, and Turnstile's own frame.

## Emails

Themes cover screens. Crux's emails have one design.

## Frontend modules

| Module | What it holds |
|---|---|
| Themes | Both themes' colours, the theme choice and applying it before the first draw, switching every tab at once, Mermaid's colour settings, the Google button's and Turnstile's themes, and dimmed files |

The Appearance part belongs to the Settings module in [`account-screens.md`](account-screens.md), and the guest Settings page to the Guest mode module in [`landing-screens.md`](landing-screens.md).

[#779]: https://github.com/calmxz/Crux/issues/779

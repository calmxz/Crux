# Glossary

Glossary for Crux in two sections, each alphabetical: the domain vocabulary, then the Card Box design vocabulary (see `DESIGN.md`).

## Domain vocabulary

- **Check** — the tutor's quiz on one gap: 1-3 Sets, ordinary or Diagnostic. Only the server grades it.
- **Close** — a Set ending, by Complete, Stop or session end. Grading runs (forced on Stop and session end) and the Recap freezes.
- **Diagnostic** — a Check that places the learner's knowledge level. Graded once over all its Sets; it makes no mastery or gap changes.
- **Item** — one multiple-choice question in a Set.
- **Recap** — the frozen view of a closed Set, shown under the message that asked it.
- **Set** — the Items the tutor asks in one turn, shown on one check card. A Check's Sets run in order. *Avoid: batch, pending check.*

## Design vocabulary

- **Account menu** — the lifted popover the identity row opens: the sign-in email as a head, then Settings, Usage and Account with drawn icons, a rule, and Sign out. Formerly the user menu (name and email head, Account and Sign out only).
- **Card** — the base unit of the world: white or blue stock, 1px `card-edge`, 6px radius, 1px hard drop. Every turn, check card, composer, divider body, sidebar current row, settings sheet, library row and dialog is built from it.
- **Check card** — the white card that shows the open Set's Items and takes the learner's answers and skips.
- **Desk** — the flat grey ground every card sits on: the session page behind the thread, the session head, the routed page background.
- **Divider** — a tab joined to a white body card. On the profile panel and the aggregate profile page the tab is coloured by section (Focus red, Gaps amber, Mastered green, Level pencil); on the Recall page there is one per source session, tabbed with its topic and due count.
- **Half-tab** — the 22x28px edge toggle that folds or unfolds a column. Only the profile panel keeps one; the sidebar's half-tab was replaced by the rail's drawn sidebar icon.
- **Head line** — the pencil label-size line that opens every card: role and time on a turn, role and count on a check card, section name and count on a divider tab.
- **Identity row** — the sidebar foot's initial circle plus display name (the sign-in email's local part when no name is set), the trigger for the account menu. On the rail it is the initial alone, with the name as its tooltip.
- **Rail** — the sidebar folded to a 3rem strip of icons: the sidebar toggle, New session, Search, Profile, Recall (only while a concept is due), then the identity initial. No logo and no per-session markers; sessions appear only when the sidebar unfolds.
- **Session action bar** — the 56px bar under the session head, topic/level/started on the left, Rename/Pin/End-or-Resume and the reference-file status on the right.
- **Sheet** — the white card a Settings or Account tab rail is joined to.
- **Stock** — the card material that tells a voice apart: white for the tutor's check card, recap and summary cards, blue for the learner's card. The tutor's own turn carries no stock; it writes flat on the desk.

# The app shell's modules against the old frontend

Part of [the old frontend comparison](../old-frontend-comparison.md) (#768). The modules are the ones in [`app-shell.md`](../../spec/app-shell.md) (Frontend modules). Old paths are under `frontend/src/`. The size key and the sizing rule are in the index.

## App shell

- **Old code:** `App.vue`, `components/sidebar/Sidebar.vue` (1,374 lines), `SidebarMobileTopStrip.vue`, `SidebarUserMenu.vue`, `composables/useSidebar.js`, and the routes in `router/index.js`. Routes marked `sidebar: false` (sign-in, legal pages, onboarding, not found) draw no shell.
- **Matches:**
  - A sidebar beside the main area on desktop, and on a phone a drawer opened from "☰" in a top strip ([`app-shell.md`](../../spec/app-shell.md), The shell).
  - "New session" at the top, the session list, and a foot with Settings and Sign out.
  - The main area swaps between a session and the other pages.
- **Differs:**
  - `/` opens the start page. The spec opens the most recent session that isn't sealed, or a new session's start box when there is none (The shell).
  - The desktop sidebar folds to a 3rem rail with Ctrl+B. The spec's list is "always in view".
  - The foot holds Profile and Recall links, and a menu under the learner's initial and display name with Settings, Usage, Account and Sign out. The spec's foot holds "What you've mastered", then Feedback, then Settings with the account's email.
- **Missing:** the sealed message in the main area; the age card when no conversation is open; the locked account's screen first; the Owner link; the guest sidebar; "Trial link" in place of the email.
- **Stack:** Vue, vue-router, PrimeVue `Toast` and `ConfirmDialog`.
- **Size:** Medium: the sidebar, drawer and routed main area fit; where the app opens and the sealed, guest and trial states are new.

## Session list

- **Old code:** the list sections in `Sidebar.vue`; `SidebarSessionRow.vue`; `SidebarRowMenu.vue` (Rename, Pin, End, Continue topic, Resume); `composables/useSessionActions.js`, `useSessionGroups.js` and `useVisibilityRelist.js`; a search box that asks the backend.
- **Matches:**
  - A menu on each line, and an action bar in the session's header (Rename, Pin, End, Resume), sharing one set of actions ([`app-shell.md`](../../spec/app-shell.md), Rename and delete).
  - Renaming in place: Enter saves, Esc cancels, and an empty name keeps the old one.
  - Lines ordered by last activity ([`sessions.md`](../../spec/sessions.md), Names and the session list).
- **Differs:**
  - A line is one row: the name, with a pin mark. Sessions fall into pinned, active and ended groups, against one list by last visit.
  - The menu has no Delete; End makes a session read-only until resumed.
  - A blur also saves a rename. There is no 80-character limit.
- **Missing:** the second and third rows ("On: Range" or "Mastered last", the last visit, the bar and "3 of 4"); the badges ("Sealed", "Remove a file to continue", "Check open", "1 waiting"); Delete with the warning that names what goes, and the typed "delete" when the Record would lose something ([`sessions.md`](../../spec/sessions.md), Deleting a session); a sealed session's menu.
- **Stack:** Vue, a hand-built popover, PrimeVue `ConfirmDialog`.
- **Size:** Medium: the list, the menu and renaming fit; the line's contents, the badges and Delete are new.

## Record

- **Old code:** `views/AggregateProfileView.vue` (864 lines), "Your profile": check accuracy, mastered concepts by week, and each topic's concept lists, with "Open profile" to the session's profile page.
- **Matches:** one page outside any session, built from every session ([`sessions.md`](../../spec/sessions.md), What the learner sees).
- **Differs:** a dashboard of counts and concept lists, against a read-only list of mastered topics and passed objectives, each with its date and its session. A line opens a profile page, not the session.
- **Missing:** the By date and By session filter; the section of objectives passed on topics not yet mastered; opening at an open check; the sealed message; the last visit beside a shared name ([`app-shell.md`](../../spec/app-shell.md), What you've mastered).
- **Stack:** Vue, with charts drawn in inline SVG.
- **Size:** Large: a stats page, not the Record.

## Files

- **Old code:** the file button in `components/chat/Composer.vue`; `services/uploadApi.js` (a type and size pre-check, then a multipart `POST /upload`); `components/chat/UploadStatus.vue`; `components/chat/ReferenceStatusBanner.vue` (file states, and "Delete file" with a confirm dialog); `composables/useReferencePoll.js` (polling at 2, 4, 8 and 15 seconds, for up to 90 seconds).
- **Matches:**
  - Files come in through a button in the chat box ([`app-shell.md`](../../spec/app-shell.md), Files on screen).
  - A wrong type or a file over the limit is refused before upload, with a message naming the file.
  - Each file shows a state, and removing one asks first.
- **Differs:**
  - The file passes through the backend, against a browser upload straight to the bucket with a one-time link ([`hosting.md`](../../spec/hosting.md), Cloud Run).
  - PDF, PowerPoint, text and Markdown up to 25 MB, against PDF, images, PowerPoint and Word up to 50 MB and 100 pages ([`files.md`](../../spec/files.md), Types and limits).
  - Files are added only inside a session, and their states show in a banner above the chat box, not under each name in the objectives panel. A refusal shows in the same status slot, not as a pinned line that stays until dismissed.
- **Missing:** the start box's chips; dropping files on desktop; the spec's wording for each state; greying while files are off or the store is full; the allowance dialog; the held session's pinned line; "Reading…" in the conversation; the 100-page check.
- **Stack:** Vue, `fetch` with `FormData`, PrimeVue `ConfirmDialog`.
- **Size:** Medium: picking, checking, states and removal exist; the upload path, the limits and the dialogs change.

## File viewer

- **Old code:** none. Page citations under a reply are plain text, and no page can be opened.
- **Missing:** the viewer at a highlighted page, page thumbnails, "Slide 30 of 31", speaker notes, the desktop placement in the panel's place, the phone's full screen, and the held file's row ([`app-shell.md`](../../spec/app-shell.md), Reading a file).
- **Size:** Large: nothing exists.

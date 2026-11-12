# The learning screen's modules against the old frontend

Part of [the old frontend comparison](../old-frontend-comparison.md) (#768). The modules are the ones in [`learning-screen.md`](../../spec/learning-screen.md) (Frontend modules). Old paths are under `frontend/src/`. The size key and the sizing rule are in the index.

## Session screen

- **Old code:** `views/SessionView.vue` (1,671 lines) lays out the top bar (`components/chat/SessionHeader.vue`), the conversation, the chat box (`components/chat/Composer.vue`) and the right-hand panel (`components/chat/CueColumn.vue`) as one grid. `stores/session.js` (1,682 lines) holds the session, its messages, the stream and the open check.
- **Matches:** one screen with a top bar, the conversation, the chat box and a panel, laid out for desktop and for a 390-pixel phone ([`learning-screen.md`](../../spec/learning-screen.md), One screen).
- **Differs:**
  - The check is a card added under the conversation. Nothing is cleared or hidden when it starts, against "the thread is cleared to the check alone" (The mastery check).
  - The top bar holds the topic, the level, the start date, and Rename, Pin, End and Resume. The spec's top bar holds the session menu with Rename and Delete, the jump menu and a title that renames on click ([`app-shell.md`](../../spec/app-shell.md), Rename and delete; Jump points).
  - The store's state is concept lists, check sets graded by index, and ended or reopened sessions. The spec's state is objectives, written problems and their marks (see the backend note, [#749](https://github.com/calmxz/Crux/issues/749), Learning and Mastery check).
- **Missing:** the switch into and out of the check, with files, earlier teaching and jump points hidden and brought back (The mastery check); the jump menu; the guest reply count and the mini check's bar ([`landing-screens.md`](../../spec/landing-screens.md), Guest mode).
- **Stack:** Vue single-file components, a Pinia store, PrimeVue `Dialog`.
- **Size:** Medium: the layout fits; the check switch, the top bar's contents and the state under it change.

## Conversation

- **Old code:** `components/chat/MessageList.vue`, `AssistantBubble.vue`, `UserBubble.vue`, `MarkdownContent.vue` with `lib/markdownRenderer.js` and `lib/markdownStreamBuffer.js`, `ToolCallChip.vue`, `CitationsList.vue`, `CapBanners.vue`, `components/TopicSuggestCard.vue`, `components/DiagnosticConsentCard.vue`, `components/SessionEndedBanner.vue`. Replies stream over server-sent events (`services/chatStreamService.js`, `lib/sseParser.js`), batched per frame (`lib/deltaBatcher.js`).
- **Matches:**
  - Tutor and learner messages, streamed with a Stop button, with a mark on a stopped reply.
  - Cards inside the thread that the learner answers there (a topic card and a level card).
  - A status slot above the chat box that holds limit messages, close to the spec's pinned lines ([`learning-screen.md`](../../spec/learning-screen.md), Crux's own lines).
- **Differs:**
  - Limit messages read "{used}/{cap} requests today" and "${used} of ${cap} spent today", against "A learner never sees money" ([`spending.md`](../../spec/spending.md), What is counted).
  - Limit messages sit above the chat box and errors arrive as toasts, against Crux's own lines as centred lines in the thread, coloured by kind, that stay in the conversation (Crux's own lines).
  - The topic card offers lettered choices that the learner taps. The spec's menus are tutor messages "answered by typing" (Menus and buttons).
  - Tool chips and page citations ("p.12") show under the tutor's reply. The spec has neither; a pointer such as "as on slide 30" is a link into the file viewer ([`app-shell.md`](../../spec/app-shell.md), Reading a file).
  - The level card asks the learner to rate their own level. The spec's diagnostic is the tutor's ([`teaching.md`](../../spec/teaching.md), The diagnostic).
- **Missing:** Crux's own lines by kind (information, warning, stop, care) and each line the spec lists; waiting marks on stopped messages; pinned lines that stack with the held line first; the age card; the named buttons under the tutor's message ("Start the check", "Not yet", "Continue", "Refresh first").
- **Stack:** Vue, PrimeVue `Toast`, markdown-it with DOMPurify, and KaTeX and highlight.js loaded on first use. The SSE parser, the stream buffer and the frame batcher import no framework.
- **Size:** Medium: messages and streaming work; Crux's own lines, waiting marks and pinned lines are new.

## Objectives panel

- **Old code:** `components/chat/CueColumn.vue` (774 lines) and `composables/usePanel.js`. On desktop it is a column on the right that folds to a thin rail. On a phone it is a strip with counts and a button that drops down the full panel.
- **Matches:** the shape: a right-hand rail on desktop, and on a phone a strip with a count that a tap opens ([`learning-screen.md`](../../spec/learning-screen.md), The objectives panel).
- **Differs:**
  - It holds Focus, Gaps, Mastered and Level, with subtopic levels: concept lists, against objectives with five statuses and a trouble mark ([`teaching.md`](../../spec/teaching.md), Objective statuses and readiness).
  - The learner can fold it away. The spec's rail is "always visible", except while the file viewer takes its place.
- **Missing:** the topic's name and its files; each objective's status; the trouble mark as text; passed dates and "passed in" links; dropped objectives; the paused topic; preferences with a way to remove each; "Mastered in this session"; the session's files with states, mistake marks and ×; the check's progress dots; the strip's coloured segments and "2 of 5".
- **Stack:** Vue, with marks drawn in inline SVG.
- **Size:** Large: the rail and strip fit, but every item in them differs.

## Mastery check

- **Old code:** `components/chat/CheckQuestion.vue` (535 lines). It shows 1 to 5 multiple-choice items per set, in 1 to 3 sets, with Skip, Back, Next, Done and Stop. The store sends each tap's index to `POST /sessions/{id}/check/answer`.
- **Matches:** progress through the problems, and sets shown as segments.
- **Differs:** the learner taps one of the options, against "No multiple choice" and answers typed in the chat box ([`mastery-check.md`](../../spec/mastery-check.md), Problems; [`learning-screen.md`](../../spec/learning-screen.md), The mastery check). The learner can skip an item or stop the check from the card.
- **Missing:** the dark check bar ("Mastery check · Problem k of N · closed book"); the Photo button in place of the file button; "Marking…", reminders and the end step as messages in the thread; the mini check's bar for guests.
- **Stack:** Vue.
- **Size:** Large: the check model differs.

## Result

- **Old code:** `components/chat/CheckRecap.vue` (281 lines), drawn inside the tutor's message once a set is graded.
- **Matches:** a card that stays in the thread, with the score as X of N and a row per problem, showing the learner's answer, the correct one and an explanation ([`learning-screen.md`](../../spec/learning-screen.md), The result).
- **Differs:** a row shows chosen and correct options, against the model answer and the missing point ([`mastery-check.md`](../../spec/mastery-check.md), Marking). There is no pass or "not yet" on the card.
- **Missing:** the problem sheet with the learner's own answer or photo; Dispute and its box; "You can dispute this when they're back." while checks are off ([`live-faults.md`](../../spec/live-faults.md)); the link from "Mastered in this session".
- **Stack:** Vue.
- **Size:** Medium: the card in the thread fits; the sheet and Dispute are new.

## Pictures

- **Old code:** none. Mermaid is not a dependency, and nothing draws a graph. KaTeX draws maths in replies, which the spec does not mention.
- **Missing:** diagrams drawn from Mermaid text and graphs drawn from SymPy's points, each with a caption ([`learning-screen.md`](../../spec/learning-screen.md), Pictures).
- **Size:** Large: nothing exists, though the module is small.

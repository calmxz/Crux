# The owner screens' modules against the old frontend

Part of [the old frontend comparison](../old-frontend-comparison.md) (#768). The modules are the ones in [`owner-screens.md`](../../spec/owner-screens.md) (Frontend modules). The size key and the sizing rule are in the index.

The old frontend has no owner page, no admin route and no role check. A search of `frontend/src/` for "owner", "admin", "trial" and "guest" finds two code comments and one error string, for the backend's missing Supabase admin setup on account delete. The backend has no owner routes either (see [#749](https://github.com/calmxz/Crux/issues/749): Safety, Feedback and Email have no old code). Each of the eight modules below has no old code, so each gap is large.

| Module | Old code | What is missing ([`owner-screens.md`](../../spec/owner-screens.md)) | Size |
|---|---|---|---|
| Owner shell | None | Its own address, the top bar with "Back to Crux", the menu and the phone's tab row with counts, "Page not found" for everyone else, the sign-in hop for email links, the Owner link at the sidebar foot (Reaching it; Layout) | Large: nothing exists |
| Owner today | None | What needs the owner, in the daily email's order, each line opening its item | Large: nothing exists |
| Owner trial | None | Requests with Approve and Decline, trial links with Switch off and its reason, dead links, the end of the trial with its move and take-back (Trial) | Large: nothing exists |
| Owner safety | None | Flags with the session reader beside the list; warn, dismiss and close dialogs; "Mark 'Reported'"; misuse closures and contests; "Enter a request" with its four kinds; the reported hold; the breach form (Safety) | Large: nothing exists |
| Owner feedback | None | Answers with unread marks, quotes with "Mark published" and "Mark removed", shared sessions with the reader (Layout) | Large: nothing exists |
| Owner counts | None | The go-public bar, "Start the window" with its same-day undo, the path, arrivals by source, the other counts (Layout) | Large: nothing exists |
| Owner money | None | The budget and the ceiling, Google's bill, the limits, the raise dialog with its tick, the learner cap and the let-in list (Money and switches) | Large: nothing exists |
| Owner switches | None | A switch per part and for guest mode, with their confirms and the "A fix passed the test" tick, and re-mark progress (Money and switches) | Large: nothing exists |

Pieces of the old frontend that do a similar job elsewhere, as facts only:

- A list beside an open item has no old example. The nearest layout is the session screen's conversation beside a right-hand panel (see [Session screen](learning-screen.md#session-screen)).
- Confirm dialogs that name what will happen are PrimeVue `ConfirmDialog` and `Dialog` (End session, Delete file, Delete account).

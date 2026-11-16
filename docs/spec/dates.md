# Dates

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers when a printed date takes effect, when Crux acts on it, how an outage moves it, and the one daily job. Email sending and the owner's daily email are in [`operations.md`](operations.md) and [`email.md`](email.md).

## Counting a date

- A printed date holds through 11:59 pm Philippine time on that date ([#763], [#772]).
- **A chance to act** (the undo of a closing, the contest of a misuse closure, the notice periods, the trial's end, Crux closing, a copy link) starts at a moment, in Philippine time. For an email, that moment is when Resend accepts it. Its last day is that moment's Philippine date plus the period, so it lasts from the period to about a day more. Ana closes her account at 2:00 pm on 3 Nov: she can keep it until 11:59 pm on 10 Nov, which is 7 days 9 h 59 min ([#772]).
- Stated lengths ("7 days to contest", "works for 7 days", "14 days ahead") are floors, so they stay as written ([#772]).
- A date the owner picks is a last day too: the trial's end, at the earliest today plus 7, and Crux closing ([#772]).
- **A keep-limit**, how long Crux keeps something nobody acts on, such as a trial request's "at most 30 days", is a ceiling. It is erased at the last daily run within it: the run on the start's Philippine date plus the limit, or the day before when the start comes before that day's run. Dana asks for a trial place at 3:00 pm on 1 Nov: her email goes at 8:05 am on 1 Dec, after 29 days 17 h 5 min. It runs longer only while the daily job is down, as the Privacy Policy says (see [`terms-and-policy.md`](terms-and-policy.md)) ([#772]).
- A copy is both: its link works until 11:59 pm on the 7th day after Resend accepts it, and the copy is erased at the next run. Ben's link, accepted at 8:05 am on 11 Nov, works until 11:59 pm on 18 Nov ([#772]).

## Notices that wait for email

- A notice period starts when Resend accepts its email, not on its planned date. This covers the idle warnings' 30 and 7 days, the 7 days to contest a misuse closure, the terms' 14 days, the 2 days after an erasure warning, and a closing started from an emailed request ([#735], [#755], [#772]). A closing from Close account starts at the learner's tap.
- Until then, a screen shows the last day as if the email went now. Once Resend accepts it, the date moves to the acceptance date plus the period, if that is later. A shown date only ever moves later, and no email says so ([#772]).
- If one of Crux's own notices is still not accepted 30 days after it was planned, the owner is told, in the owner page's Today area and by a push, and its period starts that day as if it went. Ana's misuse closure on 3 Nov, with every email refused for a month, gets 10 Dec as her last day and is erased on 12 Dec. If the email is accepted later after all, the date still moves as above ([#735], [#772]).
- An action asked for by email, deleting an account or erasing a session, never goes ahead until its email to the account's address is accepted, since a request's sender can be faked. If it is not accepted within 7 days of the owner entering the request, the owner page asks the owner to write a new email, never a reply, to the account's address from the Crux inbox, with a one-time 6-digit code the page makes, since a forged request's Reply-To could be the forger's. When the learner's reply agrees to the request and quotes the code, the owner types it back, the request is confirmed, and its period starts then. From then, Crux's queued email prints that last day, and its acceptance moves nothing. A reply with no code or a wrong one confirms nothing, since anyone can fake a From address, and nor does a reply that refuses, even quoting the code. The code dies after 5 wrong tries, after 30 days, and when the request is confirmed or cancelled, Crux's own email is accepted first, or the learner keeps the account; the owner page can make a new one. Bea asks to delete her account on 3 Nov, Resend refuses until 10 Dec, and she confirms on 11 Nov: her last day is 18 Nov ([#772]).
- A copy asked for by email waits for Resend. If it can't go within the month the Privacy Policy promises, the owner replies from the Crux inbox to say it is delayed. Any copy whose email is still not accepted 30 days after it was made is erased, and the owner is told ([#772]).

## Past the last day

- From 12:00 am Philippine time after the last day, the date has passed. Each request checks it, so the edge does not wait for the run: "Keep my account" is gone, a trial link has ended, "Request access" closes and the owner's Approve is greyed, an invite not yet accepted by Resend is not sent, and a copy page shows its expired message. Once the trial's end has passed, the owner can no longer move it or take it back. The data stays stored until the run erases it ([#772]).
- A closing, an idle account or a misuse closure past its last day opens to its card, with Sign out only and no "Read my sessions" (see [`account-screens.md`](account-screens.md)). A contest entered before the last day keeps the lock as it is; one entered after it brings the lock and its reading back ([#772]).
- A contest, or a reply to an erasure warning, counts when it reaches the Crux inbox by 11:59 pm on the last day, by the inbox's received time. The owner can enter it until the run that would act. One that arrives later is late. The owner can still cancel a waiting erasure warning ([#755], [#772]).

## When Crux acts

- A closing and an idle account are erased at the first run after the last day: day 9 for a closing, so Ana's goes at 8:05 am on 11 Nov, with any copy made and sent then ([#677], [#772]).
- A misuse closure, including one decided on a sealed flag, and an erasure warning wait one more run. The first run after the last day reminds the owner (see [`operations.md`](operations.md)), and the run after it acts, even after a missed run. A closure on 3 Nov is erased at 8:05 am on 12 Nov: day 10. An erasure warning accepted at 3:00 pm on 13 Mar has its last day on 15 Mar, and the session goes on 17 Mar. A closure with a contest entered waits for the owner's decision instead ([#753], [#772]).
- A closure the owner keeps is erased at the run its last day sets, or at the next run if that has passed ([#755], [#772]).
- Requests still waiting when the trial ends are declined at the first run after its last day ([#717], [#772]).
- When Crux closes, it erases every account only once each copy asked for by its last day, by the inbox's received time, has been made and its link has ended. The copy page stays up until then ([#677], [#772]).

## What a line says

- In a learner's line, a printed date names the last day, never the day Crux acts, which is "after that": "To contest this, reply by 11:59 pm on 10 Nov, Philippine time. After that, your account is erased." No line prints the hour of an erasure. A line that sets a deadline prints the time, on screen in the learner's own clock and in emails in Philippine time ([#763], [#772]).
- Past dates use the same clocks and print no time. Carla in New York sees "On 4 Mar the owner took no action." on her card and "On 5 Mar" in her email, for a decision at 2:00 am on 5 Mar, Philippine time. A deadline that has passed keeps its time: "Your time to contest ended at 10:59 am on 10 Nov." ([#772]).
- The owner's lines are in Philippine time, and may name the day Crux acts, as "erased on". A bare date that ends something a learner can do is a last day. Dates of past events, such as "Asked 2 Nov", stay as they are ([#772]).

## When Crux is down

- The database endpoint that the uptime checks call (see [`operations.md`](operations.md)) stores when it last answered, at most once a minute: at most 1,440 writes a day, and 864 from the checks alone (3 places, 12 times an hour) ([#772]).
- An answer after a gap of 15 minutes or more ends an **outage**. Each outage is recorded once, keyed by its start, with its end updated while it lasts ([#772]).
- Outages move every chance to act they overlap, including one that started during an outage. A date's move is the total outage time within its period, 1 day for each started 24 hours of that total, set to the new total and never added to. So four 20-minute outages in one period move it 1 day, and a long outage first seen partway still reaches its full move. For a misuse closure or an erasure warning, the period runs to the run that acts, so an outage counts once, not once for the last day and again for the run. Keep-limits don't move ([#772]).
- Ana's last day is 10 Nov. A 40-minute outage that day, or one from 11:50 pm on 10 Nov to 12:30 am on 11 Nov, moves it to 11 Nov ([#772]).
- The move happens before anything acts on a date: the first answer after an outage makes it, and before the daily job acts, and before a request is refused as past its last day, Crux checks the stored time and makes any move first. A missed run with the app up moves nothing; its actions run at the next run ([#772]).
- No email tells the learner. The screen shows the new date, and a moved trial end shows "The trial now ends at 11:59 pm on 16 Jan.", in the holder's clock. The owner's daily email says what moved (see [`operations.md`](operations.md)) ([#772]).
- Each move joins the restore log as the new last day per ID, and so does a move when Resend accepts a notice email. After a full restore, the release script resets the stored time (see [`backups-and-releases.md`](backups-and-releases.md)) ([#772]).

## The daily job

All scheduled work runs in one job: Cloud Scheduler calling the tasks service, at 8:05 am Philippine time, 5 minutes after Resend's day restarts ([#763]). Cloud Scheduler is free for up to 3 jobs per billing account, and 2 go to the peak schedule if the fallback in [`hosting.md`](hosting.md) is ever used ([#716], [#728] Answer 7).

The job acts on every date that has passed, so a missed run catches up on the next one. Dates that give someone a chance to act first gain any outage days, as "When Crux is down" says ([#735], [#762], [#772]). It does:

**Backups and reports**

- the daily database dump ([#716], [#728] Answer 7);
- the bill comparison and the daily email ([#717]);

**Email due**

- "it's back" emails on the 1st, and any email waiting for its share ([#675], [#735]);
- idle accounts' warnings at 30 and 7 days ([#677]);
- the 30-day request declines ([#717], [#728] Answer 7);

**Erasure**

- accounts past their 7-day undo, making and sending any copy asked for first ([#677], [#728] Answer 7, [#733], [#735]);
- misuse closures and erasure warnings one run after the owner's reminder, unless a contest holds them ([#733], [#772]);
- idle accounts at 12 months, once their warnings have run ([#677], [#735]);
- a copy and its address after its link's last day, or 30 days after it was made if its email never went ([#735], [#772]);
- "email me if spots open" addresses at 3 months, and the misuse block's scrambled email at 12 months ([#677]);
- a decline's saved details once it drops out of the 7 days with no flag; kinds waiting for a misuse card or a switched-off link's first showing, at the last run within 30 days of the owner's decision (see [`misuse.md`](misuse.md)) ([#733], [#764], [#776]);
- a withdrawn quote's words at 14 days, if its account has gone ([#677], [#735]);
- a dead trial link's stub, at the trial's end or 12 months after the link died, whichever comes first ([#719]);
- a dead trial link's feedback answers and quote permissions (not after a Yes or its holder's erasing, which remove them at once), 6 months after the trial ends or 12 months after the link died, whichever comes first, unless published ([#719]);
- any scrambled "told Crux is full" email or listed bucket object that its Cloud Tasks job or the erasure missed, and any copy object with no record ([#719]);
- per-account spend, rolled into totals with no account ([#677]);

**Ending things**

- let-in entries at the last run within their 7 days, not used or kept. Sign-up ignores an entry from 8:05 am on that day, even if the run is missed ([#679], [#728] Answer 7, [#772]);
- the trial, at the first run after its last day ([#733], [#772]);
- hand blocks at least 12 hours old (see [`security.md`](security.md)) ([#770]).

**The exceptions:** records with a shorter life than a day cannot wait for this job. Network addresses in the code limits, the wrong-link counts and the copy page's wrong-code counts, and the code limits' email addresses, are each deleted by a Cloud Tasks job set for when they expire ([#717], [#735], [#770]). Sign-in codes expire by checking their time when used. The daily job sweeps anything these missed, such as during a pause, and an unused code's email ([#735]). Email retries are Cloud Tasks set for their time too, so they need no Cloud Scheduler job (see "When Resend refuses or is down" in [`email.md`](email.md)) ([#763]).

Some things happen by the date alone, with no job: a re-run's budget returning on the 1st, and the go-public bar judged at the end of its last day ([#676], [#734], [#735]).

## On screen

The cards, emails and lines that print these dates are in [`account-screens.md`](account-screens.md), [`landing-screens.md`](landing-screens.md) and [`owner-screens.md`](owner-screens.md) ([#753], [#755]).

[#675]: https://github.com/calmxz/Crux/issues/675
[#676]: https://github.com/calmxz/Crux/issues/676
[#677]: https://github.com/calmxz/Crux/issues/677
[#679]: https://github.com/calmxz/Crux/issues/679
[#716]: https://github.com/calmxz/Crux/issues/716
[#717]: https://github.com/calmxz/Crux/issues/717
[#719]: https://github.com/calmxz/Crux/issues/719
[#728]: https://github.com/calmxz/Crux/issues/728
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#753]: https://github.com/calmxz/Crux/issues/753
[#755]: https://github.com/calmxz/Crux/issues/755
[#762]: https://github.com/calmxz/Crux/issues/762
[#763]: https://github.com/calmxz/Crux/issues/763
[#764]: https://github.com/calmxz/Crux/issues/764
[#770]: https://github.com/calmxz/Crux/issues/770
[#772]: https://github.com/calmxz/Crux/issues/772
[#776]: https://github.com/calmxz/Crux/issues/776

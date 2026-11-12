# The landing screens' modules against the old frontend

Part of [the old frontend comparison](../old-frontend-comparison.md) (#768). The modules are the ones in [`landing-screens.md`](../../spec/landing-screens.md) (Frontend modules). Old paths are under `frontend/src/`. The size key and the sizing rule are in the index.

The old app has no page for a visitor without an account. Every route except sign-in, sign-up, password reset, the two legal pages and "Page not found" sends a signed-out visitor to `/login` (`router/index.js`). The backend has no guest or trial link either (see [#749](https://github.com/calmxz/Crux/issues/749)).

## Landing page

- **Old code:** only `views/NotFoundView.vue`: "Page not found", "Nothing is written at this address." and "Back home". `views/LegalView.vue` draws the Terms of Service and Privacy Policy from Markdown in `legal/`, which the landing page's footer would link to.
- **Matches:** a page for an unknown address, shown without the app around it ([`landing-screens.md`](../../spec/landing-screens.md), The landing page: "This page doesn't exist." with "Go to Crux").
- **Missing:** the guest's start box with the limit line; the sample chips; the demo video and the 18+ line; the Request access section and top bar button; the region, wake ("Starting the tutor…"), unreachable, stopped, after-trial and opening states; "Who runs Crux".
- **Stack:** Vue.
- **Size:** Large: only the not-found page exists.

## Entry ticks

- **Old code:** none. The nearest is the one consent box on the sign-up page (see [Sign-in](account-screens.md#sign-in)).
- **Missing:** the two ticks inside the start box, or in the chat box's place on a trial link; held once per browser; shown again when the Trial Terms change or after Yes to the age question ([`trial.md`](../../spec/trial.md); [`landing-screens.md`](../../spec/landing-screens.md), Trial links).
- **Size:** Large: nothing exists.

## Guest mode

- **Old code:** none.
- **Missing:** the guest sidebar ("Your topic", "This tab only", "Sample topics", Request access); "7 of 10 replies left"; the 10-reply line and its buttons; the sample's end line; the upload refusal; the guest stops; the session ended by a block; going back to the landing page after Yes ([`landing-screens.md`](../../spec/landing-screens.md), Guest mode; Guest stops).
- **Size:** Large: nothing exists.

## Request access

- **Old code:** none.
- **Missing:** the page with the email, the human check, "I am 18 or over" and Send request; "Request received"; the region message under Send; "Back to Crux" to where the visitor came from ([`landing-screens.md`](../../spec/landing-screens.md), Request access).
- **Size:** Large: nothing exists.

## Trial link

- **Old code:** none.
- **Missing:** opening from the link, with the key leaving the address bar ([`quality-bar.md`](../../spec/quality-bar.md), The trial); the one-time device banner; the notice pages; the ended pages; the locked link's wording; the opening order ([`landing-screens.md`](../../spec/landing-screens.md), Trial links).
- **Size:** Large: nothing exists.

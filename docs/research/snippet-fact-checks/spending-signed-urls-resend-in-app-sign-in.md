# Spending and hosting: signed URLs, Resend size and in-app browsers

Part of [Spec facts that rested on search snippets](../snippet-fact-checks.md), checked on 2026-11-11 for #762.

## 3. A GCS V4 signed URL lasts 7 days at most

**Spec says:**

- `operations.md:43`: "The link is signed when the email goes out, so a delayed email cannot use it up. Google's signed links last at most 7 days, so that is how long it works ([#735])."
- `operations.md:41`: the daily job makes the closing copy "and sends the link itself". `operations.md:42`: for an emailed request, the owner "runs the script".
- `privacy.md:55`: "emails a private link that works for 7 days from when it is sent". `privacy.md:85`, `privacy.md:86`, `privacy.md:122` and `privacy.md:135` repeat the 7 days.
- `account-screens.md:103`: "as a private link that works for 7 days." `quality-bar.md:90`: "A day-8 copy, with a 7-day link signed when the email goes."
- `hosting.md:180`: "Google's own services use service accounts, with no stored keys". `ai-layer.md:20`: "No Google key is stored anywhere."

**Source:**

- Cloud Storage, "Signed URLs", `https://cloud.google.com/storage/docs/access-control/signed-urls`. "Last updated 2026-10-30 UTC."
- Cloud Storage, "V4 signing process with your own program", `https://cloud.google.com/storage/docs/access-control/signing-urls-manually`. "Last updated 2026-11-07 UTC."
- Google Cloud SDK reference, "gcloud storage sign-url", `https://cloud.google.com/sdk/gcloud/reference/storage/sign-url`. "Last updated 2026-05-27 UTC."
- Cloud Storage, "Signing URLs with helpers" (the client-library page), `https://cloud.google.com/storage/docs/access-control/signing-urls-with-helpers`. "Last updated 2026-11-07 UTC." It has no 12-hour or 7-day text. Its samples sign for 5 to 15 minutes.

**Page says:**

- Signed URLs: "X-Goog-Expires: The length of time the signed URL remained valid, measured in seconds from the value in X-Goog-Date. … The longest expiration value is 604800 seconds (7 days)."
- Signed URLs: "Anyone who knows the URL can access the resource until the expiration time for the URL is reached or the key used to sign the URL is rotated."
- V4 signing sample: "Expiration Time can't be longer than 604800 seconds (7 days)."
- gcloud sign-url, `--duration`: "The max duration allowed is 12 hours. This limitation exists because the system-managed key used to sign the URL may not remain valid after 12 hours. Alternatively, the max duration allowed is 7 days when signing with either the --private-key-file flag or an account that authorized with gcloud auth activate-service-account."

**Verdict: partly.** 7 days is the V4 maximum. But the spec signs without stored keys. A keyless signature goes through the Service Account Credentials API (`signBlob`), which the IAM page says uses Google-owned and managed key pairs. Google's own tool caps such a signature at 12 hours, because the key "may not remain valid after 12 hours". The Signed URLs page agrees that a rotated key ends the link early. So a 7-day link signed by the daily job on Cloud Run, or by the owner's script through impersonation, may stop working well before 7 days. The 12-hour text is only on the gcloud page. The helpers page does not repeat it, but the reason gcloud gives applies to any signature made with a managed key.

**Fix:** this is a choice for the owner, so this note gives options rather than wording.

- Keep 7 days and no stored keys: email a link to Crux, not to the bucket. Crux checks the link's token for 7 days, then hands out a fresh short signed URL on each click. `operations.md:43` then reads: "The email holds a link to Crux that works for 7 days from sending. Each click gets a new download link from Google that lasts a few minutes."
- Keep a bucket link for 7 days: store one service-account key for signing only. This is a recorded change to `hosting.md:180` and `ai-layer.md:20`.
- Shorten the link to 12 hours: change every 7-day line above, including the Privacy Policy text at `privacy.md:135`.

Files to fix under any option: `operations.md:43`, and the 7-day promises at `privacy.md:55`, `privacy.md:85`, `privacy.md:86`, `privacy.md:122`, `privacy.md:135`, `account-screens.md:103` and `quality-bar.md:90` if the period changes. Decision this touches: #735 ("**Copies of data:** a private link that works for 7 days"). The second option also changes #716's "service accounts, no stored Google keys".

**Also on the page:** the IAM page "Service account credentials" (`https://cloud.google.com/iam/docs/service-account-creds`, "Last updated 2026-11-07 UTC") says "Google-owned and managed key pairs are used by the Service Account Credentials API, and by Google Cloud services such as App Engine and Compute Engine, to generate short-lived credentials for service accounts." It also says "Google-owned and managed keys that are actively used for signing are rotated regularly according to security best practices. The rotation process is probabilistic". It gives no fixed period.

## 4. Resend allows 40 MB per email

**Spec says:** nothing. The spec never sends a copy as an attachment. #735 rejected it: "Attaching a small copy: learner data in Resend's log." The spec relies on Resend's limits at `operations.md:8`: "Resend Free sends Crux's email from the domain: 100 a day and 3,000 a month".

**Source:**

- Resend docs, "Attachments", `https://resend.com/docs/dashboard/emails/attachments`. Page metadata `dateModified` 2026-11-05.
- Resend API reference, "Send Email", `https://resend.com/docs/api-reference/emails/send-email` (read as `.md`).
- Resend knowledge base, "What are Resend account quotas and limits?", `https://resend.com/docs/knowledge-base/account-quotas-and-limits`. Page metadata `dateModified` 2026-11-05.

**Page says:**

- Attachments: "Emails can be no larger than 40MB (including attachments after Base64 encoding)."
- Send Email: "Filename and content of attachments (max 40MB per email, after Base64 encoding of the attachments)."

**Verdict: confirmed.** Base64 grows a file by about a third, so the largest file is about 30 MB. The 200 MB copy in #735's example would not fit either way.

**Also on the limits page, and bearing on `operations.md`:**

- "Transactional emails: daily email quota of 100 emails/day and 3,000 emails/month. … The daily quota is a UTC calendar day (00:00–24:00 UTC) and resets at midnight UTC. It is not a rolling 24-hour window from your first send or from when you hit the limit." Midnight UTC is 8 am Philippine time. The owner's daily email goes "about 8 am Philippine time" (`operations.md:92`), right at the reset. Crux's own day shares in the table under `operations.md:16` should count on the UTC day, or they drift from Resend's.
- "Both sent emails and received emails (inbound) count towards your account’s email quota." Crux's inbound mail goes through Cloudflare Email Routing (`operations.md:51`), so this does not bite unless Resend receiving is turned on.
- "Multiple To, CC, or BCC recipients in sent emails count as separate emails towards this quota."
- "All accounts start with a rate limit of 10 requests per second."

Section 3 of the snippet list owns the Resend limits, so these are flagged here, not fixed.

## 5. Google sign-in in the LinkedIn and Facebook in-app browsers

**Spec says:**

- `accounts.md:45` to `accounts.md:48`, under "Inside LinkedIn's or Facebook's built-in browser": "Both buttons show there ([#674])." "Crux detects the built-in browser where it can. Tapping Google there sends the learner to the same page in the phone's normal browser ([#674])." "On iPhone, or wherever the jump fails, Crux shows its own note, naming the app it is in: "Google sign-in doesn't work inside the LinkedIn app. Open this page in your browser, or use a code." ([#674])." "The code works inside these browsers ([#674])."
- `account-screens.md:25`: "Inside LinkedIn's or Facebook's browser | Continue with Google | The in-app note in `accounts.md`".
- `quality-bar.md:140`: "the Google button inside those two apps jumps to the phone's browser or shows Crux's note, never Google's error page."
- `trial.md` has no in-app line. The trial has no Google sign-in.
- The decision #674 states the fact: "A shared link opens there by default, and Google refuses sign-in there ("Error 403: disallowed_useragent")." The spec does not quote the error.

**Source:**

- Google for Developers, "Using OAuth 2.0 for Web Server Applications", `https://developers.google.com/identity/protocols/oauth2/web-server`. "Last updated 2026-10-30 UTC." Read with a plain fetch and again in a browser, to check for hidden tabs.
- Google for Developers, "OAuth 2.0 Policies", `https://developers.google.com/identity/protocols/oauth2/policies`. No date shown.
- Supporting only: Google Developers Blog, "Upcoming security changes to Google's OAuth 2.0 authorization endpoint in embedded webviews", 2021-06-29.

**Page says:**

- Web Server Applications, "Errors": "disallowed_useragent The authorization endpoint is displayed inside an embedded user-agent disallowed by Google's OAuth 2.0 Policies." It goes on: "Web developers may encounter this error when an iOS or macOS app opens a general web link in an embedded user-agent and a user navigates to Google's OAuth 2.0 authorization endpoint from your site." The browser-rendered page shows only this iOS and macOS wording, with no Android text.
- Policies, "Use secure browsers": "A developer must not direct a Google OAuth 2.0 authorization request to an embedded user-agent under the developer's control. Embedded user-agents include, but are not limited to, software libraries that allow a developer to insert arbitrary scripts, alter the default routing of a request to the Google OAuth server, or access session cookies."
- Blog (support only): "Embedded webviews implementing or extending Android WebView do not comply with Google's secure browser policy for its OAuth 2.0 Authorization Endpoint." It says the same for "WKWebView".

**Verdict: partly.**

- Confirmed: Google refuses sign-in in embedded user-agents with `disallowed_useragent`. The current docs say so for iOS and macOS web links. The 2021 blog covers Android WebView.
- Not on any Google page: that LinkedIn's and Facebook's in-app browsers are such user-agents. No Google page names either app. Whether they are embedded webviews is LinkedIn's and Meta's to say. One search of Meta's developer site, and one of LinkedIn's site and Microsoft Learn, found no first-party page on either in-app browser. So that half is unverified.
- No page I read shows "Error 403". The error code is right. The "403" in #674 is not confirmed.

**Fix:** none needed in the spec. The spec already makes it a real-phone test (`quality-bar.md:140`). If #674's text is ever quoted, drop "403" or confirm it on the phone.

## 6. An `intent://` link opens the system browser

**Spec says:** the spec does not name `intent://`. It relies on a jump that works: `accounts.md:46`: "Tapping Google there sends the learner to the same page in the phone's normal browser ([#674])." `quality-bar.md:140`: "This also settles whether LinkedIn's jump works on Android ([#678])."

**Source:**

- Chrome for Developers, "Android Intents with Chrome", `https://developer.chrome.com/docs/android/intents`. "Last updated 2023-12-12 UTC."
- Android Developers, "Build web apps in WebView", `https://developer.android.com/develop/ui/views/layout/webapps/webview`. "Last updated 2026-10-28 UTC."

**Page says:**

- Chrome: "You can launch apps directly from a web page on an Android device with an Android Intent. You can implement a user gesture to launch the app with a custom scheme or use the intent: syntax."
- Chrome: "Chrome won't launch an external app for a given Intent URI if: The Intent URI is redirected from a typed in URL; The Intent URI is initiated without user gesture."
- Android: "To open links tapped by the user, provide a WebViewClient for your WebView using setWebViewClient. All links the user taps load in your WebView. If you want more control over where a clicked link loads, create your own WebViewClient that overrides the shouldOverrideUrlLoading method."
- Android, after the example: "If the URL host doesn't match, then an Intent is created to launch the default Activity for handling URLs, which resolves to the user's default web browser."

**Verdict: unverified.** Chrome's page covers Chrome itself launching an app from an `intent:` link after a tap. It says nothing about links inside another app's browser. Android's page says the host app decides where a link goes. So whether LinkedIn's or Facebook's in-app browser hands an `intent://` link to the system browser depends on those apps. No page from LinkedIn or Meta says so. The owning page could not be found.

**Fix:** none. The spec names no mechanism and leaves the answer to the Android real-phone test. Whatever builds the jump should follow Chrome's rules: fire it only from a tap, and give a fallback URL.

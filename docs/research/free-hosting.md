# Research: free hosting options and their limits (#673)

Question: what can host Crux v1 for free, and what are the limits? Pieces: frontend (static SPA), backend API (Python, long-lived SSE streams), Postgres with pgvector, file storage for uploads, sign-in (open sign-up, email and Google).

Every claim below comes from an official pricing, limits, docs or terms page, all read on **2026-10-20**. Numbers in square brackets point to the source list at the end. Where a page was silent, the table says "not stated", and nothing is filled in from memory.

## Short answer

Crux v1 can run for $0. The usable combinations are a static host (Cloudflare is the cleanest), Render Free or Koyeb Free for FastAPI, and Supabase Free or Neon Free for Postgres with pgvector. Supabase and Neon each also bundle auth and file storage. Three limits matter most for a demo shared on social media:

1. **Idle spin-down.** Every free backend and database sleeps when idle. Render's ~1-minute wake-up hurts most. Supabase's 7-day pause is the worst: someone has to resume the project by hand.
2. **Timeouts that cut a streamed reply.** Koyeb closes HTTP connections at 100 s and Vercel Hobby functions at 300 s. Cloud Run allows up to 60 min and Render up to 100 min.
3. **Email for open sign-up.** Supabase's built-in email only sends to the project's own team, at 2 messages per hour. Open email sign-up needs your own email sender (for example Resend Free: 100/day, 3,000/month).

Commercial use: Vercel Hobby forbids it outright, and GitHub Pages forbids SaaS. Render and Koyeb say their free tiers are not for production. No other terms page I read restricts free tiers to non-commercial use.

---

## (a) Frontend: static / SPA hosting

| Option | Sleep / inactivity | Monthly limits | Storage / bandwidth | Card | Commercial use | Src |
|---|---|---|---|---|---|---|
| **Cloudflare** (Workers static assets, or Pages) | None (static) | Pages Free: 500 builds/month, 1 build at a time, 20-min build timeout. "Requests to static assets are free and unlimited." | Pages Free: up to 20,000 files per site. Bandwidth: no cap stated for static assets. | Not stated | No non-commercial clause found in the Cloudflare terms (searched "non-commercial", "personal use") | [1][2][3] |
| **Netlify Free** | None, but when credits run out "all of your web projects (sites/apps) are paused" | **300 credits/month, hard limit.** 15 credits per production deploy, 20 credits per GB of bandwidth, 2 credits per 10,000 web requests | Comes out of the same 300 credits (300 credits = 15 GB if spent on nothing else) | Not stated for Free ("Netlify only accepts credit cards" for paid plans) | No "commercial" or "personal use" wording found in the terms of use. Pricing page says "From side projects to enterprise." | [4][5][6][7] |
| **GitHub Pages** | None | Soft limit of 10 builds/hour (not applied to custom Actions builds) | 1 GB site max, 100 GB/month soft bandwidth | Not stated | **Prohibited for SaaS:** "not intended for or allowed to be used as a free web-hosting service to run your online business ... or providing commercial software as a service (SaaS)". Also: "shouldn't be used for sensitive transactions like sending passwords" | [8] |
| **Vercel Hobby** | None. When a limit is exceeded, "you will have to wait until 30 days have passed" | 1,000,000 CDN requests, 1,000,000 function invocations | 100 GB Fast Data Transfer, 10 GB Fast Origin Transfer | Not stated | **Prohibited:** "Hobby teams are restricted to non-commercial personal use only. All commercial usage of the platform requires either a Pro or Enterprise plan." | [9][10] |
| **Render static site** | None (static) | Uses the workspace's included bandwidth and build minutes (Hobby: 500 build minutes/month) | **5 GB/month bandwidth on Hobby**, shared with any Render web service. Without a card on file, running out suspends all free services for the rest of the month | Optional (see note in (b)) | Free tier docs: "Do not use them for production applications" (a production caveat, not a commercial ban) | [11][12] |
| **Firebase Hosting (Spark)** | None, but sites are disabled if the transfer quota is exceeded, until next month or a move to Blaze | 10 GB storage | **The two official pages disagree:** pricing says data transfer is "No-cost up to 360 MB/day"; the Hosting quotas page says "up to 10 GB/month" | Spark: "No payment method needed" | Terms not reviewed | [13][14] |

Takeaway: Cloudflare has no bandwidth cap that bites, no pausing, and no non-commercial clause. Netlify's credit model is tight for a project that deploys often: 20 production deploys alone use all 300 credits, and then every site pauses.

---

## (b) Backend API: Python web server with long-lived SSE

| Option | Spin-down / cold start | Monthly limits | Bandwidth | **Timeout that cuts a stream** | Card | Commercial / production | Src |
|---|---|---|---|---|---|---|---|
| **Render Free web service** | Spins down after **15 min** with no inbound traffic. Wake-up "takes about one minute" (browsers get a loading page). Local files are lost on spin-down | 750 free instance hours per workspace; when they run out, all free services are suspended until next month. "Render might restart a Free web service at any time" | 5 GB/month on Hobby, then billed. With no card on file, all free services are suspended for the rest of the month instead | Up to **100 minutes** per HTTP response (stated on a marketing comparison page; no limits-doc page found) | Optional. Free docs describe what happens "if you haven't added a payment method" | "Do not use them for production applications." Terms mention "using the Service for commercial purposes" (arbitration clause), so commercial use is expected under the terms | [11][12][15][16] |
| **Koyeb Free instance** | Scales to zero after **1 hour** without traffic (cannot be disabled). Deep-sleep cold start "typically takes 1 to 5 seconds" | One free web service per organization: 512 MB RAM, 0.1 vCPU, 2 GB SSD, Frankfurt or Washington D.C. only. No volumes | 100 GB/month outbound free (not charged yet) | **100 s:** "The connection timeout for HTTP requests is set to 100 seconds." Can close a long streamed reply | **Required.** $29 pre-authorization hold. The default plan at sign-up is Pro ("you will be charged the pro-rated amount for Pro"); downgrade to Starter to stay free | "should not be used for production applications." No free-tier clause found in the terms. Site banner: "Koyeb is joining Mistral AI" | [17][18][19][20][21][22] |
| **Google Cloud Run** (request-based billing) | Idle instances are free. Keeping instances warm needs "minimum instances", billed at an idle rate, so otherwise expect cold starts. Cold-start time not stated on the pages read | Free tier per billing account per month: 180,000 vCPU-seconds, 360,000 GiB-seconds, 2 million requests | 1 GB outbound from North America per month | Default **5 min**, configurable up to **60 min** | **Required:** "Verify that billing is enabled for your Google Cloud project". Free Trial sign-up needs a card. Usage past the free tier is billed | Terms not reviewed | [23][24][25][26] |
| **Vercel Functions (Python, Hobby)** | Serverless functions (cold-start behaviour not quantified on the pages read) | 4 Active CPU-hours, 360 GB-hours provisioned memory, 1,000,000 invocations. Max 2 GB memory | 100 GB Fast Data Transfer (shared with the frontend) | **300 s maximum**, "including streamed responses", then a 504 | Not stated | **Non-commercial only** (see (a)) | [9][10][27][28][29][30] |
| **Cloudflare Workers (Python, Free)** | Serverless (no idle server) | 100,000 requests/day. **10 ms CPU per HTTP request**, 128 MB memory. FastAPI is listed among supported Python packages | Not stated | HTTP duration: "No limit" (waiting on the network does not count as CPU). The 10 ms CPU cap rules out PDF parsing on Free | Not stated | No non-commercial clause found [3] | [31][32][33] |

**Checked, not free:**
- **Hugging Face Spaces:** "Gradio and Docker Spaces run on compute and require a paid plan to create: PRO for personal accounts". PRO is $9/month. Only static Spaces and ZeroGPU Gradio Spaces stay free. [34][35]
- **Fly.io:** "Is there a free tier? No. New organizations don't have a free tier or a monthly free usage allowance." The trial lasts "up to 2 hours of Machine runtime or 7 days". [36]
- **Railway:** a 30-day trial with a one-time $5. After that, the Free plan gives "$1 of free credit per month", with at most 0.5 GB RAM and 1 vCPU per service. RAM costs $10/GB/month, so a service using 0.5 GB nonstop costs $5/month in RAM alone, and $1 covers about 6 days. [37][38]

Arithmetic (mine, from the numbers above):
- Render's 750 hours cover one always-on service for a month (744 h), not two.
- Cloud Run's 180,000 vCPU-seconds is 50 hours of 1-vCPU billable instance time per month. Concurrent requests share an instance's billable time.

Other Render limits that matter for Crux:
- Render "may suspend a Free web service that initiates an uncommonly high volume of traffic over the public internet". Its examples are calling an external database, external APIs, or object storage, which is exactly how Crux's backend works.
- Free services "can't send outbound network traffic on ports 25, 465, or 587", so email must go through an HTTP API. [11]

---

## (c) Postgres with pgvector

| Option | Sleep / cold start | Pausing or deletion | Monthly limits | Storage / egress | Card | Commercial / positioning | Src |
|---|---|---|---|---|---|---|---|
| **Supabase Free** | Always-on while active (shared CPU, 500 MB RAM) | **Paused after 7 days of low activity.** A warning email comes about a week before. Resume by hand in the dashboard, possible "for up to 1 year after it was paused". A few requests a day prevents it | 2 active free projects. "Continually" exceeding the Free quota can trigger Fair Use restrictions | 500 MB database per project, 5 GB egress + 5 GB cached egress. No backups on Free | Not stated on the pages read | "Perfect for passion projects & simple websites". No non-commercial clause found in the terms. pgvector: enable the "vector" extension | [39][40][41][42][43] |
| **Neon Free** | Scale to zero after **5 min** (cannot be disabled). Wakes "within a few hundred milliseconds" | No inactivity deletion. Running out of CU-hours or egress means "your compute is suspended until the next billing period". Hitting the storage cap makes writes fail. "None of these limits delete your data" | 100 projects, **100 CU-hours per project**, up to 2 CU. 100 CU-hours means always-on is impossible; scale-to-zero is what makes it fit | 1 GB per project (20 GB per account), 5 GB egress per project | "No credit card required" | "Free: Prototypes, side projects, and small teams". No non-commercial clause found in the terms. pgvector supported (HNSW, IVFFlat) | [44][45][46][47][48] |
| **Aiven Free (PostgreSQL)** | Dedicated VM, no scale-to-zero described | Aiven may "Power off free services with no initial usage within the first few hours" and "with no continuative activity" (notice sent first; you can power it back on) | 1 VM, 1 CPU, 1 GB RAM | 1 GB storage | "You don't need a credit card" | "use them indefinitely free of charge". pgvector listed. Terms not reviewed | [49][50][51] |
| **Koyeb Postgres free** | Sleeps after **5 min** idle | Not stated | One free instance (0.25 vCPU, 1 GB RAM), **5 hours of compute per month** | 1 GB | Required (account-wide, see (b)) | FAQ: databases are "in public preview ... do not rely on it for critical operations". pgvector 0.8.0 | [20][52][53] |
| **Render Postgres Free** | Not described | **Expires 30 days after creation**, whatever the activity. Then a 14-day grace period, then **deleted** | One free database per workspace. No backups, no connection pooling | 1 GB | Optional | "Do not use them for production". pgvector supported | [11][54] |

Arithmetic: Koyeb's 5 compute-hours are about 60 wake-ups of at least 5 minutes each, so it is a toy. Render's database is a 30-day trial, not a free tier.

---

## (d) Object / file storage for uploads (pdf/pptx)

| Option | Free amount | Egress | Ops | Card | Notes | Src |
|---|---|---|---|---|---|---|
| **Cloudflare R2** | 10 GB-month (Standard class) | Free, "no charges for egress" | 1M Class A, 10M Class B per month | **Effectively yes:** you need "an R2 subscription" through a checkout flow, and Cloudflare asks for "a valid payment method before ... enabling subscriptions" | S3-compatible | [55][56][57] |
| **Backblaze B2** | "First 10GB storage is always free" | Free up to 3x average monthly storage, then $0.01/GB | Class B and C transactions free | Not stated | S3-compatible | [58][59] |
| **Tigris** | 5 GB Standard | Free | 10,000 Class A, 100,000 Class B per month | "No card to start" | S3-compatible | [60] |
| **Supabase Storage** | 1 GB (Free plan) | Shares the project's 5 GB egress | Not stated | Not stated | **Max file size 50 MB on Free.** Pauses with the project | [39][61] |
| **Neon Object Storage** | 5 GB per project on Free | Shares the 5 GB per-project transfer allowance | No per-operation charge (paid plans) | No card | S3-compatible, in the same project as the database | [45] |
| **Vercel Blob (Hobby)** | 1 GB | 10 GB data transfer | 10,000 simple, 2,000 advanced operations | Not stated | Vercel's Hobby non-commercial rule applies | [62][10] |
| **Google Cloud Storage** | 5 GB-months (US regions only) | 100 GB from North America per month | 5,000 Class A, 50,000 Class B | Billing account needed | Always Free tier | [25] |

Checked, not free: **Cloud Storage for Firebase** "now requires projects to be on the pay-as-you-go Blaze pricing plan" [63]. The **AWS** Free plan is credit-based ("up to $200"), and the account "closes on its own 6 months after you open it or when your credits run out" [74].

---

## (e) Sign-in: open sign-up with email and Google

| Option | Free MAU | Google / social | Email delivery | Card | Commercial / notes | Src |
|---|---|---|---|---|---|---|
| **Supabase Auth** | 50,000 MAU | Social OAuth included on Free | **Built-in SMTP: 2 messages/hour, and only to the project's team** ("Email address not authorized" for anyone else). Open email sign-up needs custom SMTP | Not stated | Pauses with the project (see (c)) | [39][64][65] |
| **Firebase Auth (with Identity Platform, Spark)** | 50K MAU (pricing). Spark daily limit: 3,000 Tier 1 daily active users | Social is a Tier 1 provider | Sends its own mail: 10,000 verification links/day, 1,500 password resets/day, 20,000 sign-in links/day. New accounts limited to 100/hour per IP | Spark: no payment method | Terms not reviewed | [13][66][67] |
| **Clerk Hobby** | 50,000 monthly retained users per app | Up to 3 social connections (Google, GitHub, ...) | Not stated | "No credit card required" | "Secured by Clerk" branding can't be removed on Hobby. No free-tier restriction found in the terms | [68][69] |
| **Auth0 Free** | 25,000 MAU | "Unlimited Social Connections" Delivery limits not stated. The "Email Workflow" feature row says "Not included" on Free | "No credit card needed" (a card is needed for a custom domain) | Terms not reviewed | [70] |
| **Kinde Free** | 10,500 MAU | "Email, SMS and social login" | Not stated | "No credit card required" | Marketed "Perfect for hobbyists and personal projects". Terms page 404, not reviewed | [71] |
| **Neon Auth (Managed Better Auth)** | Up to 60,000 MAU on Free | Google, GitHub, Vercel. "Google OAuth is enabled by default with shared credentials for development and testing". "For production, add your own Google Client ID and secret" | "sends verification codes, magic links, and password reset emails using its built-in email provider" (sending limits not stated). Custom SMTP is optional | No card | "currently available for AWS regions only". Users stored in your own Neon Postgres | [45][72][75][76][77] |

Email sender for custom SMTP: **Resend Free** sends 3,000 emails/month with a daily limit of 100 [73]. On Render Free it has to be used over HTTP, because SMTP ports are blocked [11].

---

## Free combinations that work together

### A. Cloudflare static + Render Free (FastAPI) + Supabase Free (DB, pgvector, Auth, Storage) + Resend Free

- Everything except Render is always-on until Supabase's 7-day pause. Render streams up to 100 min. Supabase gives Google sign-in, 1 GB of uploads (50 MB per file) and 500 MB of database.
- **Main risk:** the first visitor after 15 idle minutes waits about **1 minute** for Render to wake. That is the likely first impression from a LinkedIn click.
- **Other risks:**
  - Email sign-up does not work for strangers until custom SMTP (Resend) is set up.
  - If the post goes quiet for a week, Supabase pauses the project, and someone must resume it from the dashboard.
  - Render's 5 GB/month bandwidth with no card means all free services are suspended for the month. Render's "service-initiated traffic" suspension clause covers exactly this backend shape.
- Cards needed: no documented step requires one. Render says a card is optional; Supabase, Cloudflare static and Resend pages say nothing either way.

### B. Cloudflare static + Koyeb Free (FastAPI) + Neon Free (DB, pgvector, Auth, Object Storage)

- Cold starts are short: Koyeb 1-5 s after 1 h idle, Neon a few hundred ms after 5 min. Nothing pauses for inactivity. Neon bundles auth (60k MAU, Google sign-in, built-in email for verification and reset; production Google needs your own OAuth client; AWS regions only) and 5 GB of object storage.
- **Main risk:** Koyeb's **100-second HTTP connection timeout** can cut off a long streamed tutor reply partway through.
- **Other risks:**
  - Koyeb needs a card. Sign-up defaults to Pro and charges a pro-rated fee unless you switch to Starter.
  - The free instance is 0.1 vCPU / 512 MB, which is slow for parsing PDF/PPTX uploads.
  - When Neon's 100 CU-hours or 5 GB of egress run out, compute is suspended until next month, with no throttling first.
  - Koyeb is "joining Mistral AI".
- Cards needed: Koyeb.

### C. Cloudflare static (or Firebase Hosting) + Google Cloud Run (FastAPI) + Neon or Supabase + R2, B2 or Tigris + Firebase Auth (or the database vendor's auth)

- Cloud Run streams for up to 60 min and scales to zero. Firebase Auth sends its own verification emails within daily quotas, so no SMTP is needed.
- **Main risk:** billing has to be enabled, so if the post spreads, usage past the free tier is charged to the card instead of stopping.
- **Other risks:** cold starts with no warm instance unless you pay for minimum instances, and the most moving parts of the three.
- Cards needed: Google Cloud (R2 also needs one if chosen; B2 or Tigris avoid it).

### Not recommended for v1

- **Vercel Hobby:** a later paid launch breaks its non-commercial rule, and its 300 s function limit applies to streamed responses.
- **GitHub Pages:** its SaaS ban.
- **Render Postgres:** deleted after 30 + 14 days.
- **Koyeb Postgres:** 5 hours of compute per month.
- **Hugging Face, Fly.io, Railway:** not actually free (see (b)).

## Could not verify

- Render's 100-minute response limit comes from a marketing comparison page [15]. No limits-doc page states it.
- Render's free instance CPU/RAM did not appear in the pricing page text.
- Cold-start durations for Cloud Run and Vercel are not quantified on the pages read.
- Card requirements for Supabase, Netlify, Cloudflare static, B2, Vercel Hobby and Resend: not stated on the pages read.
- Email sending limits for Clerk, Auth0, Kinde and Neon Auth: not stated on the pages read.
- Terms of service not reviewed: Google/Firebase, Aiven, Auth0, Kinde (404), Backblaze, Tigris.
- Firebase Hosting transfer: 360 MB/day [13] vs 10 GB/month [14], an unresolved conflict between two Google pages.

## Sources (all read 2026-10-20)

1. Cloudflare Pages limits: https://developers.cloudflare.com/pages/platform/limits/
2. Cloudflare Workers static assets billing: https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/
3. Cloudflare terms: https://www.cloudflare.com/terms/
4. Netlify pricing: https://www.netlify.com/pricing/
5. Netlify, how credits work: https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/how-credits-work/
6. Netlify credit-based plans: https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/credit-based-pricing-plans/
7. Netlify terms of use: https://www.netlify.com/legal/terms-of-use/
8. GitHub Pages limits: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
9. Vercel Hobby plan: https://vercel.com/docs/plans/hobby
10. Vercel fair use guidelines: https://vercel.com/docs/limits/fair-use-guidelines
11. Render, Deploy for Free: https://render.com/docs/free
12. Render pricing: https://render.com/pricing
13. Firebase pricing: https://firebase.google.com/pricing
14. Firebase Hosting usage quotas: https://firebase.google.com/docs/hosting/usage-quotas-pricing
15. Render vs Heroku (marketing comparison): https://render.com/docs/render-vs-heroku-comparison
16. Render terms: https://render.com/terms
17. Koyeb instances: https://www.koyeb.com/docs/reference/instances
18. Koyeb scale-to-zero: https://www.koyeb.com/docs/run-and-scale/scale-to-zero
19. Koyeb edge network (timeouts): https://www.koyeb.com/docs/reference/edge-network
20. Koyeb pricing FAQ: https://www.koyeb.com/docs/faqs/pricing
21. Koyeb pricing: https://www.koyeb.com/pricing
22. Koyeb terms: https://www.koyeb.com/docs/legal/terms
23. Cloud Run pricing: https://cloud.google.com/run/pricing
24. Cloud Run request timeout: https://cloud.google.com/run/docs/configuring/request-timeout
25. Google Cloud free features: https://cloud.google.com/free/docs/free-cloud-features
26. Cloud Run FastAPI quickstart: https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-fastapi-service
27. Vercel Python runtime: https://vercel.com/docs/functions/runtimes/python
28. Vercel Functions limits: https://vercel.com/docs/functions/limitations
29. Vercel function duration: https://vercel.com/docs/functions/configuring-functions/duration
30. Vercel Functions pricing: https://vercel.com/docs/functions/usage-and-pricing
31. Cloudflare Python Workers: https://developers.cloudflare.com/workers/languages/python/
32. Cloudflare Workers limits: https://developers.cloudflare.com/workers/platform/limits/
33. Cloudflare Workers pricing: https://developers.cloudflare.com/workers/platform/pricing/
34. Hugging Face Spaces overview: https://huggingface.co/docs/hub/spaces-overview
35. Hugging Face pricing: https://huggingface.co/pricing
36. Fly.io pricing: https://fly.io/docs/about/pricing/
37. Railway free trial: https://docs.railway.com/reference/pricing/free-trial
38. Railway plans: https://docs.railway.com/reference/pricing/plans
39. Supabase pricing: https://supabase.com/pricing
40. Supabase project pausing: https://supabase.com/docs/guides/platform/project-pausing
41. Supabase billing FAQ: https://supabase.com/docs/guides/platform/billing-faq
42. Supabase pgvector: https://supabase.com/docs/guides/database/extensions/pgvector
43. Supabase terms: https://supabase.com/terms
44. Neon pricing: https://neon.com/pricing
45. Neon plans: https://neon.com/docs/introduction/plans
46. Neon scale to zero: https://neon.com/docs/introduction/scale-to-zero
47. Neon pgvector: https://neon.com/docs/extensions/pgvector
48. Neon terms: https://neon.com/terms-of-service
49. Aiven free plan / service pricing: https://aiven.io/docs/platform/concepts/free-plan
50. Aiven free PostgreSQL: https://aiven.io/free-postgresql-database
51. Aiven pgvector: https://aiven.io/docs/products/postgresql/concepts/pgvector
52. Koyeb databases: https://www.koyeb.com/docs/databases
53. Koyeb general FAQ: https://www.koyeb.com/docs/faqs/general
54. Render Postgres extensions: https://render.com/docs/postgresql-extensions
55. Cloudflare R2 pricing: https://developers.cloudflare.com/r2/pricing/
56. Cloudflare R2 get started: https://developers.cloudflare.com/r2/get-started/
57. Cloudflare billing policy: https://developers.cloudflare.com/billing/understand/billing-policy/
58. Backblaze B2 pricing: https://www.backblaze.com/cloud-storage/pricing
59. Backblaze B2 transaction pricing: https://www.backblaze.com/cloud-storage/transaction-pricing
60. Tigris pricing: https://www.tigrisdata.com/pricing/
61. Supabase Storage file limits: https://supabase.com/docs/guides/storage/uploads/file-limits
62. Vercel Blob pricing: https://vercel.com/docs/vercel-blob/usage-and-pricing
63. Firebase Storage Sept 2024 changes FAQ: https://firebase.google.com/docs/storage/faqs-storage-changes-announced-sept-2024
64. Supabase custom SMTP: https://supabase.com/docs/guides/auth/auth-smtp
65. Supabase Auth rate limits: https://supabase.com/docs/guides/auth/rate-limits
66. Firebase Auth limits: https://firebase.google.com/docs/auth/limits
67. Identity Platform pricing: https://cloud.google.com/identity-platform/pricing
68. Clerk pricing: https://clerk.com/pricing
69. Clerk terms: https://clerk.com/legal/terms
70. Auth0 pricing: https://auth0.com/pricing
71. Kinde pricing: https://kinde.com/pricing/
72. Neon Auth overview: https://neon.com/docs/auth/overview
73. Resend pricing: https://resend.com/pricing
74. AWS Free Tier: https://aws.amazon.com/free/
75. Neon Auth, set up OAuth: https://neon.com/docs/auth/guides/setup-oauth
76. Neon Auth, about (availability): https://neon.com/docs/auth/about
77. Neon Auth, customize emails: https://neon.com/docs/auth/guides/customize-emails

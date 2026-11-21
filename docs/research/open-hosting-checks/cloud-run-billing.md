# Research: Cloud Run request-based billing in Singapore (#726)

Question: the prices, the free tier, and the billed-time rules for re-costing Crux's server time. Crux runs three Cloud Run services in `asia-southeast1` with request-based billing: the backend, the tasks service, and the Gotenberg converter (at most 1 instance, 1 to 2 GiB).

Every claim comes from a Google Cloud docs or pricing page, read on **2026-11-21**. Numbers in square brackets point to the source list at the end. Where a page is silent, this note says so. A sentence marked "Reading" is this note's interpretation, not the page's words.

## Short answer

| Question | Answer in one line |
|---|---|
| C1. Tier and prices | Singapore is Tier 2. Request-based: USD 0.0000336 per vCPU-second, USD 0.0000035 per GiB-second, USD 0.40 per million requests. |
| C2. Free tier | Not a stated dollar credit. 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests a month, valued at Tier 1 prices (USD 4.32 + 0.90 + 0.80). In Singapore that covers about 128,571 instance-seconds at 1 vCPU, at 512 MiB or 1 GiB (reading). |
| C3. Billed time | Startup, shutdown, and any time at least one request is open, from the first request's start to the last request's end. Rounded up to 100 ms. Overlapping requests on one instance bill once. |

---

## C1. Singapore's tier and prices

### What the page says

- "Cloud Run pricing depends on the selected region. Pricing for Cloud Run services also depends on the billing configuration" [1].
- The page lists `asia-southeast1 (Singapore)` under "Subject to Tier 2 pricing" [1].
- The static table on the page shows Iowa (`us-central1`) prices. The Singapore prices below come from the page's per-region table data for "Singapore (asia-southeast1)" [1].

### Request-based billing prices, default (no committed use discount)

| Resource | Singapore, Tier 2 | Iowa, Tier 1 | Ratio |
|---|---|---|---|
| CPU, active time (per vCPU-second) | USD 0.0000336 | USD 0.000024 | 1.4 |
| Memory, active time (per GiB-second) | USD 0.0000035 | USD 0.0000025 | 1.4 |
| CPU, idle time (minimum instances only) | USD 0.0000035 | USD 0.0000025 | 1.4 |
| Memory, idle time (minimum instances only) | USD 0.0000035 | USD 0.0000025 | 1.4 |
| Requests (per 1,000,000) | USD 0.40 | USD 0.40 | 1.0 |

- The idle rate applies to "idle billable time for instances kept warm using minimum instances. Idle instances that are not minimum instances are not charged" [1].
- "Requests are only billed when they reach the container after successfully being authenticated, requests denied by IAM policy are not billed" [1].
- A "GiB-second means for example running a 1 gibibyte instance for 1 second, or running a 256 mebibyte instance for 4 seconds" [1].

### Cost of one busy instance in Singapore

| Size | Per second | Per hour |
|---|---|---|
| 1 vCPU, 512 MiB | 0.0000336 + 0.5 x 0.0000035 = USD 0.00003535 | USD 0.1273 |
| 1 vCPU, 1 GiB | 0.0000336 + 0.0000035 = USD 0.0000371 | USD 0.1336 |
| 1 vCPU, 2 GiB | 0.0000336 + 2 x 0.0000035 = USD 0.0000406 | USD 0.1462 |

These are list prices before the free tier, plus USD 0.40 per million requests.

---

## C2. The free tier

### What the pages say

- For request-based billing: "Free tier (based on us-central1 active pricing): CPU - First 180,000 vCPU-seconds free per month" [1].
- The same list gives "RAM - First 360,000 GiB-seconds free per month" and "Requests - 2 million requests free per month" [1].
- "The free tier usage is aggregated across projects by billing account and resets every month; you are billed only for usage past the free tier" [1].
- "The free tier is applied as a spending based discount using Tier 1 pricing" [1].
- The Free Program page gives the same three limits for request-based billing. It adds "1 GB of outbound data transfer from North America per month" [2].
- The budgets page lists "Free tier credits" as a savings type: "credits are applied to implement the free tier usage" [3].
- Neither Cloud Run page states a fixed dollar amount for the free tier [1][2].

### How it is valued

The free tier is stated in resource units. Its value is those units at Tier 1 (Iowa) prices:

| Part | Units | Tier 1 price | Value |
|---|---|---|---|
| CPU | 180,000 vCPU-seconds | USD 0.000024 | USD 4.32 |
| Memory | 360,000 GiB-seconds | USD 0.0000025 | USD 0.90 |
| Requests | 2 million | USD 0.40 per million | USD 0.80 |
| Total | | | USD 6.02 |

Each free-tier line on the page comes to the same two dollar amounts at its own Tier 1 price [1]:

| Billing type | CPU allowance x price | Memory allowance x price |
|---|---|---|
| Request-based | 180,000 x 0.000024 = USD 4.32 | 360,000 x 0.0000025 = USD 0.90 |
| Instance-based | 240,000 x 0.000018 = USD 4.32 | 450,000 x 0.000002 = USD 0.90 |
| Delayed jobs | 342,857 x 0.0000126 = USD 4.32 | 642,857 x 0.0000014 = USD 0.90 |
| Worker pools | 384,204 x 0.000011244 = USD 4.32 | 728,744 x 0.000001235 = USD 0.90 |

- So the page's own numbers point to a fixed dollar value: USD 4.32 for CPU and USD 0.90 for memory.
- Reading: in a Tier 2 region the discount is that dollar value, not the units. So in Singapore it covers fewer than 180,000 vCPU-seconds.
- The page does not show a Tier 2 example. All six pricing examples are in `europe-west1`, a Tier 1 region [1].
- In four examples (1, 3, 4 and 6), the cost "Without the vCPU/Memory free tier" is USD 5.22 higher, which is 4.32 + 0.90 [1].
- Example 2 (1 vCPU, 512 MiB, 10 million requests of 400 ms) is only USD 4.77 higher [1]. It uses more than both allowances, so the page does not explain the gap.
- Example 5, a job, costs USD 0.45 without the free tier and USD 0 with it [1].

### What it covers at 1 vCPU in Singapore

The page does not say whether the CPU and memory parts are separate allowances or one pool. Both readings follow.

**Reading 1: separate CPU and memory allowances.** The CPU part covers 4.32 / 0.0000336 = 128,571 vCPU-seconds. The memory part covers 0.90 / 0.0000035 = 257,143 GiB-seconds.

| Size | CPU part lasts | Memory part lasts | Free instance time |
|---|---|---|---|
| 1 vCPU, 512 MiB | 128,571 s | 257,143 / 0.5 = 514,286 s | 128,571 s (about 35.7 hours) |
| 1 vCPU, 1 GiB | 128,571 s | 257,143 s | 128,571 s (about 35.7 hours) |
| 1 vCPU, 2 GiB | 128,571 s | 257,143 / 2 = 128,571 s | 128,571 s (about 35.7 hours) |

At 512 MiB and 1 GiB, the CPU part runs out first. Memory left over is not moved to CPU in this reading.

**Reading 2: one pool of USD 5.22.**

| Size | Arithmetic | Free instance time |
|---|---|---|
| 1 vCPU, 512 MiB | 5.22 / 0.00003535 | 147,666 s (about 41.0 hours) |
| 1 vCPU, 1 GiB | 5.22 / 0.0000371 | 140,701 s (about 39.1 hours) |
| 1 vCPU, 2 GiB | 5.22 / 0.0000406 | 128,571 s (about 35.7 hours) |

- Reading 1 is the closer fit to the page. It lists CPU and RAM as separate lines, each with its own fixed dollar value [1]. It is also the lower figure, so it is the safer one to cost with.
- The requests part covers 2 million requests in either reading, because the request price is the same in both tiers.
- The free tier is shared by every project on the billing account [1]. Live, staging, the tasks service and the converter all draw on it.
- The earlier note found that spend caps count gross use before credits. The free tier therefore lowers the bill but not the spend cap's count.

---

## C3. What is billed

### What the pages say

- "Cloud Run charges you only for the resources you use, rounded up to the nearest 100 millisecond" [1].
- With request-based billing, "Cloud Run only charges for the CPU and memory allocated to an instance when" [1]:
  - "The instance is starting."
  - "The instance is gracefully shutting down (handling the SIGTERM signal)."
  - "At least one request is being processed by the instance."
- "Billable instance time begins with the start of the first request and ends at the end of the last request" [1].
- "Billable instance time is rounded up to the nearest 100 milliseconds" [1].
- The billing settings page agrees: instances "are only charged when they process requests, when they start, and when they shut down" [4].
- "With request-based billing, CPU is only allocated during request processing" [4].
- The metric `run.googleapis.com/container/billable_instance_time` says: "billable time occurs when the container instance is starting or at least one request is being processed" [5].
- Its example: "If a single request lasting 30ms was received by a revision in the past minute, it is rounded up to 100ms" [5].

### Startup and shutdown

- "During this startup time, instances are allocated CPU" [6].
- Before shutdown, a SIGTERM marks "the start of a 10 second period before the actual shutdown occurs" [6].
- "During this period, the instance is allocated CPU and billed" [6].
- Reading: each instance shutdown can add up to 10 seconds of billed time. The page does not say whether the bill stops early when the container exits first.
- Conflict: the `billable_instance_time` description names startup and requests but not shutdown [5]. The pricing page and the runtime contract both bill shutdown [1][6].

### Concurrency

- "When setting concurrency higher than one request at a time, multiple requests can share the allocated CPU and memory of an instance" [1].
- The concurrency setting "specifies the maximum number of requests that can be processed simultaneously by a given instance" [7].
- The metric example: "If a revision with 2 container instances has been continuously serving traffic in the last minute, the value is 2s/s" [5].
- So instance time is billed per instance, not per request. Two overlapping requests on one instance bill the time at least one is open, once.
- Reading: this is the union of the instance's busy time. The pricing page's "first request ... last request" sentence says the same [1].
- The per-request charge (USD 0.40 per million) still counts every request [1].

### Long and streaming responses

- No page read names server-sent events or a streaming HTTP response.
- The closest text is about WebSockets: "A Cloud Run instance that has any open WebSocket connection is considered active, so CPU is allocated and the service is billed as instance-based billing" [8].
- The page does not say whether "billed as instance-based billing" means the instance-based rate or only that the instance bills while the connection is open.
- "WebSockets streams are HTTP requests, which are still subject to the request timeout" [8].
- The request timeout defaults to "5 minutes (300 seconds) and can be extended up to 60 minutes (3600 seconds)" [9].
- Reading: a streaming response is a request that is still being processed. The instance bills from its start to its last byte, under the "first request ... last request" rule.
- Reading: the 100 ms rounding applies to billable instance time, per the pricing page [1]. The page does not say whether each busy stretch rounds separately or the month's total rounds once. The metric's 30 ms example rounds one short request on its own [5].

## Sources (all read 2026-11-21)

1. Cloud Run pricing (tiers, request-based prices including per-region data, free tier, billable instance time, examples). "Last updated" not shown: https://cloud.google.com/run/pricing
2. Google Cloud Free Program, Free Google Cloud features and trial offer (Cloud Run row). "Last updated 2026-11-13 UTC": https://cloud.google.com/free/docs/free-cloud-features
3. Cloud Billing, Create, edit, or delete budgets and budget alerts (Free tier credits). "Last updated 2026-11-10 UTC": https://docs.cloud.google.com/billing/docs/how-to/budgets
4. Cloud Run, Billing settings for services. "Last updated 2026-11-18 UTC": https://docs.cloud.google.com/run/docs/configuring/billing-settings
5. Google Cloud metrics P to Z (`run` section, `container/billable_instance_time`). "Last updated 2026-11-20 UTC": https://docs.cloud.google.com/monitoring/api/metrics_gcp_p_z
6. Cloud Run, Container runtime contract (startup, shutdown). "Last updated 2026-11-18 UTC": https://docs.cloud.google.com/run/docs/container-contract
7. Cloud Run, Maximum concurrent requests for services. "Last updated 2026-11-18 UTC": https://docs.cloud.google.com/run/docs/about-concurrency
8. Cloud Run, Using WebSockets. "Last updated 2026-11-18 UTC": https://docs.cloud.google.com/run/docs/triggering/websockets
9. Cloud Run, Configure request timeout for services. "Last updated 2026-11-18 UTC": https://docs.cloud.google.com/run/docs/configuring/request-timeout

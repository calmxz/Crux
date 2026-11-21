# Item 2: does the Cloud Run spend cap count use before the free credit? (#726)

A recheck on 2026-11-21 is in [`alerting-and-uptime-history.md`](alerting-and-uptime-history.md), question D.

Every claim below comes from an official docs, pricing, terms or source-code page, all read on **2026-11-02**. Numbers in square brackets point to the source list at the end, numbered as in the first version of this note. Where a page was silent, this note says so.

### What the pages say

- The cap "is enforced when your gross, estimated usage costs exceed 100% of your budget amount" [12].
- Estimated costs use "the list price of services and don't include savings and credits" [12].
- "For spend cap budgets, you can't edit the Savings settings" [12]. No "include credits" choice exists.
- Google's API example of a Cloud Run spend cap shows `creditTypesTreatment: EXCLUDE_ALL_CREDITS` [13].
- The budgets page lists "Free tier credits" as a savings type [14].
- It says "credits are applied to implement the free tier usage" [14]. The billing export lists `FREE_TIER` as a credit type [15].
- Firebase's spend-cap page agrees: the cap "is based on gross costs and do not include savings and credits" [16].
- Each cap covers one project and one eligible service. Cloud Run is eligible [12].
- A triggered cap pauses every Cloud Run service in the project. Services return 5xx errors [17].
- Enforcement is not instant, and any overage is billed as normal [12].

### One ambiguity

- The setup steps say some services get fast gross estimates. The "remaining services" use actual costs "inclusive of all savings" [12].
- The page does not say which services are which.
- This note reads Cloud Run as gross, from the general limitation sentence and the Cloud Run API example [12][13].
- The first month's spend amount on the budget page settles it.

### The ticket's example

- A staging month of USD 4.80 gross trips the USD 2 staging cap, though the credit covers it and the bill is 0.
- Live pauses when live alone reaches USD 6 gross, whatever the shared credit has left.
- The credit is shared across the billing account [18]. Each cap counts only its own project's Cloud Run use.
- The converter and the tasks service share the live cap if they run as Cloud Run services in that project.

### Answer

- Yes, it counts use before the credit. This matches #716's "unconfirmed" reading, so the caps are gross amounts.
- #716's caps (USD 6 live, USD 2 staging) and fallback caps (about USD 8, about USD 16) need sizing on gross list-price use.
- #675's hosting costs and the map's constraints line should state the caps as gross.

## Sources (all read 2026-11-02)

12. Google Cloud Billing, Manage spend cap budgets ("Last updated 2026-10-26 UTC"): https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps
13. Google Cloud Billing, Using the Cloud Billing Budget API for spend cap budgets: https://docs.cloud.google.com/billing/docs/how-to/budget-api-spend-cap
14. Google Cloud Billing, Create, edit, or delete budgets and budget alerts (Savings types; "Last updated 2026-10-26 UTC"): https://docs.cloud.google.com/billing/docs/how-to/budgets
15. Google Cloud Billing, standard usage cost export (`credits.type`): https://docs.cloud.google.com/billing/docs/how-to/export-data-bigquery-tables/standard-usage
16. Firebase, spend caps ("Last updated 2026-10-20 UTC"): https://firebase.google.com/docs/projects/billing/spend-caps
17. Cloud Run, Best practices for cost-optimized Cloud Run services ("Last updated 2026-10-30 UTC"): https://docs.cloud.google.com/run/docs/tips/services-cost-optimization
18. Cloud Run pricing: https://cloud.google.com/run/pricing

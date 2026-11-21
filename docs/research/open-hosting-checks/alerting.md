# Item 3: alerting charges from 1 September 2027 (#726)

The four rules from #770, and the uptime-check history from #772, are in [`alerting-and-uptime-history.md`](alerting-and-uptime-history.md).

Every claim below comes from an official docs, pricing, terms or source-code page, all read on **2026-11-02**. Numbers in square brackets point to the source list at the end, numbered as in the first version of this note. Where a page was silent, this note says so.

### What the page says

- "Starting no sooner than September 1, 2027, Cloud Monitoring will begin charging for alerting" [19].
- USD 0.35 a month for each metric reference in an alerting policy [19].
- USD 0.50 per million points returned by a metric alerting policy's conditions [19].
- In filter-based policies, "each condition counts as 1 metric reference" [19].
- Log-match policies, used for log-based alerts, "can have only a single condition" [19].
- "Log-match conditions return no points," so log-based rules pay no points charge [19].
- Metric policies on Billing, Quota or Uptime metrics are not charged [19].
- Log-based policies for Personalized Service Health logs are not charged [19]. No other log-based exception is listed.
- To stop a charge, modify, delete or disable the policy [19].

### Caveat, settled on 2026-11-11

- The page defines a metric reference as "a single mention of a metric name" [19]. A log-match condition names no metric.
- The first version of this note read each log-based rule as 1 reference, and found no log-based example on the pages read [20][21].
- **Settled:** the snippet fact-check (#762) found the Observability pricing page's Example 7. It bills log-based alerting as metric references: "100 metric references * $0.35 per month = $3.50 per month".
- So each log-based rule is 1 metric reference, at USD 0.35 a month.

### The ticket's example

- About 8 log-based rules come to about USD 2.80 a month, or USD 33.60 a year.
- Uptime checks: the first 1 million executions a month are free [20]. #717's 52,000 a month stay free.
- #717 sends errors through Error Reporting, not an alert rule. The real rule count is #717's to settle.

### Answer

- Log-based rules do cost money from no sooner than 1 September 2027, at about USD 0.35 a month each.
- #675's hosting costs gain about USD 2.80 a month for 8 rules.
- #717 can merge rules, or move less urgent items to the daily email.
- **Later:** #770 set the rules at four, about USD 1.49 a month. See [`alerting-and-uptime-history.md`](alerting-and-uptime-history.md).

## Sources (all read 2026-11-02)

19. Google Cloud Observability pricing, Pricing for alerting: https://cloud.google.com/stackdriver/pricing
20. Google Cloud Observability pricing examples (alerting policies, uptime checks): https://cloud.google.com/stackdriver/observability-pricing-examples
21. Cloud Monitoring, Manage alerting costs ("Last updated 2026-10-26 UTC"): https://docs.cloud.google.com/monitoring/alerts/cost-control

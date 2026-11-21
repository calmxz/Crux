# Research: alerting charges and uptime-check history (#726)

Questions: what Crux's four alert rules cost from no sooner than 1 September 2027 (#770), and how a release script reads an uptime check's last pass after a restore (#772). A short note on the spend cap page (item 2 of the earlier note) closes this file.

Every claim comes from a Google Cloud docs or pricing page, read on **2026-11-21**. Numbers in square brackets point to the source list at the end. Where a page is silent, this note says so. A sentence marked "Reading" is this note's interpretation, not the page's words.

## Short answer

| Question | Answer in one line |
|---|---|
| A1. Points charge | USD 0.50 per million points. One time series at the fixed 30-second period gives 86,400 points in a 30-day month, or about USD 0.043 per condition. The four rules come to about USD 1.49 a month. The ticket's USD 1.50 holds. |
| A2. Metric allotment | Yes, a user-defined log-based counter counts toward the free 150 MiB. One point is 8 bytes. One series written every minute uses at most about 0.33 MiB a month. |
| B1. History API | `projects.timeSeries.list` on `monitoring.googleapis.com/uptime_check/check_passed`, filtered by `metric.labels.check_id`. |
| B2. Permission | `monitoring.timeSeries.list`, in the predefined role Monitoring Viewer (`roles/monitoring.viewer`). A custom role with that one permission is the least privilege (reading). |
| B3. Retention | 6 weeks. Resolution is the check period, 60 seconds by default (reading). The 10:00 am pass is about 4 hours old at the restore, so the script finds it. |
| D. Spend cap page | Updated 2026-11-10. It still does not name which services use gross estimates. Cloud Run appears only in the eligible list. |

---

## A1. The points charge for a metric condition

### What the pages say

- Alerting costs "$0.50 per 1,000,000 points returned by the query of a metric alerting policy condition" [1].
- The metric reference charge is "$0.35 per month for each metric reference in an alerting policy" [1].
- Filter-based policies "can combine up to six conditions. Each condition counts as 1 metric reference" [1].
- "Log-match conditions return no points" [1]. Example 7 bills 100 log-based policies as 100 metric references, with a points cost of USD 0 [2].
- In each execution period, "Each point in the response counts as one point returned" [1].
- The execution period: "For most condition types, this is 30 seconds and can't be changed" [1].
- "Other alerting policy conditions are fixed to a 30-second execution period" [3]. Only PromQL conditions can change it [3].
- "A point is returned for each time series that is monitored by an alerting policy" [3].
- The pricing examples "take place in a 30-day month, resulting in 86,400 30-second execution periods per month" [2].
- The examples count one point per output time series per period [2]. Each example query uses a 1-minute window (`[1m]`) [2].

### How points are counted

Points per month = output time series x execution periods per month.

- The 30-second period is fixed for filter-based conditions [1][3].
- Reading: the window length (10 minutes or 24 hours) does not change the count. It sets how each point is computed, not how many points the query returns. No page shows a longer window.
- A 24-hour window is allowed. The maximum `alignmentPeriod` is "90,000 seconds (25 hours) for alerting policies" [4].

### The arithmetic, one time series each

| Condition | Time series | Periods in a 30-day month | Points | Points charge |
|---|---|---|---|---|
| More than 3,000 `/api` calls in 10 minutes | 1 | 86,400 | 86,400 | 0.0864 million x USD 0.50 = USD 0.0432 |
| More than 30,000 `/api` calls in 24 hours | 1 | 86,400 | 86,400 | USD 0.0432 |

- 86,400 periods = 30 days x 24 hours x 60 minutes x 2 periods a minute.
- In a 31-day month, each condition returns 89,280 points, or USD 0.0446.
- Monthly total: 4 metric references x USD 0.35 = USD 1.40. Points: 2 x USD 0.0432 = USD 0.0864. Total: about USD 1.49.
- So the ticket's "about USD 0.05 for each new metric condition" is about right. The exact figure is about USD 0.04.

### What the one-series assumption needs

- A log-based metric has "one stream for each combination of unique values for the set of metric and resource labels" [5].
- "Logging records separate time series for each combination of label values" [5]. Most log-based metrics also carry a default `log` label [5].
- Reading: each Cloud Run revision (or each service, if the metric matches more than one) is its own series.
- So each condition must sum across series to one output series. Per the page, "aggregating to the Google Cloud project level is cheaper" than finer levels [3].
- Each condition must also name a resource type. With "Unspecified Resource", the condition "launches a separate query for every monitored resource type" [3].
- "As each query bills a minimum of one point returned, not specifying the resource type causes a high points returned bill" [3].
- Reading: that minimum also means a quiet period with no data still bills about one point per period. Gaps do not lower the count.

---

## A2. The log-based counter and the free metric allotment

### What the pages say

- "User-defined logs-based metrics are a class of Cloud Monitoring custom metrics and are chargeable" [1].
- The free allotment is the "First 150 MiB per billing account for metrics charged by bytes ingested" [1].
- Bytes are counted as follows: "For a scalar data type: 8 bytes for each data point written to a time series. User-defined logs-based counter metrics fall into this category" [1].
- "Non-chargeable metrics don't count towards the allotment limit" [1]. A user-defined counter is chargeable, so it does count.
- Above the allotment, the price is "$0.2580/MiB" for the first 150 to 100,000 MiB [1].

### How often the counter writes

- "Every minute, for each stream, the Logging backend uses the values of the in-memory counters to determine how to update a time series" [5].
- "When the aggregated count for an interval is non-zero, that value is written to the time series" [5].
- A zero is written only "when an adjacent interval has a non-zero value" [5]. Otherwise there is a gap [5].
- So a stream writes at most one point a minute. Quiet minutes write nothing.

### The arithmetic, one series, every minute

The examples page uses "roughly 730 hours" in a month, or 43,800 minutes [2]. It gives this same case:

- 43,800 points x 8 bytes = 350,400 bytes [2].
- 350,400 / 1,048,576 = about 0.334 MiB a month [2].
- That is about 0.22% of the 150 MiB allotment. The allotment holds about 449 such series.
- On a 30-day month: 43,200 points x 8 = 345,600 bytes, or about 0.330 MiB.
- This is the upper limit. Real use is lower, because minutes with no `/api` calls write no point [5].
- Reading: a deploy starts a new revision series, but the old one stops writing. The total stays near one series' worth.

---

## B1. The API for uptime-check history

### What the pages say

- The metric is `monitoring.googleapis.com/uptime_check/check_passed`, a `GAUGE`, `BOOL` metric [6].
- Its description: "True if the resource passed the check. After sampling, data is not visible for up to 35 seconds" [6].
- Its labels include `check_id`, "The Uptime check for which the request was made", and `checker_location` [6].
- The method is `GET https://monitoring.googleapis.com/v3/{name}/timeSeries`, with `name` in the form `projects/[PROJECT_ID_OR_NUMBER]` [7].
- `filter` is required: "The filter must specify a single metric type, and can additionally specify metric labels" [7].
- `interval` is required: "Only time series that contain data points in the specified interval are included in the response" [7].
- `view` is required. With no `aggregation`, "the raw time series data is returned" [7].
- `orderBy` is unsupported. Points "are currently returned in reverse time order (most recent to oldest)" [7].
- The filter syntax uses `metric.type` and `metric.labels.[KEY]` [8].

### The filter shape

This query is assembled from the parts above. No page gives this exact uptime example.

```
GET https://monitoring.googleapis.com/v3/projects/PROJECT_ID/timeSeries
  ?filter=metric.type = "monitoring.googleapis.com/uptime_check/check_passed"
          AND metric.labels.check_id = "CHECK_ID"
  &interval.startTime=2026-11-06T00:00:00Z
  &interval.endTime=2026-11-06T06:00:00Z
  &view=FULL
```

- An uptime check "must have at least three checkers" [9].
- Reading: the response has one time series for each `checker_location`, because that is a metric label [6]. Expect three or more series.
- To find the last pass, read each series from the newest point. Take the newest point with `boolValue` true before the outage.
- Reading: whether "last pass" means any checker or every checker is the script's choice. The pages do not define it.
- Read calls are billed per time series returned, with the "First 1 million time series returned per billing account" free [1].

## B2. The permission the script needs

- The method page lists only OAuth scopes, for example `https://www.googleapis.com/auth/monitoring.read` [7]. It does not name an IAM permission.
- The IAM page lists `monitoring.timeSeries.list` inside Monitoring Viewer (`roles/monitoring.viewer`) [10].
- Monitoring Viewer "Provides read-only access to get and list information about all monitoring data and configurations" [10]. You can grant it at the project level [10].
- Reading: `projects.timeSeries.list` checks `monitoring.timeSeries.list`. No page read maps the method to the permission in words.
- Least privilege: a custom role with only `monitoring.timeSeries.list`. Add `monitoring.uptimeCheckConfigs.list` only if the script looks up the check ID by name [10].
- The IAM page supports custom roles "when you want to grant a principal a more limited set of permissions than those granted with predefined roles" [10].

## B3. How long the history stays, and the example

### What the pages say

- "Metric data points older than the retention period are deleted from time series" [11].
- Metrics with a 24-month retention are custom, agent, and external metrics, plus a named list of Google Cloud services [11]. Monitoring's own metrics are not in that list.
- "All other Google Cloud metrics" are kept for **6 weeks** [11].
- The down-sampling footnote ("6 weeks at its original sampling frequency, then it is down-sampled to 10-minute intervals") attaches to the 24-month rows [11].
- The metric entry gives no "Sampled every" value for `check_passed` [6].
- The check runs at its configured `period`: "the only supported values are 60s (1 minute), 300s (5 minutes), 600s (10 minutes), and 900s (15 minutes). Optional, defaults to 60s" [12].

Reading: `uptime_check/check_passed` falls under "All other Google Cloud metrics", so it keeps 6 weeks. Its resolution is one point per checker per check period, 60 seconds by default, for the whole 6 weeks.

The example's answer does not depend on this reading. Both retention rows keep at least 6 weeks at the original sampling frequency [11].

### The example

- The outage began at 10:00 am on 6 Nov. The restore runs at 2:00 pm on 6 Nov.
- At the restore, the last pass is about 4 hours old. The 8:00 pm 4 Nov dump is about 42 hours old.
- Both fall well inside 6 weeks.
- With a 60-second period, each checker has a pass within about 1 minute before 10:00 am.
- So yes, the script finds the last pass at about 10:00 am. The 35-second visibility delay does not matter 4 hours later [6].
- With a 15-minute period, the last pass could be up to 15 minutes before the outage began.

---

## D. The spend cap page, rechecked

- The page now shows "Last updated 2026-11-10 UTC" [13]. The earlier note read it at "Last updated 2026-10-26 UTC".
- No saved copy from 2026-11-02 exists, so this note cannot diff the wording.
- The earlier note paraphrased this passage. Its full text is still on the page:
  - "For certain services, we can estimate directional costs faster than we can calculate the actual costs" [13].
  - "For those services, the spend amount we use to enforce a spend cap budget is based on gross, estimated costs, excluding savings" [13].
  - "For the remaining services, we calculate the spend amount using actual costs, inclusive of all savings" [13].
- The page still does not say which services are which.
- Cloud Run appears only in the eligible-services table (`run.googleapis.com`) and the FAQ's eligible list [13].
- The general limitation sentence still stands: "The cost calculations for spend caps are based on gross, estimated costs and don't include savings and credits" [13].
- Cloud Run's billing page adds that spend caps "automatically apply to all Cloud Run resource types in your project" [14]. It does not say gross or actual either.
- So the earlier ambiguity stands unchanged. The first month's spend amount on the budget page still settles it.

## Sources (all read 2026-11-21)

1. Google Cloud Observability pricing (alerting, chargeable metrics, Monitoring API). "Last updated" not shown: https://cloud.google.com/stackdriver/pricing
2. Google Cloud Observability pricing examples (alerting Examples 1 and 7, bytes ingested). "Last updated" not shown: https://cloud.google.com/stackdriver/observability-pricing-examples
3. Cloud Monitoring, Manage alerting costs. "Last updated 2026-11-20 UTC": https://docs.cloud.google.com/monitoring/alerts/cost-control
4. Cloud Monitoring API, REST resource `projects.alertPolicies` (`alignmentPeriod`). "Last updated 2026-09-04 UTC": https://docs.cloud.google.com/monitoring/api/ref_v3/rest/v3/projects.alertPolicies
5. Cloud Logging, Log-based metrics overview. "Last updated 2026-11-20 UTC": https://docs.cloud.google.com/logging/docs/logs-based-metrics
6. Google Cloud metrics I to O (`monitoring` section; list generated 2026-11-19). "Last updated 2026-11-20 UTC": https://docs.cloud.google.com/monitoring/api/metrics_gcp_i_o
7. Cloud Monitoring API, Method `projects.timeSeries.list`. "Last updated 2025-07-23 UTC": https://docs.cloud.google.com/monitoring/api/ref_v3/rest/v3/projects.timeSeries/list
8. Cloud Monitoring, Monitoring filters. "Last updated 2026-11-20 UTC": https://docs.cloud.google.com/monitoring/api/v3/filters
9. Cloud Monitoring, Create public uptime checks. "Last updated 2026-11-20 UTC": https://docs.cloud.google.com/monitoring/uptime-checks
10. Cloud Monitoring, Control access with IAM. "Last updated 2026-11-20 UTC": https://docs.cloud.google.com/monitoring/access-control
11. Cloud Monitoring quotas and limits (Data retention). "Last updated 2026-11-20 UTC": https://docs.cloud.google.com/monitoring/quotas
12. Cloud Monitoring API, REST resource `projects.uptimeCheckConfigs` (`period`). "Last updated 2026-09-04 UTC": https://docs.cloud.google.com/monitoring/api/ref_v3/rest/v3/projects.uptimeCheckConfigs
13. Cloud Billing, Manage spend cap budgets. "Last updated 2026-11-10 UTC": https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps
14. Cloud Run, Billing settings for services (Budget spend caps). "Last updated 2026-11-18 UTC": https://docs.cloud.google.com/run/docs/configuring/billing-settings

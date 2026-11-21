# Keepwell Looker Studio Report & Portal Wiring

All reports connect to BigQuery dataset `keepwell_analytics` in region `asia-south1` (Mumbai). BigQuery holds pseudonymous IDs only (no raw phones, addresses, or household PII).

## 1. Data Sources (BigQuery Views)

| View | Granularity | Primary Consumer |
|---|---|---|
| `keepwell_analytics.v_first_time_fix` | centre, brand, category, technician, month, date | Centre Overview, Brand Portal |
| `keepwell_analytics.v_fvr_14d` | centre, brand, category, closure_month | Centre Overview (FVR-14 gauge), Brand Portal |
| `keepwell_analytics.v_self_fix_resolution` | centre, brand, category, month | Centre Overview, Brand Portal |
| `keepwell_analytics.v_gate_funnel` | centre, gate_month | Centre Overview |
| `keepwell_analytics.v_urgency_agreement` | centre, assessment_month, agent_class | Centre Overview |
| `keepwell_analytics.v_override_rate` | centre, activity_month | Centre Overview |
| `keepwell_analytics.v_technician_utilisation` | centre, technician, work_date, work_month | Centre Overview |
| `keepwell_analytics.v_parts_ready_at_visit` | centre, visit_month | Centre Overview |
| `keepwell_analytics.v_repeat_failures_by_model` | brand, category, model_code, series, fault_family | Brand Portal |
| `keepwell_analytics.v_response_time_first_reply` | centre, trigger, channel, ticket_month | Centre Overview, Brand Portal |
| `keepwell_analytics.v_repeat_failure_risk_scores` (P2) | ticket, centre, brand, model_code | Brand Portal |
| `keepwell_analytics.v_parts_demand_forecast_4w` (P2) | centre, part_id, forecast_week | Centre Overview |

## 2. Report 1: Centre Overview (`kw-centre-overview`)

Scoped by Looker Studio URL parameter `centre_id` (matching the authenticated user's `centre_id` claim).

| Visual | Data Source | Dimensions | Metrics / Calculated Fields |
|---|---|---|---|
| **FVR-14 Gauge** | `v_fvr_14d` | — | `SUM(fvr_14d_passed_count) / SUM(evaluated_repair_tickets)` (Target >= 0.85, Green >= 0.85, Amber 0.70–0.84, Red < 0.70) |
| **First-Time Fix Scorecard** | `v_first_time_fix` | `visit_month` | `SUM(fixed_first_time_count) / SUM(repair_first_visits)` |
| **Self-Fix Resolution & Time Saved** | `v_self_fix_resolution` | `ticket_month`, `category_code` | `SUM(self_fix_resolved_count) / SUM(total_repair_tickets)`, `SUM(est_minutes_saved)` |
| **Consent Gate Funnel** | `v_gate_funnel` | `gate_month` | `SUM(gate1_asked)`, `SUM(gate1_yes)`, `SUM(gate2_asked)`, `SUM(gate2_switch_to_video)`, `SUM(skipped_for_safety)` |
| **Urgency Agreement Bar** | `v_urgency_agreement` | `agent_class` | `SUM(agreed_count) / SUM(agent_assessed_tickets)` |
| **Override Rate Trend** | `v_override_rate` | `activity_month` | `100 * SUM(total_overrides) / SUM(assigned_ticket_count)` |
| **Technician Utilisation Table** | `v_technician_utilisation` | `technician_id`, `work_month` | `AVG(jobs_completed)` (jobs/technician-day), `SUM(jobs_fixed)`, `AVG(onsite_minutes)` |
| **Parts Ready at Visit** | `v_parts_ready_at_visit` | `visit_month` | `SUM(visits_all_parts_ready) / SUM(visits_requiring_parts)` |
| **First Reply Latency** | `v_response_time_first_reply` | `channel`, `trigger` | `AVG(p50_first_reply_seconds)`, `AVG(p90_first_reply_seconds)` |

## 3. Report 2: Brand & Retailer Portal (`kw-brand-portal`)

Scoped by Looker Studio URL parameter `brand_id` (matching the authenticated brand user's `brand_id` claim). Never exposes another centre's private pricing or stock.

| Visual | Data Source | Dimensions | Metrics / Calculated Fields |
|---|---|---|---|
| **Brand FVR-14 Gauge** | `v_fvr_14d` | `category_code` | `SUM(fvr_14d_passed_count) / SUM(evaluated_repair_tickets)` |
| **FTF by Category** | `v_first_time_fix` | `category_code`, `visit_month` | `SUM(fixed_first_time_count) / SUM(repair_first_visits)` |
| **Repeat Failures by Model Table** | `v_repeat_failures_by_model` | `model_code`, `model_series`, `fault_family` | `SUM(total_repair_tickets)`, `SUM(repeat_14d_tickets)`, `SUM(repeat_30d_tickets)`, `repeat_14d_rate` |
| **Self-Fix Deflection** | `v_self_fix_resolution` | `category_code`, `ticket_month` | `SUM(self_fix_resolved_count)`, `SUM(self_fix_resolved_count) / SUM(total_repair_tickets)` |
| **Response Time by Trigger** | `v_response_time_first_reply` | `trigger`, `channel` | `AVG(p50_first_reply_seconds)`, `AVG(p90_first_reply_seconds)` |
| **High Repeat-Risk Watchlist (P2)** | `v_repeat_failure_risk_scores` | `model_code`, `category_code` | `AVG(repeat_14d_probability)`, `COUNTIF(predicted_is_repeat_14d = 1)` |

## 4. Embedded Looker Studio Wiring

1. Enable **Embedding** in Looker Studio (`File -> Embed report -> Enable embedding`).
2. Add a Looker Studio **Parameter** (`p_centre_id` on Centre Overview; `p_brand_id` on Brand Portal) and bind it in each BigQuery Custom Query or data-source filter.
3. Pass the parameter via the Looker Studio `params` JSON query string from Part B's Flutter web iframe (`apps/console` and `apps/brand`):
   ```text
   https://lookerstudio.google.com/embed/reporting/<REPORT_ID>/page/<PAGE_ID>?params=%7B%22p_brand_id%22%3A%22<BRAND_UUID>%22%7D
   ```
4. Live operational KPIs for `GET /v1/centre/overview` and `GET /v1/brand/analytics` are computed directly in Postgres using the identical SQL definitions so the app works immediately without waiting for the scheduled BigQuery export.

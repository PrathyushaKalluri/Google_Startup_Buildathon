-- ============================================================================
-- Keepwell Analytics (P2): BigQuery ML Models
-- Dataset: keepwell_analytics (Region: asia-south1 / Mumbai)
-- Models:
--   1. repeat_failure_risk   (LOGISTIC_REG) — predicts 14-day repeat failure
--   2. parts_demand_forecast (ARIMA_PLUS)   — 4-week part demand per centre
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Repeat Failure Risk (Logistic Regression)
--    Predicts whether a closed repair ticket will see a repeat repair on the
--    same appliance within 14 days of OTP closure.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE MODEL `keepwell_analytics.repeat_failure_risk`
OPTIONS (
  model_type = 'LOGISTIC_REG',
  input_label_cols = ['is_repeat_14d'],
  auto_class_weights = TRUE,
  l2_reg = 0.1,
  max_iterations = 25,
  data_split_method = 'AUTO_SPLIT'
) AS
WITH repair_history AS (
  SELECT
    t.id AS ticket_id,
    t.appliance_id,
    a.brand_id,
    a.category_code,
    COALESCE(am.model_code, 'unknown') AS model_code,
    t.urgency_class,
    t.entitlement,
    DATE_DIFF(DATE(t.created_at), COALESCE(a.purchase_date, DATE(t.created_at)), MONTH) AS appliance_age_months,
    COUNT(*) OVER (
      PARTITION BY t.appliance_id
      ORDER BY UNIX_SECONDS(t.created_at)
      RANGE BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    ) AS prior_repair_count,
    (
      SELECT COUNT(*)
      FROM `keepwell_analytics.fix_attempt` fa
      WHERE fa.ticket_id = t.id
    ) AS self_fix_attempts,
    (
      SELECT COUNT(*)
      FROM `keepwell_analytics.visit` v
      JOIN `keepwell_analytics.visit_part_used` vpu ON vpu.visit_id = v.id
      WHERE v.ticket_id = t.id
    ) AS parts_replaced_count,
    (
      SELECT v.outcome
      FROM `keepwell_analytics.visit` v
      WHERE v.ticket_id = t.id
      ORDER BY v.planned_start ASC
      LIMIT 1
    ) AS first_visit_outcome,
    COALESCE(t.closure_confirmed_at, t.closed_at) AS closed_ts,
    LEAD(t.created_at) OVER (
      PARTITION BY t.appliance_id
      ORDER BY t.created_at
    ) AS next_repair_ts
  FROM `keepwell_analytics.ticket` t
  JOIN `keepwell_analytics.appliance` a ON a.id = t.appliance_id
  LEFT JOIN `keepwell_analytics.appliance_model` am ON am.id = a.model_id
  WHERE t.job_type = 'repair'
    AND t.status IN ('closed', 'completed')
)
SELECT
  brand_id,
  category_code,
  model_code,
  urgency_class,
  COALESCE(entitlement, 'paid') AS entitlement,
  COALESCE(appliance_age_months, 0) AS appliance_age_months,
  prior_repair_count,
  self_fix_attempts,
  parts_replaced_count,
  COALESCE(first_visit_outcome, 'none') AS first_visit_outcome,
  IF(
    next_repair_ts IS NOT NULL
    AND closed_ts IS NOT NULL
    AND TIMESTAMP_DIFF(next_repair_ts, closed_ts, DAY) <= 14,
    1,
    0
  ) AS is_repeat_14d
FROM repair_history
WHERE closed_ts IS NOT NULL;

-- Scoring view for recently closed tickets (consumed by Brand Portal & Console)
CREATE OR REPLACE VIEW `keepwell_analytics.v_repeat_failure_risk_scores` AS
WITH recent_closed AS (
  SELECT
    t.id AS ticket_id,
    t.centre_id,
    a.brand_id,
    a.category_code,
    COALESCE(am.model_code, 'unknown') AS model_code,
    t.urgency_class,
    COALESCE(t.entitlement, 'paid') AS entitlement,
    DATE_DIFF(DATE(t.created_at), COALESCE(a.purchase_date, DATE(t.created_at)), MONTH) AS appliance_age_months,
    (
      SELECT COUNT(*)
      FROM `keepwell_analytics.ticket` t_prev
      WHERE t_prev.appliance_id = t.appliance_id
        AND t_prev.job_type = 'repair'
        AND t_prev.created_at < t.created_at
    ) AS prior_repair_count,
    (
      SELECT COUNT(*) FROM `keepwell_analytics.fix_attempt` fa WHERE fa.ticket_id = t.id
    ) AS self_fix_attempts,
    (
      SELECT COUNT(*)
      FROM `keepwell_analytics.visit` v
      JOIN `keepwell_analytics.visit_part_used` vpu ON vpu.visit_id = v.id
      WHERE v.ticket_id = t.id
    ) AS parts_replaced_count,
    COALESCE(
      (SELECT v.outcome FROM `keepwell_analytics.visit` v WHERE v.ticket_id = t.id ORDER BY v.planned_start ASC LIMIT 1),
      'none'
    ) AS first_visit_outcome
  FROM `keepwell_analytics.ticket` t
  JOIN `keepwell_analytics.appliance` a ON a.id = t.appliance_id
  LEFT JOIN `keepwell_analytics.appliance_model` am ON am.id = a.model_id
  WHERE t.job_type = 'repair'
    AND t.status = 'closed'
    AND t.closed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
)
SELECT
  ticket_id,
  centre_id,
  brand_id,
  category_code,
  model_code,
  predicted_is_repeat_14d,
  (SELECT prob FROM UNNEST(predicted_is_repeat_14d_probs) WHERE label = 1) AS repeat_14d_probability
FROM ML.PREDICT(
  MODEL `keepwell_analytics.repeat_failure_risk`,
  (SELECT * FROM recent_closed)
);

-- ----------------------------------------------------------------------------
-- 2. Parts Demand Forecast (ARIMA_PLUS)
--    Forecasts weekly part consumption per (centre_id, part_id) for van/centre
--    replenishment planning.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE MODEL `keepwell_analytics.parts_demand_forecast`
OPTIONS (
  model_type = 'ARIMA_PLUS',
  time_series_timestamp_col = 'week_start',
  time_series_data_col = 'units_used',
  time_series_id_col = ['centre_id', 'part_id'],
  horizon = 4,
  holiday_region = 'IN',
  auto_arima = TRUE
) AS
SELECT
  v.centre_id,
  vpu.part_id,
  TIMESTAMP(DATE_TRUNC(DATE(v.planned_start, 'Asia/Kolkata'), WEEK(MONDAY))) AS week_start,
  SUM(vpu.quantity) AS units_used
FROM `keepwell_analytics.visit_part_used` vpu
JOIN `keepwell_analytics.visit` v ON v.id = vpu.visit_id
GROUP BY v.centre_id, vpu.part_id, week_start;

-- 4-week forecast view joined with part_catalogue metadata
CREATE OR REPLACE VIEW `keepwell_analytics.v_parts_demand_forecast_4w` AS
SELECT
  f.centre_id,
  f.part_id,
  pc.part_no,
  pc.name AS part_name,
  DATE(f.forecast_timestamp, 'Asia/Kolkata') AS forecast_week,
  GREATEST(ROUND(f.forecast_value, 1), 0) AS forecast_units,
  GREATEST(ROUND(f.prediction_interval_lower_bound, 1), 0) AS lower_bound_units,
  GREATEST(ROUND(f.prediction_interval_upper_bound, 1), 0) AS upper_bound_units
FROM ML.FORECAST(
  MODEL `keepwell_analytics.parts_demand_forecast`,
  STRUCT(4 AS horizon, 0.8 AS confidence_level)
) f
JOIN `keepwell_analytics.part_catalogue` pc ON pc.id = f.part_id;

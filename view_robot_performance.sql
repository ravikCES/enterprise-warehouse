-- view_robot_performance
-- Author: Ravi Karra
-- Date: 2026-02-19
-- Subject: Warehouse Robotics Performance Schema
CREATE OR REPLACE VIEW `your_project.wms_analytics.v_robot_efficiency_kpis` AS
SELECT
  r.robot_id,
  r.robot_type,
  COUNT(m.mission_id) AS total_missions,
  -- Calculate Success Rate
  SAFE_DIVIDE(
    COUNTIF(m.status = 'COMPLETED'), 
    COUNT(m.mission_id)
  ) * 100 AS success_rate_pct,
  -- Calculate Mean Time to Resolve (MTTR) in minutes
  AVG(DATETIME_DIFF(i.resolution_ts, i.issue_detected_ts, MINUTE)) AS avg_resolution_time_mins,
  -- Units Per Hour (UPH)
  SAFE_DIVIDE(
    COUNTIF(m.status = 'COMPLETED'),
    SUM(TIMESTAMP_DIFF(m.end_ts, m.start_ts, SECOND)) / 3600
  ) AS units_per_hour
FROM
  `your_project.wms_analytics.dim_robots` r
LEFT JOIN
  `your_project.wms_analytics.fact_robot_missions` m ON r.robot_id = m.robot_id
LEFT JOIN
  `your_project.wms_analytics.fact_interventions` i ON r.robot_id = i.robot_id
GROUP BY 1, 2;
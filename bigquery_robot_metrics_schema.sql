-- bigquery_robot_metrics_schema.sql
-- Author: Ravi Karra
-- Date: 2026-02-19
-- Subject: Warehouse Robotics Efficiency Schema

-- Table 1: Robot Master (Dimension Table)
CREATE OR REPLACE TABLE `your_project.wms_analytics.dim_robots` (
  robot_id STRING NOT NULL,
  robot_type STRING, -- Sequoia, Hercules, Sparrow, Proteus
  firmware_version STRING,
  deployment_date DATE,
  last_maintenance_ts TIMESTAMP
);

-- Table 2: Robotic Telemetry (Fact Table)
-- Partitioned by day for cost-efficiency
CREATE OR REPLACE TABLE `your_project.wms_analytics.fact_robot_missions` (
  mission_id STRING NOT NULL,
  robot_id STRING NOT NULL,
  item_id STRING,
  start_ts TIMESTAMP,
  end_ts TIMESTAMP,
  status STRING, -- COMPLETED, FAILED, INTERRUPTED
  error_code STRING, -- NULL if success
  distance_meters FLOAT64,
  battery_level_start INT64,
  battery_level_end INT64
)
PARTITION BY DATE(start_ts)
CLUSTER BY robot_id, status;

-- Table 3: Manager Interventions (Exception Fact Table)
CREATE OR REPLACE TABLE `your_project.wms_analytics.fact_interventions` (
  intervention_id STRING NOT NULL,
  robot_id STRING,
  manager_id STRING,
  issue_detected_ts TIMESTAMP,
  resolution_ts TIMESTAMP,
  resolution_type STRING -- RESET, CLEAR_JAM, MANUAL_PICK, DISCARD
)
PARTITION BY DATE(issue_detected_ts);
#!/bin/bash
# deploy_gcp.sh
# Author: Ravi Karra
# Deploy the Manager Alert Service to Google Cloud Platform

echo "🚀 Deploying Warehouse Manager Alert Service..."

gcloud functions deploy alert_manager_on_rework \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --trigger-event-filters="type=google.cloud.firestore.document.v1.created" \
  --trigger-event-filters="database=(default)" \
  --trigger-event-filters="document=rework_lane/{docId}"

echo "✅ Deployment Complete."
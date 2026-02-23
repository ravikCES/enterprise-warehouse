#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py
Author      : Ravi Karra
Date        : 2026-02-19
Subject     : GCP Cloud Function - Manager Mobile Alert
Project Type: pilot
"""

import functions_framework
from firebase_admin import messaging, initialize_app

# Initialize once globally
initialize_app()

@functions_framework.cloud_event
def alert_manager_on_rework(cloud_event):
    """
    OBJECTIVE: Trigger a mobile push notification when a robot hits an error.
    WHAT HAPPENS: Reads Firestore event and sends an FCM 'High Priority' alert.
    """
    data = cloud_event.data
    fields = data["value"]["fields"]
    
    item_id = fields.get("item_id", {}).get("stringValue", "UNKNOWN")
    error = fields.get("error_msg", {}).get("stringValue", "Mechanical Jam")

    message = messaging.Message(
        notification=messaging.Notification(
            title="🛑 WAREHOUSE EMERGENCY",
            body=f"Manager intervention needed at Station 4. Item {item_id} - {error}"
        ),
        topic="warehouse_managers"
    )
    
    messaging.send(message)
    print(f"✅ Mobile Alert Sent for Item {item_id}")
from datetime import datetime, timezone, timedelta
from models.parcel_model import ParcelModel
from models.audit_model import AuditModel

class AlertService:
    @classmethod
    def get_operator_alerts(cls, operator_id):
        operator_id = str(operator_id)

        # 1. Failed parcels submitted by this operator
        all_operator_parcels = ParcelModel.get_parcels({"submittedBy": operator_id})
        failed_parcels = [p for p in all_operator_parcels if p.get("status") == "FAILED"]
        insurance_rejections = [p for p in all_operator_parcels if p.get("insuranceStatus") == "REJECTED"]

        # 2. Batch upload events for this operator from audit_logs
        collection = AuditModel.get_collection()
        batch_events = []
        partial_failures = 0
        complete_failures = 0
        format_errors = 0

        if collection is not None:
            raw_events = list(collection.find({
                "action": "BATCH_UPLOAD",
                "actorId": operator_id,
                "details.outcome": {"$in": ["PARTIAL_FAILURE", "FAILURE", "FORMAT_ERROR"]}
            }).sort([("timestamp", -1)]))

            for e in raw_events:
                e["_id"] = str(e["_id"])
                outcome = e.get("details", {}).get("outcome")
                if outcome == "PARTIAL_FAILURE":
                    partial_failures += 1
                elif outcome == "FAILURE":
                    complete_failures += 1
                elif outcome == "FORMAT_ERROR":
                    format_errors += 1
                batch_events.append(e)

        return {
            "success": True,
            "operatorId": operator_id,
            "failedParcelsCount": len(failed_parcels),
            "failedParcels": [
                {
                    "parcelId": p.get("parcelId"),
                    "submittedAt": p.get("submittedAt"),
                    "failureReason": p.get("failureReason")
                } for p in failed_parcels
            ],
            "insuranceRejectionsCount": len(insurance_rejections),
            "batchAlertsCount": len(batch_events),
            "batchAlertsSummary": {
                "partialFailures": partial_failures,
                "completeFailures": complete_failures,
                "formatErrors": format_errors
            },
            "recentBatchFailures": [
                {
                    "timestamp": e.get("timestamp"),
                    "fileType": e.get("details", {}).get("fileType"),
                    "outcome": e.get("details", {}).get("outcome"),
                    "total": e.get("details", {}).get("total"),
                    "successful": e.get("details", {}).get("successful"),
                    "failed": e.get("details", {}).get("failed")
                } for e in batch_events[:10]
            ]
        }

    @classmethod
    def get_admin_system_alerts(cls):
        now = datetime.now(timezone.utc)
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        twenty_five_hours_ago = (now - timedelta(hours=25)).isoformat()

        parcels_coll = ParcelModel.get_collection()
        alerts = []

        if parcels_coll is None:
            return {"success": True, "alerts": []}

        # Query all parcels in the last 25 hours
        all_recent = list(parcels_coll.find({
            "submittedAt": {"$gte": twenty_five_hours_ago}
        }))

        # Separate last hour vs baseline (previous 24 hours excluding last hour)
        last_hour_parcels = [p for p in all_recent if p.get("submittedAt") >= one_hour_ago]
        baseline_parcels = [p for p in all_recent if p.get("submittedAt") < one_hour_ago]

        # --------------------------------------------------
        # A. FAILURE RATE SPIKE
        # --------------------------------------------------
        total_last_hour = len(last_hour_parcels)
        if total_last_hour > 0:
            failed_last_hour = sum(1 for p in last_hour_parcels if p.get("status") == "FAILED")
            tech_fail_rate = failed_last_hour / float(total_last_hour)
            # Trigger when technical_failure_rate > 15% (strictly > 0.15)
            if tech_fail_rate > 0.15:
                rate_pct = round(tech_fail_rate * 100, 2)
                alerts.append({
                    "type": "FAILURE_RATE_SPIKE",
                    "severity": "HIGH",
                    "message": f"Technical failure rate in the last hour is {rate_pct}% (threshold: 15.0%).",
                    "currentValue": rate_pct,
                    "threshold": 15.0,
                    "window": "last_hour"
                })

        # --------------------------------------------------
        # B. VOLUME SPIKE
        # --------------------------------------------------
        current_hour_volume = total_last_hour
        baseline_24h_volume = len(baseline_parcels)
        baseline_hourly_volume = baseline_24h_volume / 24.0

        if baseline_hourly_volume > 0:
            # Trigger when current_hour_volume > 2 x baseline_hourly_volume (strictly > 2x)
            if current_hour_volume > 2.0 * baseline_hourly_volume:
                threshold_val = round(2.0 * baseline_hourly_volume, 2)
                alerts.append({
                    "type": "VOLUME_SPIKE",
                    "severity": "MEDIUM",
                    "message": f"Parcel volume in the last hour ({current_hour_volume}) exceeds 2x 24h baseline ({round(baseline_hourly_volume, 2)}/hr).",
                    "currentValue": current_hour_volume,
                    "threshold": threshold_val,
                    "window": "last_hour"
                })

        # --------------------------------------------------
        # C. DEPARTMENT SKEW
        # --------------------------------------------------
        dept_parcels_last_hour = [p for p in last_hour_parcels if p.get("department")]
        valid_dept_total = len(dept_parcels_last_hour)

        if valid_dept_total >= 5:
            counts = {
                "MAIL": sum(1 for p in dept_parcels_last_hour if p.get("department") == "MAIL"),
                "REGULAR": sum(1 for p in dept_parcels_last_hour if p.get("department") == "REGULAR"),
                "HEAVY": sum(1 for p in dept_parcels_last_hour if p.get("department") == "HEAVY")
            }
            for dept, cnt in counts.items():
                share = cnt / float(valid_dept_total)
                # Trigger if one department represents >80% of last-hour volume (strictly > 0.80)
                if share > 0.80:
                    share_pct = round(share * 100, 2)
                    alerts.append({
                        "type": "DEPARTMENT_SKEW",
                        "severity": "MEDIUM",
                        "message": f"Department '{dept}' represents {share_pct}% of routed volume in the last hour (threshold: 80.0%).",
                        "currentValue": share_pct,
                        "threshold": 80.0,
                        "department": dept,
                        "window": "last_hour"
                    })

        # --------------------------------------------------
        # D. INSURANCE SPIKE
        # --------------------------------------------------
        current_insurance_volume = sum(1 for p in last_hour_parcels if p.get("insuranceRequired") is True)
        baseline_24h_insurance = sum(1 for p in baseline_parcels if p.get("insuranceRequired") is True)
        baseline_hourly_insurance = baseline_24h_insurance / 24.0

        if baseline_hourly_insurance > 0:
            # Trigger when current_insurance_volume > 2 x baseline_hourly_insurance (strictly > 2x)
            if current_insurance_volume > 2.0 * baseline_hourly_insurance:
                threshold_val = round(2.0 * baseline_hourly_insurance, 2)
                alerts.append({
                    "type": "INSURANCE_SPIKE",
                    "severity": "MEDIUM",
                    "message": f"Insurance-required volume in the last hour ({current_insurance_volume}) exceeds 2x 24h baseline ({round(baseline_hourly_insurance, 2)}/hr).",
                    "currentValue": current_insurance_volume,
                    "threshold": threshold_val,
                    "window": "last_hour"
                })

        return {
            "success": True,
            "alerts": alerts
        }

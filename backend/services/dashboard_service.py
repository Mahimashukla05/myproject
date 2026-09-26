import logging
from models.parcel_model import ParcelModel

logger = logging.getLogger("parcel_routing_app")

class DashboardService:
    VALID_PERIODS = {"today", "week", "all"}

    @classmethod
    def get_summary(cls, period="all"):
        period_clean = str(period or "all").lower().strip()
        if period_clean not in cls.VALID_PERIODS:
            return {"success": False, "error": f"Invalid period '{period}'. Allowed periods: today, week, all."}, 400

        summary = ParcelModel.get_dashboard_summary(period=period_clean)
        if summary is None:
            logger.error("Dashboard summary failed: Database is currently unavailable.")
            return {
                "success": False,
                "error": "Database is currently unavailable. Please try again later.",
                "errorType": "TECHNICAL"
            }, 503

        return {"success": True, **summary}, 200

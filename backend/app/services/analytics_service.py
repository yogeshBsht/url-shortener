from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Click
from datetime import datetime, timedelta
from typing import Dict, List


class AnalyticsService:
    """Service for analytics operations."""
    
    @staticmethod
    def get_top_referrers(db: Session, short_code: str, limit: int = 5) -> List[Dict]:
        """
        Get top referring domains.
        
        Args:
            db: Database session
            short_code: Short code
            limit: Max results
        
        Returns:
            List of {referer, count} dicts
        """
        results = db.query(
            Click.referer,
            func.count(Click.id).label('count')
        ).filter(
            Click.short_code == short_code,
            Click.referer.isnot(None)
        ).group_by(
            Click.referer
        ).order_by(
            func.count(Click.id).desc()
        ).limit(limit).all()
        
        return [
            {"referer": row.referer, "count": row.count}
            for row in results
        ]
    
    @staticmethod
    def get_hourly_distribution(db: Session, short_code: str) -> Dict[int, int]:
        """
        Get click distribution by hour of day.
        
        Args:
            db: Database session
            short_code: Short code
        
        Returns:
            Dict mapping hour (0-23) to click count
        """
        results = db.query(
            func.extract('hour', Click.clicked_at).label('hour'),
            func.count(Click.id).label('count')
        ).filter(
            Click.short_code == short_code
        ).group_by(
            func.extract('hour', Click.clicked_at)
        ).all()
        
        distribution = {hour: 0 for hour in range(24)}
        for row in results:
            distribution[int(row.hour)] = row.count
        
        return distribution
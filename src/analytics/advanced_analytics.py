"""
Advanced Analytics Engine
Comprehensive analytics, trend analysis, and insights generation.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import statistics
import json
from enum import Enum

import numpy as np
from scipy import stats as scipy_stats


class TrendDirection(str, Enum):
    """Enum for trend directions."""
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    STABLE = "stable"


@dataclass
class DataPoint:
    """Represents a single data point."""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = None


@dataclass
class Trend:
    """Represents a trend in data."""
    direction: TrendDirection
    slope: float
    strength: float  # 0-1, higher = stronger trend
    start_date: datetime
    end_date: datetime
    predicted_value: Optional[float] = None


@dataclass
class Insight:
    """Represents an extracted insight."""
    title: str
    description: str
    impact: str  # "high", "medium", "low"
    category: str  # "performance", "behavior", "security", "usage"
    data_point: Optional[float] = None
    recommendation: Optional[str] = None


class AnalyticsEngine:
    """Advanced analytics and insights engine."""
    
    def __init__(self):
        self.data_cache: Dict[str, List[DataPoint]] = defaultdict(list)
        self.insights_cache: Dict[str, List[Insight]] = defaultdict(list)
        self.trend_cache: Dict[str, Trend] = {}
    
    # ==================== Trend Analysis ====================
    
    def detect_trend(
        self,
        data_points: List[Tuple[datetime, float]],
        window_size: int = 7
    ) -> Trend:
        """
        Detect trends in data using linear regression.
        
        Args:
            data_points: List of (timestamp, value) tuples
            window_size: Number of points to consider for trend
        
        Returns:
            Trend object containing direction, slope, and strength
        """
        if len(data_points) < window_size:
            return Trend(
                direction=TrendDirection.STABLE,
                slope=0.0,
                strength=0.0,
                start_date=data_points[0][0],
                end_date=data_points[-1][0]
            )
        
        # Use recent data points
        recent_points = data_points[-window_size:]
        
        # Extract values and create time indices
        values = np.array([p[1] for p in recent_points])
        x = np.arange(len(recent_points))
        
        # Perform linear regression
        slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(x, values)
        
        # Determine trend direction
        if abs(p_value) > 0.05:  # Not statistically significant
            direction = TrendDirection.STABLE
            strength = 0.0
        elif slope > 0:
            direction = TrendDirection.UPTREND
            strength = min(abs(r_value), 1.0)
        else:
            direction = TrendDirection.DOWNTREND
            strength = min(abs(r_value), 1.0)
        
        # Predict next value
        predicted_value = slope * (len(recent_points)) + intercept
        
        return Trend(
            direction=direction,
            slope=slope,
            strength=strength,
            start_date=recent_points[0][0],
            end_date=recent_points[-1][0],
            predicted_value=predicted_value
        )
    
    def detect_anomalies(
        self,
        data_points: List[float],
        method: str = "zscore",
        threshold: float = 2.0
    ) -> List[Tuple[int, float]]:
        """
        Detect anomalies in data.
        
        Args:
            data_points: List of numerical values
            method: "zscore" or "iqr"
            threshold: Sensitivity threshold
        
        Returns:
            List of (index, value) tuples for anomalies
        """
        anomalies = []
        
        if method == "zscore":
            if len(data_points) < 2:
                return anomalies
            
            mean = statistics.mean(data_points)
            std_dev = statistics.stdev(data_points) if len(data_points) > 1 else 0
            
            for idx, value in enumerate(data_points):
                if std_dev > 0:
                    z_score = abs((value - mean) / std_dev)
                    if z_score > threshold:
                        anomalies.append((idx, value))
        
        elif method == "iqr":
            sorted_data = sorted(data_points)
            q1 = sorted_data[len(sorted_data) // 4]
            q3 = sorted_data[3 * len(sorted_data) // 4]
            iqr = q3 - q1
            
            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr
            
            for idx, value in enumerate(data_points):
                if value < lower_bound or value > upper_bound:
                    anomalies.append((idx, value))
        
        return anomalies
    
    # ==================== Statistical Analysis ====================
    
    def calculate_statistics(
        self,
        data_points: List[float]
    ) -> Dict[str, float]:
        """Calculate comprehensive statistics."""
        if not data_points:
            return {}
        
        return {
            "count": len(data_points),
            "mean": statistics.mean(data_points),
            "median": statistics.median(data_points),
            "std_dev": statistics.stdev(data_points) if len(data_points) > 1 else 0,
            "variance": statistics.variance(data_points) if len(data_points) > 1 else 0,
            "min": min(data_points),
            "max": max(data_points),
            "range": max(data_points) - min(data_points),
            "q1": sorted(data_points)[len(data_points) // 4],
            "q3": sorted(data_points)[3 * len(data_points) // 4],
        }
    
    def calculate_correlation(
        self,
        series1: List[float],
        series2: List[float]
    ) -> float:
        """Calculate Pearson correlation between two series."""
        if len(series1) != len(series2) or len(series1) < 2:
            return 0.0
        
        correlation, _ = scipy_stats.pearsonr(series1, series2)
        return correlation
    
    # ==================== Performance Analysis ====================
    
    def analyze_quiz_performance(
        self,
        quiz_scores: List[float],
        quiz_times: List[float],
        time_unit: str = "minutes"
    ) -> Dict[str, Any]:
        """
        Analyze quiz performance metrics.
        
        Args:
            quiz_scores: List of quiz scores (0-100)
            quiz_times: List of time taken for each quiz
            time_unit: Unit of time
        
        Returns:
            Performance analysis dictionary
        """
        stats = self.calculate_statistics(quiz_scores)
        
        # Calculate improvement trend
        improvement_trend = None
        if len(quiz_scores) >= 2:
            improvement_trend = self.detect_trend(
                [(datetime.now() - timedelta(days=i), v) for i, v in enumerate(reversed(quiz_scores))],
                window_size=min(5, len(quiz_scores))
            )
        
        # Calculate efficiency (score per unit time)
        efficiency_scores = []
        for score, time in zip(quiz_scores, quiz_times):
            if time > 0:
                efficiency_scores.append(score / time)
        
        efficiency_stats = self.calculate_statistics(efficiency_scores) if efficiency_scores else {}
        
        return {
            "score_statistics": stats,
            "improvement_trend": {
                "direction": improvement_trend.direction if improvement_trend else None,
                "strength": improvement_trend.strength if improvement_trend else 0.0
            },
            "efficiency_metrics": efficiency_stats,
            "time_statistics": self.calculate_statistics(quiz_times)
        }
    
    def analyze_learning_patterns(
        self,
        activity_log: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze learning patterns from activity logs.
        
        Args:
            activity_log: List of activity records with timestamp and type
        
        Returns:
            Learning pattern analysis
        """
        if not activity_log:
            return {}
        
        # Group by time of day
        hourly_distribution = defaultdict(int)
        daily_distribution = defaultdict(int)
        activity_types = defaultdict(int)
        
        for log in activity_log:
            timestamp = datetime.fromisoformat(log.get("timestamp", datetime.now().isoformat()))
            hourly_distribution[timestamp.hour] += 1
            daily_distribution[timestamp.weekday()] += 1
            activity_types[log.get("type", "unknown")] += 1
        
        # Find peak activity hours
        peak_hours = sorted(
            hourly_distribution.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # Find most active days
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        peak_days = sorted(
            daily_distribution.items(),
            key=lambda x: x[1],
            reverse=True
        )[:2]
        
        return {
            "hourly_distribution": dict(hourly_distribution),
            "daily_distribution": {days[k]: v for k, v in daily_distribution.items()},
            "peak_activity_hours": [h[0] for h in peak_hours],
            "peak_activity_days": [days[d[0]] for d in peak_days],
            "activity_breakdown": dict(activity_types),
            "total_activities": len(activity_log)
        }
    
    # ==================== Insights Generation ====================
    
    def generate_insights(
        self,
        quiz_data: Dict[str, Any],
        user_profile: Dict[str, Any],
        activity_log: List[Dict[str, Any]]
    ) -> List[Insight]:
        """
        Generate actionable insights from various data sources.
        
        Args:
            quiz_data: Quiz performance data
            user_profile: User profile information
            activity_log: User activity log
        
        Returns:
            List of Insight objects
        """
        insights = []
        
        # Performance insights
        quiz_scores = quiz_data.get("scores", [])
        if quiz_scores:
            avg_score = statistics.mean(quiz_scores)
            
            if avg_score >= 85:
                insights.append(Insight(
                    title="Excellent Performance",
                    description=f"Your average quiz score is {avg_score:.1f}%, indicating strong mastery",
                    impact="high",
                    category="performance",
                    data_point=avg_score,
                    recommendation="Consider challenging advanced topics"
                ))
            elif avg_score < 60:
                insights.append(Insight(
                    title="Improvement Needed",
                    description=f"Average score of {avg_score:.1f}% suggests review of fundamentals",
                    impact="high",
                    category="performance",
                    data_point=avg_score,
                    recommendation="Focus on core concepts; consider study materials"
                ))
        
        # Activity insights
        if activity_log:
            patterns = self.analyze_learning_patterns(activity_log)
            peak_hours = patterns.get("peak_activity_hours", [])
            
            if peak_hours:
                insights.append(Insight(
                    title="Peak Learning Time",
                    description=f"You're most active between {peak_hours[0]:02d}:00-{peak_hours[0]+1:02d}:00",
                    impact="medium",
                    category="behavior",
                    recommendation="Schedule important quizzes during your peak hours"
                ))
        
        # Progress insights
        if len(quiz_scores) >= 3:
            trend = self.detect_trend(
                [(datetime.now() - timedelta(days=i), v) for i, v in enumerate(reversed(quiz_scores))],
                window_size=min(5, len(quiz_scores))
            )
            
            if trend.direction == TrendDirection.UPTREND:
                insights.append(Insight(
                    title="Positive Progress",
                    description=f"Your scores show a {trend.strength*100:.0f}% upward trend",
                    impact="high",
                    category="performance",
                    recommendation="Continue with current study strategy"
                ))
            elif trend.direction == TrendDirection.DOWNTREND:
                insights.append(Insight(
                    title="Score Decline Detected",
                    description=f"Recent scores show a {trend.strength*100:.0f}% downward trend",
                    impact="high",
                    category="performance",
                    recommendation="Review recent material; consider adjusting study routine"
                ))
        
        return insights
    
    # ==================== Predictive Analytics ====================
    
    def predict_performance(
        self,
        historical_scores: List[float],
        future_periods: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Predict future performance based on historical data.
        
        Args:
            historical_scores: List of past scores
            future_periods: Number of periods to predict
        
        Returns:
            List of predictions with confidence intervals
        """
        if len(historical_scores) < 2:
            return []
        
        # Fit linear regression model
        x = np.arange(len(historical_scores))
        y = np.array(historical_scores)
        
        slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(x, y)
        
        predictions = []
        for period in range(1, future_periods + 1):
            predicted_value = slope * (len(historical_scores) + period - 1) + intercept
            
            # Calculate confidence interval (simple approximation)
            confidence = (0.95 - abs(p_value)) * 100
            error_margin = std_err * period
            
            predictions.append({
                "period": period,
                "predicted_score": max(0, min(100, predicted_value)),  # Clamp to 0-100
                "confidence": max(0, min(100, confidence)),
                "lower_bound": max(0, predicted_value - error_margin),
                "upper_bound": min(100, predicted_value + error_margin)
            })
        
        return predictions
    
    # ==================== Data Export ====================
    
    def export_analytics_report(
        self,
        filename: str,
        analytics_data: Dict[str, Any]
    ) -> bool:
        """
        Export analytics report to JSON file.
        
        Args:
            filename: Output filename
            analytics_data: Analytics data to export
        
        Returns:
            True if successful
        """
        try:
            with open(filename, 'w') as f:
                json.dump(analytics_data, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error exporting analytics: {str(e)}")
            return False
    
    def generate_summary_report(
        self,
        user_id: str,
        time_period: str = "month"
    ) -> Dict[str, Any]:
        """
        Generate comprehensive summary report for a user.
        
        Args:
            user_id: User identifier
            time_period: "week", "month", or "all"
        
        Returns:
            Summary report dictionary
        """
        return {
            "generated_at": datetime.now().isoformat(),
            "user_id": user_id,
            "period": time_period,
            "summary": {
                "total_quizzes": 0,
                "average_score": 0.0,
                "improvement_trend": "stable",
                "key_insights": []
            }
        }


# ==================== Utility Functions ====================

def calculate_percentile(data: List[float], percentile: float) -> float:
    """Calculate percentile rank."""
    if not data:
        return 0.0
    return np.percentile(data, percentile)


def calculate_confidence_interval(
    data: List[float],
    confidence: float = 0.95
) -> Tuple[float, float]:
    """
    Calculate confidence interval for mean.
    
    Returns:
        (lower_bound, upper_bound)
    """
    if len(data) < 2:
        return (0.0, 0.0)
    
    mean = statistics.mean(data)
    std_err = statistics.stdev(data) / (len(data) ** 0.5)
    
    # Use t-distribution (more appropriate for small samples)
    t_value = scipy_stats.t.ppf((1 + confidence) / 2, len(data) - 1)
    margin_of_error = t_value * std_err
    
    return (mean - margin_of_error, mean + margin_of_error)

"""
Analytics Dashboard UI
Streamlit interface for displaying advanced analytics and insights.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import requests

import src.config as config
from src.analytics.advanced_analytics import AnalyticsEngine, TrendDirection
from src.frontend.ui_components import ResponsiveLayout, InteractiveComponents


def format_datetime(iso_string: Optional[str]) -> str:
    """Format ISO datetime string to human-readable format."""
    if not iso_string:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %I:%M %p")
    except (ValueError, AttributeError):
        return iso_string


def render_analytics_dashboard():
    """Render the main analytics dashboard."""
    st.set_page_config(page_title="Analytics Dashboard", layout="wide")
    st.title("📊 Analytics Dashboard")
    
    # Initialize session state
    if "analytics_engine" not in st.session_state:
        st.session_state.analytics_engine = AnalyticsEngine()
    
    engine = st.session_state.analytics_engine
    
    # Sidebar navigation
    with st.sidebar:
        st.title("Navigation")
        tab = st.radio(
            "Select View",
            ["Overview", "Performance", "Learning Patterns", "Predictions", "Insights"]
        )
        
        time_period = st.selectbox(
            "Time Period",
            ["Last Week", "Last Month", "Last 3 Months", "All Time"]
        )
    
    try:
        token = st.session_state.get("auth_token", "")
        headers = {"Authorization": f"Bearer {token}"}
        
        if tab == "Overview":
            render_overview(headers, engine, time_period)
        elif tab == "Performance":
            render_performance_analysis(headers, engine, time_period)
        elif tab == "Learning Patterns":
            render_learning_patterns(headers, engine, time_period)
        elif tab == "Predictions":
            render_predictions(headers, engine)
        else:
            render_insights(headers, engine)
    
    except Exception as e:
        InteractiveComponents.notification(f"Error: {str(e)}", "error")


def render_overview(headers: Dict, engine, time_period: str):
    """Render analytics overview."""
    st.markdown("## Your Analytics Overview")
    
    try:
        # Fetch user analytics
        period_map = {
            "Last Week": 7,
            "Last Month": 30,
            "Last 3 Months": 90,
            "All Time": 365
        }
        days = period_map.get(time_period, 30)
        
        response = requests.get(
            f"{config.fastapi_url}/analytics/user?days={days}",
            headers=headers
        )
        
        if response.status_code != 200:
            st.error("Failed to load analytics data")
            return
        
        data = response.json()
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            ResponsiveLayout.stat_card(
                "Total Quizzes",
                str(data.get("total_quizzes", 0)),
                "📝",
                "#667eea"
            )
        
        with col2:
            avg_score = data.get("average_score", 0)
            ResponsiveLayout.stat_card(
                "Average Score",
                f"{avg_score:.1f}%",
                "⭐",
                "#4CAF50"
            )
        
        with col3:
            total_time = data.get("total_study_time_minutes", 0)
            ResponsiveLayout.stat_card(
                "Study Time",
                f"{total_time // 60}h",
                "⏱️",
                "#FF9800"
            )
        
        with col4:
            streak = data.get("current_streak", 0)
            ResponsiveLayout.stat_card(
                "Current Streak",
                f"{streak} days",
                "🔥",
                "#F44336"
            )
        
        # Score distribution
        st.markdown("---")
        st.markdown("### Score Distribution")
        
        scores = data.get("quiz_scores", [])
        if scores:
            # Create histogram
            fig = px.histogram(
                x=scores,
                nbins=10,
                labels={"x": "Score", "count": "Number of Quizzes"},
                title="Quiz Score Distribution"
            )
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        # Recent activity
        st.markdown("---")
        st.markdown("### Recent Activity")
        
        activity_log = data.get("activity_log", [])[:10]
        
        activity_items = []
        for log in activity_log:
            activity_items.append({
                "Time": log.get("timestamp", "N/A"),
                "Activity": log.get("type", "N/A").replace("_", " ").title(),
                "Details": log.get("subject_id", "N/A")
            })
        
        if activity_items:
            st.dataframe(
                pd.DataFrame(activity_items),
                use_container_width=True,
                hide_index=True
            )
    
    except Exception as e:
        st.error(f"Error rendering overview: {str(e)}")


def render_performance_analysis(headers: Dict, engine, time_period: str):
    """Render detailed performance analysis."""
    st.markdown("## Performance Analysis")
    
    try:
        response = requests.get(
            f"{config.fastapi_url}/analytics/performance",
            headers=headers
        )
        
        if response.status_code != 200:
            st.error("Failed to load performance data")
            return
        
        perf_data = response.json()
        quiz_scores = perf_data.get("quiz_scores", [])
        quiz_times = perf_data.get("quiz_times", [])
        
        if not quiz_scores:
            st.info("No quiz data available")
            return
        
        # Performance analysis
        analysis = engine.analyze_quiz_performance(quiz_scores, quiz_times)
        stats = analysis.get("score_statistics", {})
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Quizzes",
                stats.get("count", 0)
            )
        
        with col2:
            st.metric(
                "Highest Score",
                f"{stats.get('max', 0):.1f}%"
            )
        
        with col3:
            st.metric(
                "Lowest Score",
                f"{stats.get('min', 0):.1f}%"
            )
        
        with col4:
            st.metric(
                "Score Std Dev",
                f"{stats.get('std_dev', 0):.1f}%"
            )
        
        # Score progression
        st.markdown("---")
        st.markdown("### Score Progression Over Time")
        
        df = pd.DataFrame({
            "Quiz": range(1, len(quiz_scores) + 1),
            "Score": quiz_scores
        })
        
        fig = px.line(
            df,
            x="Quiz",
            y="Score",
            markers=True,
            title="Quiz Scores Over Time"
        )
        fig.add_hline(y=statistics.mean(quiz_scores), line_dash="dash", line_color="red",
                     annotation_text="Average", annotation_position="right")
        fig.update_layout(height=400, yaxis_range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)
        
        # Efficiency analysis
        st.markdown("---")
        st.markdown("### Efficiency Metrics")
        
        efficiency_stats = analysis.get("efficiency_metrics", {})
        time_stats = analysis.get("time_statistics", {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Avg Quiz Time",
                f"{time_stats.get('mean', 0):.0f} min"
            )
        
        with col2:
            st.metric(
                "Min Time",
                f"{time_stats.get('min', 0):.0f} min"
            )
        
        with col3:
            st.metric(
                "Max Time",
                f"{time_stats.get('max', 0):.0f} min"
            )
        
        # Improvement trend
        improvement = analysis.get("improvement_trend", {})
        if improvement.get("direction"):
            trend_emoji = "📈" if improvement["direction"] == "uptrend" else "📉"
            InteractiveComponents.notification(
                f"{trend_emoji} Trend: {improvement['direction'].upper()} (Strength: {improvement['strength']*100:.0f}%)",
                "success" if improvement["direction"] == "uptrend" else "warning"
            )
    
    except Exception as e:
        st.error(f"Error in performance analysis: {str(e)}")


def render_learning_patterns(headers: Dict, engine, time_period: str):
    """Render learning patterns analysis."""
    st.markdown("## Learning Patterns")
    
    try:
        response = requests.get(
            f"{config.fastapi_url}/analytics/learning-patterns",
            headers=headers
        )
        
        if response.status_code != 200:
            st.error("Failed to load learning patterns")
            return
        
        activity_log = response.json().get("activity_log", [])
        
        if not activity_log:
            st.info("No activity data available")
            return
        
        patterns = engine.analyze_learning_patterns(activity_log)
        
        # Hourly distribution
        st.markdown("### Activity by Hour of Day")
        
        hourly_data = patterns.get("hourly_distribution", {})
        if hourly_data:
            hours = list(range(24))
            counts = [hourly_data.get(str(h), 0) for h in hours]
            
            fig = px.bar(
                x=hours,
                y=counts,
                labels={"x": "Hour of Day", "y": "Number of Activities"},
                title="Activity Distribution by Hour"
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        
        # Daily distribution
        st.markdown("---")
        st.markdown("### Activity by Day of Week")
        
        daily_data = patterns.get("daily_distribution", {})
        if daily_data:
            fig = px.bar(
                x=list(daily_data.keys()),
                y=list(daily_data.values()),
                labels={"x": "Day", "y": "Number of Activities"},
                title="Activity Distribution by Day"
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        
        # Activity types
        st.markdown("---")
        st.markdown("### Activity Breakdown")
        
        activity_types = patterns.get("activity_breakdown", {})
        if activity_types:
            fig = px.pie(
                labels=list(activity_types.keys()),
                values=list(activity_types.values()),
                title="Activity Types"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Peak times summary
        col1, col2, col3 = st.columns(3)
        
        with col1:
            peak_hours = patterns.get("peak_activity_hours", [])
            if peak_hours:
                st.metric("Peak Hour", f"{peak_hours[0]:02d}:00 - {peak_hours[0]+1:02d}:00")
        
        with col2:
            peak_days = patterns.get("peak_activity_days", [])
            if peak_days:
                st.metric("Most Active Day", peak_days[0])
        
        with col3:
            total = patterns.get("total_activities", 0)
            st.metric("Total Activities", total)
    
    except Exception as e:
        st.error(f"Error analyzing learning patterns: {str(e)}")


def render_predictions(headers: Dict, engine):
    """Render performance predictions."""
    st.markdown("## Performance Predictions")
    
    try:
        response = requests.get(
            f"{config.fastapi_url}/analytics/user/quiz-scores",
            headers=headers
        )
        
        if response.status_code != 200:
            st.info("Not enough data for predictions")
            return
        
        quiz_scores = response.json().get("scores", [])
        
        if len(quiz_scores) < 2:
            st.info("Need at least 2 quizzes to generate predictions")
            return
        
        # Generate predictions
        predictions = engine.predict_performance(quiz_scores, future_periods=5)
        
        if predictions:
            st.markdown("### Next 5 Quiz Predictions")
            
            # Prepare data for visualization
            pred_data = pd.DataFrame(predictions)
            
            fig = go.Figure()
            
            # Historical scores
            fig.add_trace(go.Scatter(
                x=list(range(len(quiz_scores))),
                y=quiz_scores,
                mode='lines+markers',
                name='Historical Scores',
                line=dict(color='blue')
            ))
            
            # Predictions
            x_pred = list(range(len(quiz_scores), len(quiz_scores) + len(predictions)))
            fig.add_trace(go.Scatter(
                x=x_pred,
                y=pred_data['predicted_score'],
                mode='lines+markers',
                name='Predicted Scores',
                line=dict(color='red', dash='dash')
            ))
            
            # Confidence interval
            fig.add_trace(go.Scatter(
                x=x_pred + x_pred[::-1],
                y=list(pred_data['upper_bound']) + list(pred_data['lower_bound'][::-1]),
                fill='toself',
                fillcolor='rgba(255, 0, 0, 0.2)',
                line=dict(color='rgba(255,255,255,0)'),
                name='95% Confidence Interval'
            ))
            
            fig.update_layout(
                title="Quiz Score Predictions",
                xaxis_title="Quiz Number",
                yaxis_title="Score",
                height=400,
                yaxis_range=[0, 100]
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Prediction details
            st.markdown("---")
            st.markdown("### Prediction Details")
            
            pred_display = []
            for pred in predictions:
                pred_display.append({
                    "Quiz #": pred["period"],
                    "Predicted Score": f"{pred['predicted_score']:.1f}%",
                    "Confidence": f"{pred['confidence']:.0f}%",
                    "Range": f"{pred['lower_bound']:.1f}% - {pred['upper_bound']:.1f}%"
                })
            
            st.dataframe(
                pd.DataFrame(pred_display),
                use_container_width=True,
                hide_index=True
            )
    
    except Exception as e:
        st.error(f"Error generating predictions: {str(e)}")


def render_insights(headers: Dict, engine):
    """Render AI-generated insights."""
    st.markdown("## AI-Generated Insights")
    
    try:
        response = requests.get(
            f"{config.fastapi_url}/analytics/insights",
            headers=headers
        )
        
        if response.status_code != 200:
            st.error("Failed to load insights")
            return
        
        insights_data = response.json()
        insights_list = insights_data.get("insights", [])
        
        if not insights_list:
            st.info("No insights available yet")
            return
        
        # Display insights organized by category
        st.markdown("### Key Insights")
        
        # Filter by impact level
        impact_filter = st.multiselect(
            "Filter by Impact Level:",
            ["high", "medium", "low"],
            default=["high", "medium"]
        )
        
        filtered_insights = [
            i for i in insights_list
            if i.get("impact") in impact_filter
        ]
        
        for idx, insight in enumerate(filtered_insights[:10], 1):
            impact_color_map = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢"
            }
            impact_emoji = impact_color_map.get(insight.get("impact"), "⚪")
            
            with st.expander(f"{impact_emoji} {insight.get('title', 'Insight')}"):
                st.markdown(f"**Category:** {insight.get('category', 'N/A').title()}")
                st.markdown(f"**Impact:** {insight.get('impact', 'N/A').upper()}")
                st.markdown(f"**Description:** {insight.get('description', 'N/A')}")
                
                if insight.get("recommendation"):
                    st.markdown(f"**Recommendation:** {insight.get('recommendation')}")
                
                if insight.get("data_point"):
                    st.markdown(f"**Data Point:** {insight.get('data_point'):.1f}")
        
        # Summary statistics
        st.markdown("---")
        st.markdown("### Insights Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            high_impact = len([i for i in insights_list if i.get("impact") == "high"])
            st.metric("High Impact", high_impact)
        
        with col2:
            categories = set(i.get("category") for i in insights_list)
            st.metric("Categories", len(categories))
        
        with col3:
            st.metric("Total Insights", len(insights_list))
    
    except Exception as e:
        st.error(f"Error loading insights: {str(e)}")


import statistics

if __name__ == "__main__":
    render_analytics_dashboard()

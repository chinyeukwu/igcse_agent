"""
Modern Student Dashboard with Gamification
Displays user stats, achievements, streaks, and personalized recommendations.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import json

import src.config as config
from src.frontend.ui_components import GameComponents, ThemeManager, ResponsiveLayout, InteractiveComponents


def format_datetime(iso_string: Optional[str]) -> str:
    """Format ISO datetime string to human-readable format."""
    if not iso_string:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %I:%M %p")
    except (ValueError, AttributeError):
        return iso_string


def calculate_level_and_xp(total_quizzes: int, average_score: float) -> tuple:
    """Calculate user level and XP based on quiz performance."""
    # Level = 1 + (total_quizzes // 10)
    level = 1 + (total_quizzes // 10)
    
    # XP per quiz = average_score (0-100)
    total_xp = int(total_quizzes * (average_score or 50))
    xp_for_next_level = (level + 1) * 1000
    xp_current_level = total_xp % xp_for_next_level
    
    return level, xp_current_level, xp_for_next_level


def calculate_streak(quiz_dates: List[str]) -> tuple:
    """Calculate current and longest streaks."""
    if not quiz_dates:
        return 0, 0
    
    # Parse dates
    dates = sorted([datetime.fromisoformat(d).date() for d in quiz_dates if d])
    if not dates:
        return 0, 0
    
    current_streak = 0
    max_streak = 0
    today = datetime.now().date()
    
    # Check current streak
    temp_date = today
    for date in reversed(dates):
        if (temp_date - date).days == 0 or (temp_date - date).days == 1:
            current_streak += 1
            temp_date = date
        else:
            break
    
    # Check all streaks for longest
    current_run = 1
    for i in range(len(dates) - 1, 0, -1):
        if (dates[i - 1] - dates[i]).days == 1:
            current_run += 1
            max_streak = max(max_streak, current_run)
        else:
            current_run = 1
    
    return current_streak, max_streak


def get_earned_badges(quiz_history: List[Dict], total_quizzes: int, average_score: float) -> List[str]:
    """Determine which badges user has earned."""
    earned = []
    
    if total_quizzes >= 10:
        earned.append("quiz_master")
    
    if average_score >= 80:
        earned.append("top_performer")
    
    if total_quizzes >= 50:
        earned.append("consistency_king")
    
    # Check for speed demon (3 quizzes in one day)
    today_quizzes = sum(1 for q in quiz_history if q.get("created_at", "").startswith(datetime.now().strftime("%Y-%m-%d")))
    if today_quizzes >= 3:
        earned.append("speed_demon")
    
    # Check for subject expert (perfect score)
    perfect_scores = [q for q in quiz_history if q.get("score", 0) == 100]
    if perfect_scores:
        earned.append("subject_expert")
    
    return earned


def render_dashboard(token: str, username: str):
    """Render the modern gamified student dashboard."""
    
    # Initialize theme
    ThemeManager.initialize_theme()
    ThemeManager.theme_toggle()
    
    st.title("🎓 Your Learning Dashboard")
    
    # Fetch user statistics
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{config.fastapi_url}/quiz/statistics", headers=headers)
        
        if response.status_code != 200:
            st.error("Failed to load your statistics. Please refresh.")
            return
        
        stats = response.json()
        
        # Extract stats
        total_quizzes = stats.get("total_quizzes", 0)
        average_score = stats.get("average_score", 0)
        quiz_history = stats.get("quiz_history", [])
        
        # Calculate gamification metrics
        level, xp_current, xp_next = calculate_level_and_xp(total_quizzes, average_score)
        current_streak, longest_streak = calculate_streak([q.get("created_at") for q in quiz_history])
        earned_badges = get_earned_badges(quiz_history, total_quizzes, average_score)
        
        # Header section with personalized greeting
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"### Welcome back, **{username}**! 👋")
            st.markdown(f"You're on a **{current_streak} day streak** 🔥")
        
        with col2:
            GameComponents.level_card(level, xp_current, xp_next)
        
        with col3:
            ResponsiveLayout.stat_card(
                "Total Quizzes", 
                str(total_quizzes),
                "📊",
                "#667eea"
            )
        
        # Streak and progress section
        st.markdown("---")
        st.markdown("### Your Progress")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            ResponsiveLayout.stat_card(
                "Average Score",
                f"{average_score:.1f}%",
                "✅",
                "#4CAF50"
            )
        with col2:
            ResponsiveLayout.stat_card(
                "Longest Streak",
                f"{longest_streak} days",
                "🏆",
                "#FF9800"
            )
        with col3:
            ResponsiveLayout.stat_card(
                "Current Streak",
                f"{current_streak} days",
                "🔥",
                "#F44336"
            )
        
        # Main progress sections
        st.markdown("---")
        st.markdown("### Learning Goals")
        
        GameComponents.display_progress_bar(
            "Quiz Completion (Target: 20)",
            min(total_quizzes, 20),
            20,
            "#667eea"
        )
        
        GameComponents.display_progress_bar(
            "Score Goal (Target: 85%)",
            average_score,
            100,
            "#4CAF50"
        )
        
        GameComponents.display_progress_bar(
            "Level Up Progress",
            xp_current,
            xp_next,
            "#FF9800"
        )
        
        # Achievements/Badges section
        st.markdown("---")
        st.markdown("### Achievements Unlocked")
        st.caption(f"You've earned {len(earned_badges)} badges!")
        
        GameComponents.display_badges_grid(earned_badges, all_badges=False)
        
        with st.expander("View all badges"):
            GameComponents.display_badges_grid(list(GameComponents.BADGES.keys()), all_badges=True)
        
        # Recent quizzes section
        st.markdown("---")
        st.markdown("### Recent Quizzes")
        
        if quiz_history:
            for quiz in quiz_history[:5]:  # Show last 5
                ResponsiveLayout.quiz_card(
                    quiz.get("subject", "Unknown").title(),
                    quiz.get("difficulty", "medium"),
                    quiz.get("score", 0),
                    quiz.get("created_at", "Unknown")[:10]
                )
        else:
            st.info("Start taking quizzes to see your progress here!")
        
        # Subject performance breakdown
        st.markdown("---")
        st.markdown("### Performance by Subject")
        
        by_subject = stats.get("by_subject", {})
        if by_subject:
            cols = st.columns(len(by_subject))
            for idx, (subject, metrics) in enumerate(by_subject.items()):
                with cols[idx]:
                    ResponsiveLayout.stat_card(
                        subject.title(),
                        f"{metrics.get('avg_score', 0):.0f}%",
                        "📈",
                        "#667eea"
                    )
                    st.caption(f"{metrics.get('count', 0)} quizzes")
        
        # Call to action
        st.markdown("---")
        st.markdown("### What's Next?")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🎯 Take a Quiz", use_container_width=True):
                st.session_state.page = "quiz"
                st.rerun()
        
        with col2:
            if st.button("📚 Review Subjects", use_container_width=True):
                st.session_state.page = "subjects"
                st.rerun()
        
        with col3:
            if st.button("💬 Chat with AI", use_container_width=True):
                st.session_state.page = "chat"
                st.rerun()
        
        # Hidden notification for streak milestones
        if current_streak > 0 and current_streak % 7 == 0:
            InteractiveComponents.notification(
                f"Milestone reached! Your {current_streak}-day streak is amazing! 🎉",
                "success"
            )
    
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")
        InteractiveComponents.notification(
            "Connection error - using cached data",
            "warning"
        )


def render_quick_start():
    """Render quick start section for new users."""
    st.markdown("""
    ## Getting Started 🚀
    
    Welcome to your personalized IGCSE learning platform!
    
    ### How Gamification Works:
    - **Levels**: Gain XP from every quiz to level up
    - **Streaks**: Take daily quizzes to build your streak
    - **Badges**: Unlock achievements by hitting milestones
    - **Leaderboards**: Compete with classmates (coming soon)
    
    ### Quick Tips:
    1. Start with **Easy** quizzes to build confidence
    2. Gradually increase difficulty as you improve
    3. Focus on weak subjects to balance your skills
    4. Daily quizzes help maintain your streak
    
    Ready to get started? Pick a subject and take your first quiz!
    """)
    
    ResponsiveLayout.subject_button_grid(
        ["Maths", "English", "French", "Science", "FineArts"]
    )

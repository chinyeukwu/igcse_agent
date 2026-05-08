"""
Modern Streamlit UI Components for IGCSE Tutor
Gamification, achievements, streaks, and responsive design elements.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class GameComponents:
    """Gamification components for Streamlit UI."""
    
    # Achievement badges
    BADGES = {
        "quiz_master": {"emoji": "🏆", "name": "Quiz Master", "description": "Completed 10 quizzes"},
        "streak_warrior": {"emoji": "🔥", "name": "Streak Warrior", "description": "7-day streak"},
        "top_performer": {"emoji": "⭐", "name": "Top Performer", "description": "Average score > 80%"},
        "consistency_king": {"emoji": "👑", "name": "Consistency King", "description": "Took 50+ quizzes"},
        "speed_demon": {"emoji": "⚡", "name": "Speed Demon", "description": "Completed 3 quizzes in one day"},
        "subject_expert": {"emoji": "🧠", "name": "Subject Expert", "description": "Perfect score on any subject"},
        "night_owl": {"emoji": "🌙", "name": "Night Owl", "description": "Quiz at midnight"},
        "early_bird": {"emoji": "🌅", "name": "Early Bird", "description": "Quiz before 6am"},
    }
    
    @staticmethod
    def display_badge(badge_key: str, earned: bool = True):
        """Display a single achievement badge."""
        if badge_key not in GameComponents.BADGES:
            return
        
        badge = GameComponents.BADGES[badge_key]
        opacity = 1.0 if earned else 0.3
        
        with st.container():
            col1, col2 = st.columns([1, 3])
            with col1:
                # Emoji with opacity effect
                st.markdown(f"<div style='font-size: 2em; opacity: {opacity};'>{badge['emoji']}</div>", 
                           unsafe_allow_html=True)
            with col2:
                st.markdown(f"**{badge['name']}**")
                st.caption(f"<div style='opacity: {opacity};'>{badge['description']}</div>", 
                          unsafe_allow_html=True)
    
    @staticmethod
    def display_badges_grid(earned_badges: List[str], all_badges: bool = False):
        """Display badges in a responsive grid."""
        badges_to_show = GameComponents.BADGES if all_badges else {k: GameComponents.BADGES[k] for k in earned_badges}
        
        cols = st.columns(4)
        for idx, (badge_key, badge_data) in enumerate(badges_to_show.items()):
            with cols[idx % 4]:
                earned = badge_key in earned_badges
                GameComponents.display_badge(badge_key, earned)
    
    @staticmethod
    def display_streak(current_streak: int, longest_streak: int):
        """Display streak information with visual indicator."""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Current Streak", f"{current_streak} days", 
                     delta=f"🔥" if current_streak > 0 else "Start one today!")
        
        with col2:
            st.metric("Longest Streak", f"{longest_streak} days")
        
        with col3:
            # Next milestone
            milestone = ((current_streak // 7) + 1) * 7
            until_milestone = milestone - current_streak
            st.metric("Until Next Milestone", f"{until_milestone} days", 
                     delta=f"{milestone}-day streak")
    
    @staticmethod
    def display_progress_bar(label: str, value: float, max_value: float = 100.0, 
                            color: str = "#00D9FF"):
        """Display a styled progress bar."""
        percentage = (value / max_value) * 100
        
        html_str = f"""
        <div style="margin: 20px 0;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="font-weight: bold;">{label}</span>
                <span style="font-weight: bold;">{value:.1f}/{max_value:.1f}</span>
            </div>
            <div style="width: 100%; height: 20px; background-color: #f0f0f0; border-radius: 10px; 
                       overflow: hidden; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);">
                <div style="width: {percentage}%; height: 100%; background: linear-gradient(90deg, {color} 0%, 
                           {color}dd 100%); transition: width 0.3s ease;"></div>
            </div>
        </div>
        """
        st.markdown(html_str, unsafe_allow_html=True)
    
    @staticmethod
    def level_card(level: int, xp_current: int, xp_next_level: int):
        """Display player level card with XP progress."""
        xp_progress = (xp_current / xp_next_level) * 100
        
        html_str = f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   padding: 20px; border-radius: 15px; color: white; text-align: center;
                   box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <div style="font-size: 14px; opacity: 0.9;">LEVEL</div>
            <div style="font-size: 48px; font-weight: bold; margin: 10px 0;">{level}</div>
            <div style="background: rgba(255,255,255,0.2); height: 8px; border-radius: 4px; 
                       margin: 15px 0; overflow: hidden;">
                <div style="width: {xp_progress}%; height: 100%; background: white;"></div>
            </div>
            <div style="font-size: 12px; opacity: 0.9;">{xp_current}/{xp_next_level} XP</div>
        </div>
        """
        st.markdown(html_str, unsafe_allow_html=True)


class ThemeManager:
    """Manage dark/light theme for the application."""
    
    @staticmethod
    def initialize_theme():
        """Initialize theme settings in session state."""
        if "theme" not in st.session_state:
            st.session_state.theme = "light"
    
    @staticmethod
    def theme_toggle():
        """Display theme toggle button."""
        col1, col2 = st.columns([11, 1])
        with col2:
            current_theme = st.session_state.get("theme", "light")
            new_theme = "dark" if current_theme == "light" else "light"
            emoji = "🌙" if current_theme == "light" else "☀️"
            
            if st.button(emoji, key="theme_toggle", help="Toggle dark/light mode"):
                st.session_state.theme = new_theme
                st.rerun()
    
    @staticmethod
    def get_css_styles():
        """Get CSS styles based on current theme."""
        current_theme = st.session_state.get("theme", "light")
        
        if current_theme == "dark":
            return """
            <style>
                .stMetric { background-color: #1e1e1e; border-radius: 10px; padding: 15px; }
                .stExpander { background-color: #2a2a2a; }
                .quiz-card { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); }
            </style>
            """
        else:
            return """
            <style>
                .stMetric { background-color: #f5f5f5; border-radius: 10px; padding: 15px; }
                .stExpander { background-color: #fafafa; }
                .quiz-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            </style>
            """


class ResponsiveLayout:
    """Responsive layout components for mobile and desktop."""
    
    @staticmethod
    def quiz_card(subject: str, difficulty: str, score: float, timestamp: str):
        """Display a quiz result card."""
        color_map = {
            "easy": "#4CAF50",
            "medium": "#FF9800",
            "hard": "#F44336"
        }
        color = color_map.get(difficulty, "#2196F3")
        
        html_str = f"""
        <div style="background: white; border-left: 5px solid {color}; 
                   padding: 15px; border-radius: 8px; margin: 10px 0;
                   box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="font-size: 16px;">{subject}</strong>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;">
                        {difficulty.capitalize()} • {timestamp}
                    </div>
                </div>
                <div style="font-size: 24px; font-weight: bold; color: {color};">
                    {score:.1f}%
                </div>
            </div>
        </div>
        """
        st.markdown(html_str, unsafe_allow_html=True)
    
    @staticmethod
    def subject_button_grid(subjects: List[str], on_click_callbacks: Dict = None):
        """Display subjects as clickable cards in responsive grid."""
        subject_emojis = {
            "maths": "🔢",
            "english": "📚",
            "french": "🇫🇷",
            "science": "🔬",
            "finearts": "🎨"
        }
        
        cols = st.columns(5)
        for idx, subject in enumerate(subjects):
            with cols[idx % 5]:
                emoji = subject_emojis.get(subject.lower(), "📝")
                
                html_str = f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                           padding: 30px; border-radius: 15px; text-align: center;
                           color: white; cursor: pointer; transition: transform 0.2s;
                           box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                    <div style="font-size: 32px; margin-bottom: 10px;">{emoji}</div>
                    <div style="font-weight: bold; font-size: 14px;">{subject.capitalize()}</div>
                </div>
                """
                st.markdown(html_str, unsafe_allow_html=True)
                
                if st.button(f"Select {subject}", key=f"subject_{subject}", use_container_width=True):
                    if on_click_callbacks and subject in on_click_callbacks:
                        on_click_callbacks[subject]()
    
    @staticmethod
    def stat_card(title: str, value: str, icon: str, color: str = "#667eea"):
        """Display a statistic card."""
        html_str = f"""
        <div style="background: linear-gradient(135deg, {color} 0%, {color}dd 100%);
                   padding: 20px; border-radius: 12px; color: white;
                   box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div style="font-size: 12px; opacity: 0.9; text-transform: uppercase;">{title}</div>
                    <div style="font-size: 32px; font-weight: bold; margin-top: 10px;">{value}</div>
                </div>
                <div style="font-size: 40px; opacity: 0.8;">{icon}</div>
            </div>
        </div>
        """
        st.markdown(html_str, unsafe_allow_html=True)


class InteractiveComponents:
    """Interactive UI components for enhanced user experience."""
    
    @staticmethod
    def quiz_timer(total_seconds: int):
        """Display an animated quiz timer."""
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        
        # Color based on remaining time
        if total_seconds > 300:
            color = "#4CAF50"
        elif total_seconds > 60:
            color = "#FF9800"
        else:
            color = "#F44336"
        
        html_str = f"""
        <div style="background: linear-gradient(135deg, {color} 0%, {color}dd 100%);
                   padding: 15px; border-radius: 10px; color: white; text-align: center;
                   font-size: 32px; font-weight: bold; font-family: 'Courier New';">
            ⏱️ {minutes:02d}:{seconds:02d}
        </div>
        """
        st.markdown(html_str, unsafe_allow_html=True)
    
    @staticmethod
    def answer_button(question_num: int, option_text: str, option_idx: int, 
                     is_selected: bool = False, show_correct: bool = False,
                     is_correct: bool = False):
        """Display an interactive answer button."""
        background = "#4CAF50" if (show_correct and is_correct) else "#F44336" if (show_correct and not is_correct and is_selected) else "#667eea" if is_selected else "#f0f0f0"
        text_color = "white" if is_selected or show_correct else "#333"
        border = "3px solid #667eea" if is_selected else "1px solid #ddd"
        
        html_str = f"""
        <div style="background: {background}; border: {border}; padding: 15px; 
                   border-radius: 8px; text-align: left; cursor: pointer;
                   transition: all 0.2s; margin: 8px 0; color: {text_color};
                   font-weight: {'bold' if is_selected else 'normal'};">
            {option_text}
        </div>
        """
        st.markdown(html_str, unsafe_allow_html=True)
    
    @staticmethod
    def confetti_animation():
        """Display a confetti celebration animation."""
        html_str = """
        <div style="text-align: center; font-size: 60px; animation: bounce 0.5s ease-in-out;">
            🎉 🎊 🎉 🎊 🎉
        </div>
        <style>
            @keyframes bounce {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-20px); }
            }
        </style>
        """
        st.markdown(html_str, unsafe_allow_html=True)
    
    @staticmethod
    def notification(message: str, notification_type: str = "info"):
        """Display an animated notification."""
        icon_map = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        color_map = {
            "success": "#4CAF50",
            "error": "#F44336",
            "warning": "#FF9800",
            "info": "#2196F3"
        }
        
        icon = icon_map.get(notification_type, "ℹ️")
        color = color_map.get(notification_type, "#2196F3")
        
        html_str = f"""
        <div style="background: {color}20; border-left: 4px solid {color};
                   padding: 15px; border-radius: 8px; margin: 10px 0;
                   animation: slideIn 0.3s ease-out;">
            <div style="display: flex; align-items: center;">
                <div style="font-size: 24px; margin-right: 10px;">{icon}</div>
                <div style="color: #333; font-weight: 500;">{message}</div>
            </div>
        </div>
        <style>
            @keyframes slideIn {{
                from {{ transform: translateX(-100%); opacity: 0; }}
                to {{ transform: translateX(0); opacity: 1; }}
            }}
        </style>
        """
        st.markdown(html_str, unsafe_allow_html=True)

"""
Streamlit chatbot frontend with authentication.
Provides user-friendly IGCSE tutor interface for 15-18 year olds.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import requests
import uuid
from src.frontend.auth_pages import (
    show_login_page,
    is_authenticated,
    show_logout_button,
)
import src.config as config
from src.chat_service import ChatService
from src.database import get_session

# ===== Page Configuration =====
st.set_page_config(
    page_title="🤖 IGCSE Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== Initialize Session State =====
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "auth_token" not in st.session_state:
    st.session_state.auth_token = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "is_offline" not in st.session_state:
    st.session_state.is_offline = False
if "last_failed_query" not in st.session_state:
    st.session_state.last_failed_query = None
if "retry_count" not in st.session_state:
    st.session_state.retry_count = 0


# ===== Main Application =====
def main():
    """Main application entry point."""
    # Check authentication
    if not is_authenticated():
        show_login_page(config.fastapi_url)
        return

    # Authenticated - show chat interface
    show_chat_interface()


def show_chat_interface():
    """Display main chat interface for authenticated users."""
    api_url = config.fastapi_url
    api_key = config.openai_key

    # Page styling with gradient colors
    st.markdown(
        """
        <style>
        .main-title {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 15px;
            color: white;
            text-align: center;
            margin-bottom: 20px;
        }
        .menu-button {
            border-radius: 10px;
            padding: 15px;
            margin: 8px 0;
            font-weight: bold;
            border: none;
            cursor: pointer;
            transition: all 0.3s ease;
            width: 100%;
            text-align: left;
            font-size: 16px;
        }
        .menu-button-active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        .menu-button-inactive {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            color: #333;
        }
        .menu-button:hover {
            transform: translateX(5px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .sidebar-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .user-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            text-align: center;
        }
        .status-online {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            margin: 10px 0;
        }
        .status-offline {
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
            color: white;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            margin: 10px 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Title and sidebar
    st.markdown('<div class="main-title"><h1>🤖 IGCSE Tutor</h1><p>Your AI-powered study companion for IGCSE exams</p></div>', unsafe_allow_html=True)

    # Sidebar with colorful menu
    with st.sidebar:
        st.markdown('<div class="sidebar-header"><h2>📚 Navigation</h2></div>', unsafe_allow_html=True)

        # Get current page from session state
        current_page = st.session_state.get("page", "💬 Ask a Question")

        # Create menu buttons
        col1 = st.columns(1)[0]

        menu_items = [
            ("💬 Ask a Question", "💬 Ask a Question"),
            ("📝 Take a Quiz", "📝 Take a Quiz"),
            ("📊 Progress", "📊 Progress"),
            ("⚙️ Settings", "⚙️ Settings"),
        ]

        for icon_label, page_name in menu_items:
            is_active = current_page == page_name
            button_style = "menu-button menu-button-active" if is_active else "menu-button menu-button-inactive"

            if st.button(
                icon_label,
                key=f"menu_{page_name}",
                use_container_width=True,
                help=f"Go to {page_name}"
            ):
                st.session_state.page = page_name
                st.rerun()

        st.markdown("---")

        # New chat button with gradient
        if st.button("➕ New Chat", key="new_chat_btn", use_container_width=True):
            st.session_state.chat_session_id = str(uuid.uuid4())
            st.session_state.chat_history = []
            st.rerun()

        st.markdown("---")

        # Status indicator
        if st.session_state.is_offline:
            st.markdown('<div class="status-offline">🔴 <b>Offline Mode</b><br/>Limited functionality</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-online">🟢 <b>Online</b><br/>Full features available</div>', unsafe_allow_html=True)

        # User info and logout
        show_logout_button(api_url)

    # Main content based on selected page
    page = st.session_state.get("page", "💬 Ask a Question")

    if page == "💬 Ask a Question":
        show_ask_question_page(api_url)
    elif page == "📝 Take a Quiz":
        show_quiz_page(api_url)
    elif page == "📊 Progress":
        show_progress_page()
    elif page == "⚙️ Settings":
        show_settings_page()


def show_ask_question_page(api_url: str):
    """
    Display the ask question page.

    Args:
        api_url: FastAPI base URL
    """
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 25px; border-radius: 15px; margin-bottom: 20px;">
        <h2 style="color: white; margin: 0;">💬 Ask Your Question</h2>
        <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Ask anything about IGCSE subjects: English, Maths, Science, French, Fine Arts</p>
    </div>
    """, unsafe_allow_html=True)

    # Load chat history from database if not already loaded
    if not st.session_state.chat_history and st.session_state.user_id:
        try:
            db_session = get_session()
            messages = ChatService.get_session_history(
                db_session,
                st.session_state.user_id,
                st.session_state.chat_session_id
            )
            st.session_state.chat_history = [
                {"role": msg["role"], "type": "text", "content": msg["message"]}
                for msg in messages
            ]
            db_session.close()
        except Exception as e:
            st.warning(f"Could not load chat history: {str(e)}")

    # Display chat history
    if st.session_state.chat_history:
        st.markdown("### 📋 Chat History")
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                if message["type"] == "text":
                    st.markdown(message["content"])
                elif message["type"] == "table":
                    st.dataframe(message["content"])

    # Chat input
    user_input = st.chat_input(
        "Ask me any IGCSE question...",
        key="chat_input",
    )

    if user_input:
        # Display user message
        st.session_state.chat_history.append({
            "role": "user",
            "type": "text",
            "content": user_input,
        })

        # Save user message to database
        if st.session_state.user_id:
            try:
                db_session = get_session()
                ChatService.save_message(
                    db_session,
                    st.session_state.user_id,
                    st.session_state.chat_session_id,
                    "user",
                    user_input
                )
                db_session.close()
            except Exception as e:
                st.warning(f"Could not save message: {str(e)}")

        with st.chat_message("user"):
            st.markdown(user_input)

        # Query API
        token = st.session_state.get("auth_token")
        if not token:
            st.error("❌ Authentication error. Please log in again.")
            return

        headers = {"Authorization": f"Bearer {token}"}

        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    res = requests.post(
                        f"{api_url}/query",
                        json={"query": user_input},
                        headers=headers,
                        timeout=30,
                    )

                    if res.status_code == 200:
                        result = res.json()
                        response_content = result.get("data", "No response")
                        if result.get("type") == "text":
                            st.markdown(response_content)
                        elif result.get("type") == "table":
                            st.dataframe(response_content)

                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "type": result.get("type", "text"),
                            "content": response_content,
                        })

                        # Save assistant message to database
                        if st.session_state.user_id:
                            try:
                                db_session = get_session()
                                ChatService.save_message(
                                    db_session,
                                    st.session_state.user_id,
                                    st.session_state.chat_session_id,
                                    "assistant",
                                    str(response_content)
                                )
                                db_session.close()
                            except Exception as e:
                                st.warning(f"Could not save response: {str(e)}")

                    elif res.status_code == 401:
                        st.error("❌ Your session has expired. Please log in again.")
                    else:
                        st.error(f"❌ Error: {res.status_code}")
                        st.session_state.last_failed_query = user_input
                        if st.button("🔄 Retry", key="retry_query_btn"):
                            st.session_state.retry_count += 1
                            st.rerun()

                except requests.exceptions.Timeout:
                    st.error("❌ Request timeout. Please try again.")
                    st.session_state.last_failed_query = user_input
                    if st.button("🔄 Retry", key="retry_timeout_btn"):
                        st.session_state.retry_count += 1
                        st.rerun()
                except requests.exceptions.ConnectionError:
                    st.warning("⚠️ Could not connect to server. Offline mode not yet available.")
                    st.session_state.last_failed_query = user_input
                    if st.button("🔄 Retry", key="retry_connection_btn"):
                        st.session_state.retry_count += 1
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")
                    st.session_state.last_failed_query = user_input
                    if st.button("🔄 Retry", key="retry_general_btn"):
                        st.session_state.retry_count += 1
                        st.rerun()


def show_quiz_page(api_url: str):
    """Display the quiz interface."""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 25px; border-radius: 15px; margin-bottom: 20px;">
        <h2 style="color: white; margin: 0;">📝 Take a Quiz</h2>
        <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Test your knowledge with IGCSE practice quizzes</p>
    </div>
    """, unsafe_allow_html=True)

    # Initialize quiz session state
    if "current_quiz" not in st.session_state:
        st.session_state.current_quiz = None
    if "user_answers" not in st.session_state:
        st.session_state.user_answers = {}
    if "quiz_submitted" not in st.session_state:
        st.session_state.quiz_submitted = False

    # Quiz generation section
    col1, col2, col3 = st.columns(3)
    with col1:
        subject = st.selectbox(
            "📚 Subject",
            ["Maths", "English", "French", "Science", "FineArts"],
            key="quiz_subject"
        )
    with col2:
        difficulty = st.selectbox(
            "⭐ Difficulty",
            ["Easy", "Medium", "Hard"],
            key="quiz_difficulty"
        )
    with col3:
        question_count = st.selectbox(
            "❓ Questions",
            [3, 5, 10],
            key="quiz_questions",
            index=1  # Default to 5
        )

    token = st.session_state.get("auth_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # Generate quiz button
    if st.button("🚀 Generate Quiz", key="generate_quiz_btn"):
        with st.spinner("⏳ Generating quiz..."):
            try:
                response = requests.post(
                    f"{api_url}/quiz/generate",
                    json={
                        "subject": subject.lower(),
                        "difficulty": difficulty.lower(),
                        "question_count": question_count
                    },
                    headers=headers,
                    timeout=30
                )

                if response.status_code == 200:
                    st.session_state.current_quiz = response.json()
                    st.session_state.user_answers = {}
                    st.session_state.quiz_submitted = False
                    st.success("✅ Quiz generated!")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to generate quiz: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    # Display quiz
    if st.session_state.current_quiz and not st.session_state.quiz_submitted:
        st.markdown("---")
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 15px; border-radius: 10px; margin-bottom: 15px;">
            <h3 style="color: white; margin: 0;">📋 Quiz Questions</h3>
        </div>
        """, unsafe_allow_html=True)

        quiz_data = st.session_state.current_quiz
        questions = quiz_data.get("questions", [])

        for i, q_data in enumerate(questions):
            question_text = q_data.get("question", "")
            options = q_data.get("options", [])

            st.markdown(f"**Q{i+1}: {question_text}**")

            if options:
                st.session_state.user_answers[i] = st.radio(
                    f"Options for Q{i+1}",
                    options=options,
                    index=0 if i not in st.session_state.user_answers else options.index(st.session_state.user_answers.get(i, options[0])) if st.session_state.user_answers.get(i) in options else 0,
                    key=f"answer_{i}",
                    label_visibility="collapsed"
                )
            else:
                st.session_state.user_answers[i] = st.text_input(
                    f"Your answer for Q{i+1}",
                    value=st.session_state.user_answers.get(i, ""),
                    key=f"answer_{i}",
                    label_visibility="collapsed"
                )

        # Submit quiz button
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("✅ Submit Quiz", key="submit_quiz_btn"):
                with st.spinner("⏳ Submitting..."):
                    try:
                        # Convert user answers (option text) to indices
                        user_answers_indices = []
                        for i, q_data in enumerate(questions):
                            user_answer = st.session_state.user_answers.get(i, "")
                            options = q_data.get("options", [])
                            if user_answer in options:
                                user_answers_indices.append(options.index(user_answer))
                            else:
                                user_answers_indices.append(-1)  # Not answered

                        response = requests.post(
                            f"{api_url}/quiz/submit",
                            json={
                                "subject": quiz_data.get("subject", ""),
                                "difficulty": quiz_data.get("difficulty", ""),
                                "topic": quiz_data.get("topic", "IGCSE Practice"),
                                "questions": questions,
                                "user_answers": user_answers_indices
                            },
                            headers=headers,
                            timeout=30
                        )

                        if response.status_code == 200:
                            result = response.json()
                            st.session_state.quiz_result = result
                            st.session_state.quiz_submitted = True
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to submit quiz: {response.status_code}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

        with col2:
            if st.button("🔄 Clear Answers", key="clear_answers_btn"):
                st.session_state.user_answers = {}
                st.rerun()

    # Display results
    if st.session_state.quiz_submitted and st.session_state.current_quiz:
        st.markdown("---")
        st.markdown("""
        <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); padding: 15px; border-radius: 10px; margin-bottom: 15px;">
            <h3 style="color: white; margin: 0;">🎯 Quiz Results</h3>
        </div>
        """, unsafe_allow_html=True)

        result = st.session_state.get("quiz_result", {})
        correct_count = result.get("correct_count", 0)
        total_questions = result.get("total_questions", 1)
        percentage = result.get("percentage", 0)

        # Score display
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Your Score", f"{correct_count}/{total_questions}")
        with col2:
            st.metric("Percentage", f"{percentage:.1f}%")

        # Feedback
        if percentage >= 80:
            st.success("🎉 Excellent work! You've mastered this topic!")
        elif percentage >= 60:
            st.info("📈 Good effort! Keep practicing to improve.")
        else:
            st.warning("📚 Keep studying! Review the material and try again.")

        # Answer review
        st.markdown("### 📝 Answer Review")
        quiz_data = st.session_state.current_quiz
        questions = quiz_data.get("questions", [])
        subject = quiz_data.get("subject", "").lower()

        for i, q_data in enumerate(questions):
            question_text = q_data.get("question", "")
            options = q_data.get("options", [])
            correct_idx = q_data.get("correct_answer", 0)
            explanation = q_data.get("explanation", "")
            workings = q_data.get("workings", "")

            user_answer = st.session_state.user_answers.get(i, "No answer")
            correct_answer = options[correct_idx] if correct_idx < len(options) else "N/A"

            with st.expander(f"Q{i+1}: {question_text}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Your answer:** {user_answer}")
                with col2:
                    st.markdown(f"**Correct answer:** {correct_answer}")

                if explanation:
                    st.info(f"**Explanation:** {explanation}")

                # Show workings for Maths only
                if subject == "maths" and workings:
                    st.markdown("---")
                    st.markdown("**📐 Step-by-Step Solution:**")
                    st.code(workings, language="text")

        # Start new quiz button
        if st.button("🆕 Take Another Quiz", key="new_quiz_btn"):
            st.session_state.current_quiz = None
            st.session_state.user_answers = {}
            st.session_state.quiz_submitted = False
            st.rerun()


def show_progress_page():
    """Display user progress page."""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 25px; border-radius: 15px; margin-bottom: 20px;">
        <h2 style="color: white; margin: 0;">📊 Your Progress</h2>
        <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Track your learning journey and achievements</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("Coming soon! Track your learning journey here...")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Questions Asked", "0", "0")
    with col2:
        st.metric("Quizzes Taken", "0", "0")
    with col3:
        st.metric("Average Score", "0%", "0%")
    with col4:
        st.metric("Study Streak", "0 days", "0 days")


def show_settings_page():
    """Display settings page."""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 25px; border-radius: 15px; margin-bottom: 20px;">
        <h2 style="color: white; margin: 0;">⚙️ Settings</h2>
        <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Customize your learning experience</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🎨 Theme")
        theme = st.radio("Choose theme:", ["Light", "Dark", "Auto"])

    with col2:
        st.markdown("### 🎓 Subjects")
        subjects = st.multiselect(
            "Select your IGCSE subjects:",
            ["English", "Maths", "Science", "French", "Fine Arts"],
            default=["English", "Maths"],
        )

    st.markdown("---")
    st.markdown("### 📋 Account")
    if st.button("Change Password"):
        st.info("Password change feature coming soon!")


# ===== Entry Point =====
if __name__ == "__main__":
    main()

"""
Streamlit authentication pages (login and signup).
Provides user-friendly auth interface for 15-18 year olds.
"""

import streamlit as st
import requests
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def set_auth_session(token: str, user_data: dict) -> None:
    """
    Set authentication data in Streamlit session state.

    Args:
        token: Authentication token
        user_data: User information dictionary
    """
    st.session_state.authenticated = True
    st.session_state.auth_token = token
    st.session_state.user_id = user_data.get("id")
    st.session_state.username = user_data.get("username")
    st.session_state.email = user_data.get("email")
    st.session_state.full_name = user_data.get("full_name", "")
    st.session_state.role = user_data.get("role", "student")


def clear_auth_session() -> None:
    """Clear authentication data from Streamlit session state."""
    st.session_state.authenticated = False
    st.session_state.auth_token = None
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.email = None
    st.session_state.full_name = None
    st.session_state.role = None


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return st.session_state.get("authenticated", False)


def show_login_page(api_url: str) -> None:
    """
    Display login page with form.

    Args:
        api_url: FastAPI base URL
    """
    st.set_page_config(
        page_title="🔐 IGCSE Tutor Login",
        page_icon="🎓",
        layout="centered",
        initial_sidebar_state="collapsed",
    )

    # Custom styling for teenagers
    st.markdown(
        """
        <style>
        .login-container {
            max-width: 400px;
            margin: 0 auto;
        }
        .stButton > button {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: bold;
            border: none;
            padding: 12px;
            border-radius: 8px;
            font-size: 16px;
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("# 🎓 IGCSE Tutor")
        st.markdown("### Welcome Back!")
        st.markdown("---")

    # Tabs for login and signup
    tab1, tab2 = st.tabs(["📝 Login", "✍️ Sign Up"])

    with tab1:
        show_login_form(api_url)

    with tab2:
        show_signup_form(api_url)


def show_login_form(api_url: str) -> None:
    """
    Display login form.

    Args:
        api_url: FastAPI base URL
    """
    # Initialize login state if not exists
    if "login_in_progress" not in st.session_state:
        st.session_state.login_in_progress = False

    with st.form("login_form", clear_on_submit=True):
        username = st.text_input(
            "Username",
            placeholder="Enter your username",
            key="login_username",
            disabled=st.session_state.login_in_progress,
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            key="login_password",
            disabled=st.session_state.login_in_progress,
        )

        col1, col2 = st.columns(2)
        with col1:
            submit_button = st.form_submit_button(
                "🚀 Login",
                use_container_width=True,
                disabled=st.session_state.login_in_progress,
            )
        with col2:
            st.form_submit_button(
                "Reset",
                use_container_width=True,
                disabled=st.session_state.login_in_progress,
            )

        if submit_button:
            if not username or not password:
                st.error("❌ Please enter both username and password")
            else:
                st.session_state.login_in_progress = True
                with st.spinner("🔐 Logging in... Please wait"):
                    success, message, token, user_data = login_user(api_url, username, password)
                st.session_state.login_in_progress = False

                if success:
                    set_auth_session(token, user_data)
                    st.success(f"✅ Welcome back, {user_data.get('username')}!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"❌ {message}")


def show_signup_form(api_url: str) -> None:
    """
    Display signup form.

    Args:
        api_url: FastAPI base URL
    """
    # Initialize signup state if not exists
    if "signup_in_progress" not in st.session_state:
        st.session_state.signup_in_progress = False

    with st.form("signup_form", clear_on_submit=True):
        username = st.text_input(
            "Username",
            placeholder="Choose a username (3-50 chars, alphanumeric)",
            key="signup_username",
            disabled=st.session_state.signup_in_progress,
        )
        email = st.text_input(
            "Email",
            placeholder="Enter your email",
            key="signup_email",
            disabled=st.session_state.signup_in_progress,
        )
        full_name = st.text_input(
            "Full Name (Optional)",
            placeholder="Enter your full name",
            key="signup_fullname",
            disabled=st.session_state.signup_in_progress,
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="8+ chars with uppercase, lowercase, and numbers",
            key="signup_password",
            disabled=st.session_state.signup_in_progress,
        )
        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            placeholder="Re-enter your password",
            key="signup_confirm",
            disabled=st.session_state.signup_in_progress,
        )

        st.markdown(
            """
            **Password Requirements:**
            - At least 8 characters
            - At least one uppercase letter
            - At least one lowercase letter
            - At least one digit
            """
        )

        col1, col2 = st.columns(2)
        with col1:
            submit_button = st.form_submit_button(
                "✨ Create Account",
                use_container_width=True,
                disabled=st.session_state.signup_in_progress,
            )
        with col2:
            st.form_submit_button(
                "Reset",
                use_container_width=True,
                disabled=st.session_state.signup_in_progress,
            )

        if submit_button:
            # Validation
            if not username or not email or not password:
                st.error("❌ Please fill in all required fields")
            elif len(username) < 3 or len(username) > 50:
                st.error("❌ Username must be 3-50 characters")
            elif not username.isalnum():
                st.error("❌ Username must contain only letters and numbers")
            elif password != confirm_password:
                st.error("❌ Passwords do not match")
            elif len(password) < 8:
                st.error("❌ Password must be at least 8 characters")
            else:
                st.session_state.signup_in_progress = True
                with st.spinner("✨ Creating your account... Please wait"):
                    success, message = register_user(
                        api_url,
                        username=username,
                        email=email,
                        password=password,
                        full_name=full_name,
                    )
                st.session_state.signup_in_progress = False

                if success:
                    st.success("✅ Account created successfully! Please log in.")
                    st.info("Switch to the 'Login' tab to log in with your new credentials.")
                else:
                    st.error(f"❌ {message}")


def login_user(
    api_url: str,
    username: str,
    password: str,
) -> Tuple[bool, str, Optional[str], Optional[dict]]:
    """
    Call login API endpoint.

    Args:
        api_url: FastAPI base URL
        username: Username
        password: Password

    Returns:
        Tuple of (success: bool, message: str, token: Optional[str], user_data: Optional[dict])
    """
    try:
        response = requests.post(
            f"{api_url}/auth/login",
            json={"username": username, "password": password},
            timeout=5,
        )

        if response.status_code == 200:
            data = response.json()
            return True, data.get("message", "Login successful"), data["token"], data["user"]

        error_detail = response.json().get("detail", "Login failed")
        return False, error_detail, None, None

    except requests.exceptions.Timeout:
        return False, "Request timeout. Please try again.", None, None
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to server. Please check your connection.", None, None
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return False, "An unexpected error occurred. Please try again.", None, None


def register_user(
    api_url: str,
    username: str,
    email: str,
    password: str,
    full_name: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Call registration API endpoint.

    Args:
        api_url: FastAPI base URL
        username: Username
        email: Email address
        password: Password
        full_name: Full name (optional)

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        payload = {
            "username": username,
            "email": email,
            "password": password,
        }
        if full_name:
            payload["full_name"] = full_name

        response = requests.post(
            f"{api_url}/auth/register",
            json=payload,
            timeout=5,
        )

        if response.status_code == 201:
            data = response.json()
            return True, data.get("message", "Registration successful")

        error_detail = response.json().get("detail", "Registration failed")
        return False, error_detail

    except requests.exceptions.Timeout:
        return False, "Request timeout. Please try again."
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to server. Please check your connection."
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return False, "An unexpected error occurred. Please try again."


def show_logout_button(api_url: str) -> None:
    """
    Display logout button in sidebar.

    Args:
        api_url: FastAPI base URL
    """
    with st.sidebar:
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**👤 {st.session_state.username}**")
            st.caption(st.session_state.get("role", "student").title())

        with col2:
            if st.button("🚪 Logout", use_container_width=True):
                logout_user(api_url)
                clear_auth_session()
                st.rerun()


def logout_user(api_url: str) -> bool:
    """
    Call logout API endpoint.

    Args:
        api_url: FastAPI base URL

    Returns:
        True if logout successful, False otherwise
    """
    try:
        token = st.session_state.get("auth_token")
        if not token:
            return False

        response = requests.post(
            f"{api_url}/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )

        return response.status_code == 200

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return False

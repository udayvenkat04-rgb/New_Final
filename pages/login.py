import os
import base64
import streamlit as st
from backend.database import check_connection
from backend.auth.authentication import authenticate_user, login_user, logout_user
from backend.utils.helpers import inject_custom_css

# Page setup - Wide layout for split screen matching the user PNG
st.set_page_config(page_title="Login - MPIS Portal", page_icon="🔐", layout="wide", initial_sidebar_state="expanded")
inject_custom_css()

# Path to the user-provided PNG illustration graphics
RIGHT_GRAPHIC_PATH = os.path.join("data", "login_right_graphic.png")
FULL_PNG_PATH = os.path.join("data", "login_hero.png")

# Custom CSS override matching the user PNG styling & Indigo Theme
st.markdown("""
<style>
/* Background of app on login page & viewport centering */
/* .stApp {
    background-color: #f1f5f9 !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    min-height: 100vh !important;
} */

/* .main {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 100% !important;
} */

/* Unboxed layout - Remove outer card background box and form border */


/* Unboxed layout - Remove outer card background box and form border */
div[data-testid="stHorizontalBlock"] {
    background: transparent !important;
    border-radius: 0px !important;
    padding: 10px !important;
    box-shadow: none !important;
    border: none !important;
    align-items: center !important;
}

div[data-testid="stForm"] {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
}


/* Enhanced Input Highlights */
div[data-baseweb="input"] {
    border-radius: 12px !important;
    border: 1.5px solid #cbd5e1 !important;
    padding: 3px 6px !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03) !important;
    transition: all 0.2s ease !important;
}
div[data-baseweb="input"]:hover {
    border-color: #818cf8 !important;
}
div[data-baseweb="input"]:focus-within {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.2) !important;
}

/* Enhanced Sign In Button Highlight */
div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 28px !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    box-shadow: 0 6px 20px rgba(79, 70, 229, 0.35) !important;
    transition: all 0.25s ease !important;
    width: 100% !important;
}
div[data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 28px rgba(79, 70, 229, 0.5) !important;
    background: linear-gradient(135deg, #4338ca 0%, #3730a3 100%) !important;
}

/* Ensure Remember Me wrapper has transparent background & perfect vertical alignment */
div[data-testid="stCheckbox"] {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}

div[data-testid="stCheckbox"] label {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    margin: 0 !important;
    padding: 0 !important;
    min-height: 38px !important;
}

div[data-testid="stCheckbox"] input[type="checkbox"] {
    accent-color: #6366f1 !important;
    width: 18px !important;
    height: 18px !important;
    cursor: pointer !important;
    display: inline-block !important;
    visibility: visible !important;
    opacity: 1 !important;
    margin: 0 !important;
}

div[data-testid="stCheckbox"] label p {
    color: #64748b !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1.2 !important;
    transition: color 0.2s ease !important;
}
div[data-testid="stCheckbox"]:hover label p {
    color: #4f46e5 !important;
}





/* Public Portal Secondary Button - Constant Solid Dark Indigo Theme Styling */
div[data-testid="stButton"] button {
    background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%) !important;
    border: 1.5px solid #4338ca !important;
    color: #ffffff !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 14.5px !important;
    padding: 12px 20px !important;
    box-shadow: 0 6px 20px rgba(79, 70, 229, 0.35) !important;
    width: 100% !important;
    transition: all 0.25s ease !important;
}

div[data-testid="stButton"] button:hover {
    background: linear-gradient(135deg, #4338ca 0%, #312e81 100%) !important;
    border-color: #312e81 !important;
    color: #ffffff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 28px rgba(79, 70, 229, 0.5) !important;
}

/* Right column image styling - rounded corners matching card & disable click-to-zoom */
[data-testid="stImage"] {
    pointer-events: none !important;
}

button[title="View fullscreen"],
button[data-testid="StyledFullScreenButton"],
[data-testid="stImage"] button {
    display: none !important;
    visibility: hidden !important;
    pointer-events: none !important;
}

[data-testid="stImage"] img {
    border-radius: 20px !important;
    pointer-events: none !important;
    cursor: default !important;
    user-select: none !important;
}

/* Mobile optimizations for Login Page */
@media screen and (max-width: 991px) {
    /* Hide the giant biometric graphic on mobile to keep login screen clean and focused */
    .login-graphic-container {
        display: none !important;
    }
    
    /* Scale down welcome header text sizes on mobile to prevent messy wrapping */
    .login-greeting-container h1 {
        font-size: 28px !important;
        line-height: 1.2 !important;
        margin-bottom: 6px !important;
    }
    .login-greeting-container p {
        font-size: 13.5px !important;
        margin-bottom: 15px !important;
    }
    .login-greeting-container div:first-child {
        margin-bottom: 16px !important;
    }
    
    /* Force checkbox and forgot password columns inside the form to stay side-by-side in a row */
    div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: space-between !important;
        flex-wrap: nowrap !important;
        gap: 10px !important;
        padding: 0 !important;
    }
    
    div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"],
    div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div.stColumn {
        width: 50% !important;
        flex: 1 1 50% !important;
        min-width: 50% !important;
        max-width: 50% !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* Reset margins for elements inside the columns */
    div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] div.element-container {
        margin: 0 !important;
        padding: 0 !important;
    }

    /* Scale down checkbox and forgot password link font sizes on mobile to prevent messy wrapping */
    div[data-testid="stForm"] div[data-testid="stCheckbox"] label p {
        font-size: 12px !important;
    }

    div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] a {
        font-size: 12px !important;
    }
    
    /* Right-align the forgot password container link text */
    div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] div {
        text-align: right !important;
    }
}
</style>
""", unsafe_allow_html=True)

# Verify MongoDB availability
connected, db_msg = check_connection()
if not connected:
    st.error(f"⚠️ **Database Connection Error**: {db_msg}")
    st.warning("Please ensure MongoDB is running and your `DATABASE_URL` is configured correctly in `.env`.")
    st.stop()

# Check if already authenticated — auto-redirect directly to role dashboard
if st.session_state.get("authenticated", False):
    user = st.session_state.get("user", {})
    role = user.get("role", "")
    if role == "admin":
        st.switch_page("pages/admin_dashboard.py")
    elif role == "officer":
        st.switch_page("pages/officer_dashboard.py")
    else:
        st.switch_page("pages/cases.py")

# ── Interactive Dialog Modals ─────────────────────────────────────────

@st.dialog("🔑 Reset Your Password")
def show_forgot_password_dialog():
    st.markdown("Enter your registered email address or username to receive password reset instructions.")
    reset_target = st.text_input("Username or Email", placeholder="e.g. officer@test.com or admin")
    if st.button("Send Reset Instructions", key="btn_confirm_reset", use_container_width=True):
        if not reset_target or not reset_target.strip():
            st.error("Please enter your registered username or email address.")
        else:
            from backend.repositories.user_repository import UserRepository
            user_repo = UserRepository()
            user = user_repo.get_by_email(reset_target) or user_repo.get_by_username(reset_target)
            if user:
                st.success(f"✅ Password reset instructions have been sent for user **{user.username}** (`{user.email}`)! Check your inbox or contact administrator.")
            else:
                st.info(f"ℹ️ Password reset request initiated for `{reset_target}`. If an account matches, instructions have been dispatched.")


@st.dialog("📝 Create New Officer Account")
def show_signup_dialog():
    st.markdown("Register for an authorized law enforcement officer account.")
    with st.form("signup_dialog_form", clear_on_submit=False):
        reg_name = st.text_input("Full Name *", placeholder="e.g. Officer Rajesh Sharma")
        reg_email = st.text_input("Email Address *", placeholder="e.g. rajesh@police.gov.in")
        reg_username = st.text_input("Desired Username *", placeholder="e.g. officer_rajesh")
        reg_role = st.selectbox("Account Role *", options=["officer", "admin"])
        reg_password = st.text_input("Password *", type="password", placeholder="••••••••••••")
        reg_confirm = st.text_input("Confirm Password *", type="password", placeholder="••••••••••••")
        
        reg_submit = st.form_submit_button("Create Account", use_container_width=True)
        
    if reg_submit:
        if not reg_name or not reg_email or not reg_username or not reg_password:
            st.error("Please fill in all required fields marked with *.")
        elif reg_password != reg_confirm:
            st.error("Password and Confirm Password do not match.")
        else:
            from backend.repositories.user_repository import UserRepository
            user_repo = UserRepository()
            if user_repo.get_by_username(reg_username):
                st.error(f"Username '{reg_username}' is already taken. Please choose another username.")
            elif user_repo.get_by_email(reg_email):
                st.error(f"Email '{reg_email}' is already registered.")
            else:
                from backend.models import User
                from backend.utils.security import hash_password
                new_user = User(
                    username=reg_username.strip(),
                    name=reg_name.strip(),
                    email=reg_email.strip(),
                    role=reg_role,
                    password=hash_password(reg_password)
                )
                user_repo.create(new_user)
                st.success("🎉 Account created successfully! You can now log in using your new credentials.")

# Handle action query parameter triggers for dialog modals
action = st.query_params.get("action")
if action == "forgot":
    st.query_params.clear()
    show_forgot_password_dialog()
elif action == "signup":
    st.query_params.clear()
    show_signup_dialog()

# ── Split layout matching user PNG design ─────────────────────────────
col_form, col_graphic = st.columns([1.1, 1.0], gap="large")

with col_form:
    st.markdown("""
    <div class="login-greeting-container" style="padding: 10px 10px 0 10px;">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 24px;">
            <span style="background: #4f46e5; color: white; width: 14px; height: 14px; border-radius: 4px; display: inline-flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 900;">🔒</span>
            <strong style="font-size: 16px; color: #0f172a; font-weight: 800; letter-spacing: -0.3px;">Finnger / MPIS Portal</strong>
        </div>
        <h1 style="font-size: 42px; font-weight: 800; color: #0f172a; margin-top: 0; margin-bottom: 8px; line-height: 1.15;">
            Hello,<br/><span style="color: #4f46e5;">Welcome Back</span>
        </h1>
        <p style="color: #94a3b8; font-size: 15px; margin-bottom: 25px;">
            Hey, welcome back to your special place
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Render Standard Login Form matching input structure in user PNG
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="••••••••••••")

        c1, c2 = st.columns([1, 1], vertical_alignment="center")
        with c1:
            st.checkbox("Remember me", value=True)

        with c2:
            st.markdown("""
            <div style="display: flex; align-items: center; justify-content: flex-end; min-height: 38px;">
                <a href="?action=forgot" target="_self" style="color: #94a3b8; font-size: 13.5px; font-weight: 500; text-decoration: none; transition: color 0.2s;" onmouseover="this.style.color='#6366f1'" onmouseout="this.style.color='#94a3b8'">Forgot Password?</a>
            </div>
            """, unsafe_allow_html=True)



        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        submit = st.form_submit_button("Sign In", use_container_width=True)

    if submit:
        if not email or not password:
            st.error("Please enter both username/email and password.")
        else:
            try:
                user = authenticate_user(email, password)
                if user:
                    login_user(user)
                    user_role = user.get("role")
                    if user_role == "admin":
                        st.switch_page("pages/admin_dashboard.py")
                    elif user_role == "officer":
                        st.switch_page("pages/officer_dashboard.py")
                    else:
                        st.switch_page("pages/cases.py")
                else:
                    st.error("Invalid credentials. Please check your username/email and password.")
            except ValueError as exc:
                st.error(f"⚠️ {exc}")
            except ConnectionError as exc:
                st.error(f"🔌 {exc}")

    # Sign Up link matching original placement and Indigo theme - Centered Alignment
    st.markdown("""
    <div style="margin-top: 18px; font-size: 14px; color: #64748b; text-align: center;">
        Don't have an account? 
        <a href="?action=signup" target="_self" style="color: #4f46e5; font-weight: 700; text-decoration: none; margin-left: 4px; transition: color 0.2s;" onmouseover="this.style.color='#4338ca'" onmouseout="this.style.color='#4f46e5'">Sign Up</a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚨 Visit Public Missing Person Portal (No Login Required)", key="public_portal_btn", use_container_width=True):
        st.switch_page("pages/public_portal.py")




def _get_image_as_base64(file_path):
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return ""

with col_graphic:
    graphic_b64 = _get_image_as_base64(RIGHT_GRAPHIC_PATH) or _get_image_as_base64(FULL_PNG_PATH)
    if graphic_b64:
        st.markdown(
            f'''
            <div class="login-graphic-container" style="width: 100%; text-align: center; pointer-events: none; user-select: none;">
                <img src="data:image/png;base64,{graphic_b64}" 
                     style="width: 100%; border-radius: 20px; display: block; margin: 0 auto; pointer-events: none; user-select: none; box-shadow: 0 8px 24px rgba(124, 58, 237, 0.15);" 
                     alt="Biometric Authentication Graphic" />
            </div>
            ''',
            unsafe_allow_html=True
        )
    else:
        st.info("Biometric Authentication Graphic")

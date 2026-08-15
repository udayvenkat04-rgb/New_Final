import streamlit as st
from backend.database import check_connection
from backend.auth.authentication import authenticate_user, login_user, logout_user
from backend.utils.helpers import inject_custom_css

# Page setup
st.set_page_config(page_title="Login - Portal", page_icon="🔐", layout="centered")
inject_custom_css()

# Verify MongoDB availability
connected, db_msg = check_connection()
if not connected:
    st.error(f"⚠️ **Database Connection Error**: {db_msg}")
    st.warning("Please ensure MongoDB is running and your `DATABASE_URL` is configured correctly in `.env`.")
    st.stop()

st.markdown("<h2 style='text-align: center; color: #10b981;'>🔐 Officer & Admin Login</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8;'>Enter your credentials to access secure management dashboards.</p>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# Check if already authenticated
if st.session_state.get("authenticated", False):
    user = st.session_state.get("user", {})
    role = user.get("role", "")
    st.success(f"You are currently logged in as: **{user.get('username')}** ({role.upper()})")

    col1, col2 = st.columns(2)
    with col1:
        if role == "admin":
            if st.button("👑 Open Admin Dashboard", use_container_width=True):
                st.switch_page("pages/admin_dashboard.py")
        else:
            if st.button("🛡️ Open Officer Dashboard", use_container_width=True):
                st.switch_page("pages/officer_dashboard.py")
    with col2:
        if st.button("🚪 Log Out", key="logout_btn", use_container_width=True):
            logout_user()
else:
    # Render Login Form
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Username / Email", placeholder="e.g. admin or officer")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submit = st.form_submit_button("Sign In", use_container_width=True)

    if submit:
        if not email or not password:
            st.error("Please enter both username/email and password.")
        else:
            try:
                user = authenticate_user(email, password)
                if user:
                    login_user(user)
                    st.toast(f"🎉 Login Successful! Welcome, {user.get('username') or user.get('name')}!", icon="🔐")
                    st.success(f"Welcome back, {user.get('username') or user.get('name')}! Redirecting to your dashboard...")
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

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    if st.button("🚨 Visit Public Missing Person Portal (No Login Required)", key="public_portal_btn", use_container_width=True):
        st.switch_page("pages/public_portal.py")
    st.markdown("</div>", unsafe_allow_html=True)

    st.caption("ℹ️ Demo Credentials: Admin (`admin` / `admin123`) | Officer (`officer` / `officer123`)")

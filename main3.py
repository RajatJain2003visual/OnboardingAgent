import streamlit as st
from download_attachments_agent import download_agent
from pydantic import EmailStr, ValidationError, TypeAdapter
from dotenv import load_dotenv
import os
from Processing_documents import extract_details
from Validate_details_agent import validate_agent
import shutil
from generate_and_send_mail import generate_mail_with_reason, send_mail_agent
import base64
import mimetypes
import time
import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import download_attachments_agent
import generate_and_send_mail
from google.oauth2 import id_token
from google.auth.transport import requests
import ast
import streamlit.components.v1 as components



# --- 1. SETUP & INIT ---
if "old_attachments_cleared" not in st.session_state:
    folder_path = "attachments"
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        print("Folder deleted successfully")
    st.session_state.old_attachments_cleared = True


load_dotenv(override=True)

# if "old_session_cleared" not in st.session_state:
#     if "EMAIL_USERNAME" in os.environ:
#         os.environ.__delitem__('EMAIL_USERNAME') 
#     if "EMAIL_PASSWORD" in os.environ:
#         os.environ.__delitem__('EMAIL_PASSWORD')
#     st.session_state.old_session_cleared = True 


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# --- 4. SIDEBAR & CREDENTIALS ---
st.title("Span Onboarding")

if "credentials" not in st.session_state:

    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        scopes=SCOPES,
        redirect_uri="http://localhost:8501"
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )

    st.header(f"Welcome to SpanOnboarding")
    st.markdown(f"### 🔐 Please login with your google account to continue using SpanOnboarding...")
    st.link_button("🔐 Login with Google", auth_url, type="primary", use_container_width=True)

    if "code" in st.query_params:
        flow.fetch_token(code=st.query_params["code"])
        st.session_state.credentials = flow.credentials
        st.rerun()

else:
    if "service" not in st.session_state:
        with st.spinner("Please wait while we log you in..."):
            credentials = st.session_state.credentials
            service = build("gmail", "v1", credentials=credentials)
            st.session_state.service = service
            # download_attachments_agent.GMAIL_SERVICE = st.session_state.service
            # generate_and_send_mail.GMAIL_SERVICE = st.session_state.service
            # ---- Extract Google profile info ----
            userinfo = id_token.verify_oauth2_token(
                credentials.id_token,
                requests.Request(),
                audience=credentials.client_id
            )

            st.session_state.user_name = userinfo.get("name")
            st.session_state.user_email = userinfo.get("email")
            st.session_state.user_photo = userinfo.get("picture")

            st.success("Logged in successfully!")

if "service" in st.session_state:
    download_attachments_agent.GMAIL_SERVICE = st.session_state.service
    generate_and_send_mail.GMAIL_SERVICE = st.session_state.service

# Initialize Session State Variables
for key in ["download_done", "processing_done", "validated", "c_name"]:
    if key not in st.session_state:
        st.session_state[key] = False if key != "c_name" else ""

# --- 2. HELPER FUNCTIONS ---
def is_valid_email(email: str) -> bool:
    email_adapter = TypeAdapter(EmailStr)
    try:
        email_adapter.validate_python(email)
        return True
    except ValidationError:
        return False


def style_button_by_text(button_text, height="auto", width="auto", color=None, background_color=None):
    """
    Targets a Streamlit button containing specific text and styles it.
    """
    js_code = f"""
    <script>
        // Use a mutation observer to ensure we catch the button even if it renders late
        const observer = new MutationObserver((mutations) => {{
            const buttons = window.parent.document.querySelectorAll('button');
            buttons.forEach(btn => {{
                if (btn.innerText.includes('{button_text}')) {{
                    btn.style.height = '{height}';
                    btn.style.width = '{width}';
                    
                    // Center content logic (Flexbox is default, ensuring it sticks)
                    btn.style.display = 'flex';
                    btn.style.justifyContent = 'center';
                    btn.style.alignItems = 'center';
                    
                    // Optional overrides
                    if ('{color}' !== 'None') btn.style.color = '{color}';
                    if ('{background_color}' !== 'None') {{
                        btn.style.backgroundColor = '{background_color}';
                        btn.style.borderColor = '{background_color}';
                    }}
                }}
            }});
        }});
        
        observer.observe(window.parent.document.body, {{ childList: true, subtree: true }});
    </script>
    """
    # Inject the JS. height=0 ensures this component itself is invisible.
    components.html(js_code, height=0)


# def save_to_env(key: str, value: str, env_path: str = ".env"):
#     lines = []
#     if os.path.exists(env_path):
#         with open(env_path, "r") as f:
#             lines = [line for line in f.readlines() if not line.startswith(f"{key}=")]
#     with open(env_path, "w") as f:
#         for line in lines:
#             f.write(line)
#         f.write(f"{key}={value}\n")

# --- 3. OVERLAY LOGIC ---
@st.dialog("Attachment Preview", width="large")
def show_attachment_overlay(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    
    if mime_type == "application/pdf":
        with open(file_path, "rb") as f:
            base64_data = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_data}" width="100%" height="800" style="border:none;"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    elif mime_type and mime_type.startswith("image"):
        st.image(file_path, use_container_width=True)
    else:
        st.error("Unsupported file format for preview.")

# # --- 4. SIDEBAR & CREDENTIALS ---
# st.title("Span Onboarding")

# with st.sidebar:
#     st.title("Credentials")
#     from_mail = st.text_input("From Email")
#     app_password = st.text_input("App Password", type="password")
#     if is_valid_email(from_mail):
#         save_to_env("EMAIL_USERNAME", from_mail)
#         # st.secrets("EMAIL_USERNAME") = from_mail
#         # st.session_state.EMAIL_USERNAME = from_mail
#     length = [c for c in app_password if str.isalpha(c)]
#     if len(len) == 16:
#         save_to_env("EMAIL_PASSWORD", app_password)
        # st.secrets("EMAIL_PASSWORD") = app_password
        # st.session_state.EMAIL_PASSWORD = app_password



# --- 5. MAIN INPUT & DOWNLOAD ---
# st.header("Enter Candidate Email")
# if "EMAIL_USERNAME" not in os.environ or "EMAIL_PASSWORD" not in os.environ:
    # st.warning("Please enter Email and App password in sidebar")
# if "EMAIL_USERNAME" not in st.session_state or "EMAIL_PASSWORD" not in st.session_state:
#     st.warning("Please enter Email and App password in sidebar")


if "service" in st.session_state:

    with st.sidebar:
        # user_col1, user_col2 = st.columns([4,2])

        # with user_col1:
        #     st.title(f"Welcome {st.session_state.user_name}")
        # with user_col2:
        #     st.image(st.session_state.user_photo)

        col1, col2, col3 = st.columns([1, 2, 1])  # Adjust the middle number to make the image larger/smaller

        with col2:
            st.image(st.session_state.user_photo)
        # st.image(st.session_state.user_photo, )
        st.title(f"Welcome {st.session_state.user_name}")

    st.header("Enter Candidate Email")
    to_mail = st.text_input("", placeholder="candidate@example.com")

    # Only the DOWNLOAD BUTTON depends on the email input validity
    if is_valid_email(to_mail):

        download_attachments = st.button("Download Attachments", key="da", type="primary")

        if download_attachments:
            # style_button_by_text(
            #     button_text="Send Mail to",  # Partial match works too
            #     height="100px",            # Taller than default
            #     width="100%",             # Full width
            #     background_color="#4CAF50" # Custom Green
            # )
            with st.spinner("⬇️ Downloading attachments..."):
                response = download_agent(to_mail)
            if response:
                st.session_state.download_done = True
                st.success("🥳 Attachments downloaded")
                time.sleep(5)
                st.rerun()

# --- 6. DOCUMENT PROCESSING DASHBOARD ---
# CRITICAL FIX: This is now UN-INDENTED. It runs as long as download is done.
if st.session_state.download_done:
    
    st.session_state.to_mail = to_mail

    # A. Sidebar Files
    with st.sidebar:
        st.subheader("Downloaded Attachments")
        if os.path.exists('attachments'):
            for docs in os.listdir('attachments'):
                mime_type, _ = mimetypes.guess_type(docs)
                if mime_type and (mime_type.startswith("image/") or mime_type == "application/pdf"):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.caption(docs)
                    with col2:
                        if st.button("👁️", key=f"btn_{docs}"):
                            show_attachment_overlay(os.path.join('attachments', docs))
    
    # B. Process Button
    process_button = st.button("🔎 Start Processing Documents", type="secondary")
    if process_button:
        with st.spinner("Processing documents..."):
            st.session_state.data, st.session_state.raw_data = extract_details()
            st.session_state.processing_done = True
            st.rerun()

    # C. Validation Logic (First Run)
    if st.session_state.processing_done and not st.session_state.validated:
        with st.spinner("Validating details..."):
            st.session_state.discrepancy = validate_agent(st.session_state.raw_data)
            # Unpack to get Name
            _, _, _, _, _, _, df_identity_docs = st.session_state.data
            if not df_identity_docs.empty:
                st.session_state.c_name = df_identity_docs["name"].iloc[0]
            
            st.session_state.validated = True
            st.session_state.processing_done = False
            st.rerun()

    # D. Display & Edit Data
    if "data" in st.session_state:
        checklist_df, df_academics, df_college, df_jobs, df_salary_slips, df_bank_credits, df_identity_docs = st.session_state.data
        
        st.subheader("📋 Document Checklist")
        checklist_df = st.data_editor(checklist_df, key="edit_check")
        
        st.subheader("🏫 Academics Details")
        df_academics = st.data_editor(df_academics, key="edit_acad")
        
        st.subheader("🎓 College Details")
        df_college = st.data_editor(df_college, key="edit_college")
        
        st.subheader("🏢 Company Details")
        df_jobs = st.data_editor(df_jobs, key="edit_jobs")
        
        st.subheader("🤑 Salary Details")
        df_salary_slips = st.data_editor(df_salary_slips, key="edit_salary_slips")
        
        st.subheader("💰 Bank Details")
        df_bank_credits = st.data_editor(df_bank_credits, key="edit_bank_credits")
        
        st.subheader("🙎 Identity Details")
        df_identity_docs = st.data_editor(df_identity_docs, key="edit_identity_docs")

        # Update Session State with Edits
        st.session_state.data = (checklist_df, df_academics, df_college, df_jobs, df_salary_slips, df_bank_credits, df_identity_docs)
        
        # Re-Validate Button
        if st.button("Save edited & Revalidate 🔄"):
            with st.spinner("Re-checking rules..."):
                # st.session_state.discrepancy = validate_agent(st.session_state.raw_data)
                st.session_state.discrepancy = validate_agent(st.session_state.data)
                # st.markdown(st.session_state.dicrepancy)
                # st.success("Data updated and re-validated!")
                st.rerun()

    # E. Discrepancy Report
    if "discrepancy" in st.session_state:
        st.subheader("Discrepancy Report")
        with st.container(border=True):
            # st.markdown(st.session_state.discrepancy)
            discrepancy, sentiment = ast.literal_eval(st.session_state.discrepancy) 
            if sentiment == 'positive':
                st.success(discrepancy)
            else:
                st.error(discrepancy)
        # if st.session_state.discrepancy == "No discrepancies found":
            #  st.success("No discrepancies found")
        # else:
            #  st.error(st.session_state.discrepancy)

    # F. Email Generation
    if st.session_state.validated:
        st.divider()
        # col1, col2 = st.columns(2)
        
        # with col1:
        if st.button(f"✉️ Generate Mail for {to_mail}", type="primary",use_container_width=True):
            with st.spinner("Generating mail..."):
                mail_reason = f"Output from discrepancy check agent: {st.session_state.discrepancy}"
                st.session_state.mail_content = generate_mail_with_reason(mail_reason, st.session_state.c_name, "Spanidea")
                style_button_by_text(
                    button_text="Send Mail to",  # Partial match works too
                    # height="100px",            # Taller than default
                    width="100%",             # Full width
                    background_color="#4CAF50" # Custom Green
                )
            st.rerun()
    
        # Only show the rest if mail content exists
        if "mail_content" in st.session_state:
            edited_mail = st.text_area(
                "Review & Edit Email",
                value=st.session_state.mail_content,
                key="mail_content_area", # Changed key to avoid conflict with variable
                height=300
            )
            # Update the state if user manually edits the text area
            st.session_state.mail_content = edited_mail

            # with col2:
                # Spacer
                # st.write("")
                # st.write("")
                # space = '\u00A0'*10
                # space2 = '\u00A0'*40
            st.session_state.smb = st.button(f"""📤 Send Mail to {st.session_state.c_name}""", type="primary",use_container_width=True)
            if st.session_state.smb:
                with st.spinner("Sending mail..."):
                    send_status = send_mail_agent(st.session_state.mail_content, to_mail=st.session_state.to_mail)
                    if send_status:
                        st.success("Mail sent successfully!")
                    else:
                        st.error("Failed to send mail.")


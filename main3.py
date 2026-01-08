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

# --- 1. SETUP & INIT ---
if "old_attachments_cleared" not in st.session_state:
    folder_path = "attachments"
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        print("Folder deleted successfully")
    st.session_state.old_attachments_cleared = True


load_dotenv(override=True)

if "old_session_cleared" not in st.session_state:
    if "EMAIL_USERNAME" in os.environ:
        os.environ.__delitem__('EMAIL_USERNAME') 
    if "EMAIL_PASSWORD" in os.environ:
        os.environ.__delitem__('EMAIL_PASSWORD')
    st.session_state.old_session_cleared = True 

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

def save_to_env(key: str, value: str, env_path: str = ".env"):
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = [line for line in f.readlines() if not line.startswith(f"{key}=")]
    with open(env_path, "w") as f:
        for line in lines:
            f.write(line)
        f.write(f"{key}={value}\n")

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

# --- 4. SIDEBAR & CREDENTIALS ---
st.title("Span Onboarding")

with st.sidebar:
    st.title("Credentials")
    from_mail = st.text_input("From Email")
    app_password = st.text_input("App Password", type="password")
    if is_valid_email(from_mail):
        # save_to_env("EMAIL_USERNAME", from_mail)
        # st.secrets("EMAIL_USERNAME") = from_mail
        st.session_state.EMAIL_USERNAME = from_mail
    if len(app_password) == 16:
        # save_to_env("EMAIL_PASSWORD", app_password)
        # st.secrets("EMAIL_PASSWORD") = app_password
        st.session_state.EMAIL_PASSWORD = app_password



# --- 5. MAIN INPUT & DOWNLOAD ---
st.header("Enter Candidate Email")
# if "EMAIL_USERNAME" not in os.environ or "EMAIL_PASSWORD" not in os.environ:
    # st.warning("Please enter Email and App password in sidebar")
if "EMAIL_USERNAME" not in st.session_state or "EMAIL_PASSWORD" not in st.session_state:
    st.warning("Please enter Email and App password in sidebar")
else:
    to_mail = st.text_input("", placeholder="candidate@example.com")

    # Only the DOWNLOAD BUTTON depends on the email input validity
    if is_valid_email(to_mail):

        download_attachments = st.button("Download Attachments", key="da", type="primary")

        if download_attachments:
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
            st.session_state.data = extract_details()
            st.session_state.processing_done = True
            st.rerun()

    # C. Validation Logic (First Run)
    if st.session_state.processing_done and not st.session_state.validated:
        with st.spinner("Validating details..."):
            st.session_state.discrepancy = validate_agent(st.session_state.data)
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
                st.session_state.discrepancy = validate_agent(st.session_state.data)
                st.success("Data updated and re-validated!")
                st.rerun()

    # E. Discrepancy Report
    if "discrepancy" in st.session_state:
        st.subheader("Discrepancy Report")
        if st.session_state.discrepancy == "No discrepancies found":
             st.success("No discrepancies found")
        else:
             st.error(st.session_state.discrepancy)

    # F. Email Generation
    if st.session_state.validated:
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(f"✉️ Generate Mail for {to_mail}", type="primary"):
                with st.spinner("Generating mail..."):
                    mail_reason = f"Output from discrepancy check agent: {st.session_state.discrepancy}"
                    st.session_state.mail_content = generate_mail_with_reason(mail_reason, st.session_state.c_name, "Spanidea")
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

            with col2:
                # Spacer
                st.write("")
                st.write("")
                if st.button(f"📤 Send to {st.session_state.c_name}", type="primary"):
                    with st.spinner("Sending mail..."):
                        send_status = send_mail_agent(st.session_state.mail_content, to_mail=st.session_state.to_mail)
                        if send_status:
                            st.success("Mail sent successfully!")
                        else:
                            st.error("Failed to send mail.")
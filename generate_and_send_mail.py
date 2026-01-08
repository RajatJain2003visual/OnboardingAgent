from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import smtplib
import mimetypes
from email.message import EmailMessage
from pathlib import Path
from typing import List, Optional, TypedDict, Annotated
from langchain.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain.messages import HumanMessage, SystemMessage
from langchain_core.messages import BaseMessage
import operator
import streamlit as st
import base64
import mimetypes
import os
from pathlib import Path
from typing import List, Optional
from email.message import EmailMessage
from googleapiclient.errors import HttpError
import os
import base64
from googleapiclient.errors import HttpError

load_dotenv()

llm = ChatOpenAI(model="gpt-5-nano")


# @tool
# def send_mail(
#     sender: str,
#     to: List[str],
#     subject: str,
#     text: str,
#     html: Optional[str] = None,
#     cc: Optional[List[str]] = None,
#     bcc: Optional[List[str]] = None,
#     attachments: Optional[List[str]] = None,
#     smtp_server: str = "smtp.gmail.com",
#     port: int = 465,
# ):
#     """
#     Send an email with optional HTML content and attachments.

#     App password must be stored in environment variable:
#     GMAIL_APP_PASSWORD
#     """

#     if not to:
#         raise ValueError("At least one recipient is required")

#     app_password = os.getenv("EMAIL_PASSWORD")
#     # app_password = st.secrets("EMAIL_PASSWORD")
#     # app_password = st.session_state.EMAIL_PASSWORD
#     if not app_password:
#         raise EnvironmentError("EMAIL_PASSWORD not set")

#     cc = cc or []
#     bcc = bcc or []
#     attachments = attachments or []

#     msg = EmailMessage()
#     msg["From"] = sender
#     msg["To"] = ", ".join(to)
#     msg["Cc"] = ", ".join(cc)
#     msg["Subject"] = subject

#     # ---- Email body ----
#     msg.set_content(text)

#     if html:
#         msg.add_alternative(html, subtype="html")

#     # ---- Attachments ----
#     for file_path in attachments:
#         path = Path(file_path)

#         if not path.exists():
#             raise FileNotFoundError(f"Attachment not found: {file_path}")

#         mime_type, _ = mimetypes.guess_type(path)
#         maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)

#         with open(path, "rb") as f:
#             msg.add_attachment(
#                 f.read(),
#                 maintype=maintype,
#                 subtype=subtype,
#                 filename=path.name,
#             )

#     # ---- Send email ----
#     all_recipients = to + cc + bcc

#     with smtplib.SMTP_SSL(smtp_server, port) as server:
#         server.login(sender, app_password)
#         server.send_message(msg, to_addrs=all_recipients)

#     return True

@tool
def send_gmail_message(
    service,
    to: List[str],
    subject: str,
    text: str,
    sender: str = "me",
    html: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
):
    """
    Composes and sends an email using the Gmail API with support for HTML, CC, BCC, and Attachments.

    Args:
        service: The authenticated Gmail API service instance.
        to (List[str]): List of recipient email addresses.
        subject (str): The subject of the email.
        text (str): The plain text body of the email.
        sender (str): The sender address. Defaults to "me" (authenticated user). 
                      Can be formatted like "Name <email@example.com>".
        html (str, optional): The HTML body of the email.
        cc (List[str], optional): List of CC recipients.
        bcc (List[str], optional): List of BCC recipients.
        attachments (List[str], optional): List of file paths to attach.

    Returns:
        dict: The sent message object containing 'id' and 'threadId'.
    """

    if not to:
        raise ValueError("At least one recipient is required in the 'to' list.")

    cc = cc or []
    bcc = bcc or []
    attachments = attachments or []

    # 1. Create the EmailMessage Object
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    
    if cc:
        msg["Cc"] = ", ".join(cc)
    
    # Note: The Gmail API handles BCC delivery logic automatically if the header exists, 
    # but strictly speaking, BCC headers should not be visible in the final message body.
    # The API will see this header, deliver to these people, and strip the header for the recipients.
    if bcc:
        msg["Bcc"] = ", ".join(bcc)

    # 2. Set Email Body (Text + HTML Fallback)
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    # 3. Process Attachments
    for file_path in attachments:
        path = Path(file_path)

        if not path.exists():
            # You might want to log a warning instead of raising, depending on agent behavior
            raise FileNotFoundError(f"Attachment not found: {file_path}")

        # Guess MIME type or default to binary stream
        mime_type, _ = mimetypes.guess_type(path)
        maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)

        with open(path, "rb") as f:
            file_data = f.read()
            msg.add_attachment(
                file_data,
                maintype=maintype,
                subtype=subtype,
                filename=path.name,
            )

    # 4. Encode and Send via Gmail API
    try:
        # The Gmail API requires a base64url encoded string of the raw message bytes
        encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        create_message = {'raw': encoded_message}

        # We use the 'messages.send' method instead of smtplib
        sent_message = service.users().messages().send(userId='me', body=create_message).execute()
        
        print(f"Email sent successfully. Message Id: {sent_message['id']}")
        return sent_message

    except HttpError as error:
        print(f"An error occurred while sending email via Gmail API: {error}")
        return None

def generate_mail_with_reason(reason : str, candidate_name : Optional[str]="", sender_name : Optional[str] = "")->str:

    """Generate email using llm"""

    system_prompt = f"You are professional copywriter. You have to write a mail to the candidate whether the documents are approved or not"
    user_prompt = f"""Use this following information to craft mail: \n
    reason : {reason},
    candidate name : {candidate_name},
    sender_name : {sender_name}"""

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]


    try : 
        response = llm.invoke(messages)
        return response.content
    
    except:
        return "Some exception occured"
    

from langchain.agents import create_agent
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


system_prompt = f"You are an email assistant. You first format the 'email body/content format' to 'best html format' and then have to send email based on user request.\n\
                  You have access to tools to send email. Use them when required. Do not ask for any approval from user to send email.\n\
                  Always ensure the email is professional and error free. Return 'True' or 'False' if success or failure"

system_message = SystemMessage(system_prompt)

def send_mail_agent(email_data, to_mail) -> str:
    # GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

    llm = ChatOpenAI(
        model="gpt-5-nano"
    )

    sender_name = os.getenv("EMAIL_USERNAME")
    # sender_name = st.secrets("EMAIL_USERNAME")
    # sender_name = st.session_state.EMAIL_USERNAME
    message = f"Send the mail based on this content: {email_data}, to : {to_mail} , from : {sender_name}"
    user_message = HumanMessage(message)

    messages = [system_message, user_message]
    
    tool = [send_mail]
    agent = create_agent(model=llm, tools=tool)

    response = agent.invoke({"messages":messages})

    return response['messages'][-1].content
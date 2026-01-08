import imaplib
import email
import os
from getpass import getpass
from typing import Optional
from langchain.tools import tool
from dotenv import load_dotenv
import streamlit as st
import os
import base64
from googleapiclient.errors import HttpError

load_dotenv(override=True)

IMAP_SERVER = "imap.gmail.com"

import json
os.makedirs("attachments", exist_ok=True)

# @tool
# def download_attachments(
#     search_criteria:str = None
# ) -> str:
#     """
#     Downloads attachments from emails.
#     Use below search_criteria commands with 'COMMAND' only:
#     ALL, ANSWERED, UNANSWERED, DELETED, UNDELETED, DRAFT, UNDRAFT, FLAGGED, UNFLAGGED, SEEN, UNSEEN, RECENT,
#     FROM "str", TO "str", CC "str", BCC "str", SUBJECT "str", BODY "str", TEXT "str", HEADER <field> "str", BEFORE <date>,
#     ON <date>, SINCE <date>, LARGER <bytes>, SMALLER <bytes>, UID <ids>, KEYWORD "kw", UNKEYWORD "kw", NOT <crit>,
#     OR <crit1> <crit2>, (use X-GM-RAW for Gmail)
#     For example: '(SUBJECT "Offer Letter")' OR '(SINCE 01-Dec-2024 LARGER 50000 UNFLAGGED)' etc
#     """
#     USERNAME = os.getenv("EMAIL_USERNAME")
#     EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

#     # USERNAME = st.secrets("EMAIL_USERNAME")
#     # EMAIL_PASSWORD = st.secrets("EMAIL_PASSWORD")

#     # USERNAME = st.session_state.EMAIL_USERNAME
#     # EMAIL_PASSWORD = st.session_state.EMAIL_PASSWORD

#     output_dir = './attachments'
#     mailbox = 'INBOX'
#     os.makedirs(output_dir, exist_ok=True)
#     metadata = []  # List of dicts: {'filename': str, 'sender': str, 'uid': str}

#     try:
#         mail = imaplib.IMAP4_SSL(IMAP_SERVER)
#         mail.login(USERNAME, EMAIL_PASSWORD)

#         rv, data = mail.select(mailbox)
#         if rv != 'OK':
#             mail.logout()
#             return f"Mailbox select failed for {mailbox}: {data}"

#         status, messages = mail.search(None, search_criteria)
#         email_ids = messages[0].split()
#         count = 0

#         for email_id in email_ids:
#             status, msg_data = mail.fetch(email_id, '(RFC822)')
#             raw_email = msg_data[0][1]
#             msg = email.message_from_bytes(raw_email)
#             sender = msg.get('From', 'Unknown')

#             for part in msg.walk():
#                 if part.get_content_maintype() == 'multipart':
#                     continue
#                 if not part.get('Content-Disposition'):
#                     continue
#                 filename = part.get_filename()
#                 if filename:
#                     filepath = os.path.join(output_dir, filename)
#                     with open(filepath, 'wb') as f:
#                         f.write(part.get_payload(decode=True))
#                     metadata.append({'filename': filename, 'sender': sender, 'uid': email_id.decode()})
#                     count += 1

#         # Save metadata
#         meta_path = os.path.join(output_dir, 'metadata.json')
#         with open(meta_path, 'w') as f:
#             json.dump(metadata, f, indent=2)

#         mail.close()
#         mail.logout()
#         senders = list(set([m['sender'] for m in metadata]))
#         return None
#     except Exception as e:
#         return f"Error: {str(e)}"

@tool
def download_attachments(
    service,
    download_dir='attachments',
    max_results=10,
    sender=None,
    recipient=None,
    subject=None,
    keywords=None,
    date_after=None,
    date_before=None
):
    """
    Downloads email attachments based on structured filters.
    
    Args:
        service: Authenticated Gmail API service.
        download_dir (str): Folder to save attachments.
        max_results (int): Max emails to check (default 10).
        
        sender (str, optional): Filter by sender email (e.g., 'boss@company.com').
        recipient (str, optional): Filter by recipient email (e.g., 'me' or 'colleague@company.com').
        subject (str, optional): Filter by words in the subject line.
        keywords (str, optional): General keywords to search in the email body.
        date_after (str, optional): "YYYY/MM/DD" - Emails received AFTER this date.
        date_before (str, optional): "YYYY/MM/DD" - Emails received BEFORE this date.

    Returns:
        list: Paths of downloaded files.
    """
    
    # --- 1. Construct the Gmail Query String Dynamically ---
    query_parts = ["has:attachment"] # Base requirement: must have files

    if sender:
        query_parts.append(f"from:{sender}")
    
    if recipient:
        query_parts.append(f"to:{recipient}")
    
    if subject:
        query_parts.append(f"subject:({subject})") # Parentheses handle multi-word subjects safely
    
    if keywords:
        query_parts.append(f"{keywords}")
        
    if date_after:
        query_parts.append(f"after:{date_after}")

    if date_before:
        query_parts.append(f"before:{date_before}")

    final_query = " ".join(query_parts)
    print(f"DEBUG - Generated Query: {final_query}")

    # --- 2. Execute Search ---
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    downloaded_files = []

    try:
        results = service.users().messages().list(
            userId='me', 
            q=final_query, 
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])

        if not messages:
            print("No emails found matching these filters.")
            return []

        print(f"Found {len(messages)} emails. Processing...")

        # --- 3. Process Emails (Same as before) ---
        for msg in messages:
            try:
                txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            except HttpError:
                continue 

            def get_parts(payload):
                if 'parts' in payload:
                    for part in payload['parts']:
                        yield from get_parts(part)
                else:
                    yield payload

            for part in get_parts(txt['payload']):
                if part.get('filename') and part.get('body') and part['body'].get('attachmentId'):
                    file_name = part['filename']
                    att_id = part['body']['attachmentId']
                    
                    try:
                        att = service.users().messages().attachments().get(
                            userId='me', messageId=msg['id'], id=att_id
                        ).execute()
                        
                        data = att['data']
                        file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                        
                        # Handle duplicate filenames
                        file_path = os.path.join(download_dir, file_name)
                        if os.path.exists(file_path):
                            file_path = os.path.join(download_dir, f"{msg['id']}_{file_name}")

                        with open(file_path, 'wb') as f:
                            f.write(file_data)
                        
                        downloaded_files.append(file_path)
                        print(f"Downloaded: {file_path}")
                    except Exception as e:
                        print(f"Error downloading {file_name}: {e}")

    except HttpError as error:
        print(f"An error occurred: {error}")
    
    return downloaded_files



# -------------------------------------------------------------------
# CREATING AGENT
# -------------------------------------------------------------------

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

system_message = SystemMessage("You are a email downloading assistant.\n"
        "You are given a tool to download attachments from emails.\n"
        "AFTER the tool result, always return ""True"" or ""False"" as a output")

def download_agent(to_mail:str):
    #GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

    llm = ChatOpenAI(
        model="gpt-4.1-mini"
    )
    user_message = HumanMessage(f"Download attachments send by {to_mail}")

    messages = [system_message, user_message]

    tools = [download_attachments]

    agent = create_agent(model=llm, tools=tools)

    response = agent.invoke({"messages":messages})

    return response['messages'][-1].content

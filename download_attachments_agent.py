import imaplib
import email
import os
from getpass import getpass
from typing import Optional
from langchain.tools import tool
from dotenv import load_dotenv
import streamlit as st

load_dotenv(override=True)

IMAP_SERVER = "imap.gmail.com"

import json
os.makedirs("attachments", exist_ok=True)

@tool
def download_attachments(
    search_criteria:str = None
) -> str:
    """
    Downloads attachments from emails.
    Use below search_criteria commands with 'COMMAND' only:
    ALL, ANSWERED, UNANSWERED, DELETED, UNDELETED, DRAFT, UNDRAFT, FLAGGED, UNFLAGGED, SEEN, UNSEEN, RECENT,
    FROM "str", TO "str", CC "str", BCC "str", SUBJECT "str", BODY "str", TEXT "str", HEADER <field> "str", BEFORE <date>,
    ON <date>, SINCE <date>, LARGER <bytes>, SMALLER <bytes>, UID <ids>, KEYWORD "kw", UNKEYWORD "kw", NOT <crit>,
    OR <crit1> <crit2>, (use X-GM-RAW for Gmail)
    For example: '(SUBJECT "Offer Letter")' OR '(SINCE 01-Dec-2024 LARGER 50000 UNFLAGGED)' etc
    """
    # USERNAME = os.getenv("EMAIL_USERNAME")
    # EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

    USERNAME = st.secrets("EMAIL_USERNAME")
    EMAIL_PASSWORD = st.secrets("EMAIL_PASSWORD")

    output_dir = './attachments'
    mailbox = 'INBOX'
    os.makedirs(output_dir, exist_ok=True)
    metadata = []  # List of dicts: {'filename': str, 'sender': str, 'uid': str}

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(USERNAME, EMAIL_PASSWORD)

        rv, data = mail.select(mailbox)
        if rv != 'OK':
            mail.logout()
            return f"Mailbox select failed for {mailbox}: {data}"

        status, messages = mail.search(None, search_criteria)
        email_ids = messages[0].split()
        count = 0

        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            sender = msg.get('From', 'Unknown')

            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if not part.get('Content-Disposition'):
                    continue
                filename = part.get_filename()
                if filename:
                    filepath = os.path.join(output_dir, filename)
                    with open(filepath, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                    metadata.append({'filename': filename, 'sender': sender, 'uid': email_id.decode()})
                    count += 1

        # Save metadata
        meta_path = os.path.join(output_dir, 'metadata.json')
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        mail.close()
        mail.logout()
        senders = list(set([m['sender'] for m in metadata]))
        return None
    except Exception as e:
        return f"Error: {str(e)}"


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

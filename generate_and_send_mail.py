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

load_dotenv()

llm = ChatOpenAI(model="gpt-5-nano")


@tool
def send_mail(
    sender: str,
    to: List[str],
    subject: str,
    text: str,
    html: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
    smtp_server: str = "smtp.gmail.com",
    port: int = 465,
):
    """
    Send an email with optional HTML content and attachments.

    App password must be stored in environment variable:
    GMAIL_APP_PASSWORD
    """

    if not to:
        raise ValueError("At least one recipient is required")

    app_password = os.getenv("EMAIL_PASSWORD")
    if not app_password:
        raise EnvironmentError("EMAIL_PASSWORD not set")

    cc = cc or []
    bcc = bcc or []
    attachments = attachments or []

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject

    # ---- Email body ----
    msg.set_content(text)

    if html:
        msg.add_alternative(html, subtype="html")

    # ---- Attachments ----
    for file_path in attachments:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Attachment not found: {file_path}")

        mime_type, _ = mimetypes.guess_type(path)
        maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)

        with open(path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=path.name,
            )

    # ---- Send email ----
    all_recipients = to + cc + bcc

    with smtplib.SMTP_SSL(smtp_server, port) as server:
        server.login(sender, app_password)
        server.send_message(msg, to_addrs=all_recipients)

    return True

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
    message = f"Send the mail based on this content: {email_data}, to : {to_mail} , from : {sender_name}"
    user_message = HumanMessage(message)

    messages = [system_message, user_message]
    
    tool = [send_mail]
    agent = create_agent(model=llm, tools=tool)

    response = agent.invoke({"messages":messages})

    return response['messages'][-1].content

if __name__ == "__main__":
    send_mail_agent("Hi How are you ?", "rajatofficial5940@gmail.com")


if __name__ == "__main__":
    pass


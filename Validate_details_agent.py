import imaplib
import email
import os
from getpass import getpass
from typing import Optional
from langchain.tools import tool
from dotenv import load_dotenv
from validate_agent_sys_prompt import system_prompt

load_dotenv(override=True)

# -------------------------------------------------------------------
# CREATING AGENT
# -------------------------------------------------------------------

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


system_message = SystemMessage(system_prompt)

def validate_agent(data) -> str:
    #GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

    llm = ChatOpenAI(
        model="gpt-5-mini",
    )
    user_message = HumanMessage(f"Validate the following details: {data}.\n")

    messages = [system_message, user_message]

    agent = create_agent(model=llm)

    response = agent.invoke({"messages":messages})

    return response['messages'][-1].content


# output = validate_agent("pmuskan@spanidea.com")
# print(output)
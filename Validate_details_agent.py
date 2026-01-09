import imaplib
import email
import os
from getpass import getpass
from typing import Optional
from langchain.tools import tool
from dotenv import load_dotenv
from validate_agent_sys_prompt import system_prompt
from data_extract_prompt import prompt as details_extract_prompt
load_dotenv(override=True)

# # -------------------------------------------------------------------
# # CREATING AGENT
# # -------------------------------------------------------------------

# from langchain.agents import create_agent
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_openai import ChatOpenAI
# from langchain_core.messages import HumanMessage, SystemMessage


# system_message = SystemMessage(system_prompt)

# def validate_agent(data) -> str:
#     #GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

#     llm = ChatOpenAI(
#         model="gpt-5-mini",
#     )
#     user_message = HumanMessage(f"Validate the following details: {data}.\n "
#                                 "Here is the prompt that is used for extracting detail from the documents, use this: {details_extract_prompt}")

#     messages = [system_message, user_message]

#     agent = create_agent(model=llm)

#     response = agent.invoke({"messages":messages})

#     return response['messages'][-1].content


# # output = validate_agent("pmuskan@spanidea.com")
# # print(output)

#############################################################
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from langchain.agents import create_agent
import os

from validate_agent_sys_prompt import system_prompt
from data_extract_prompt import details_extract_prompt

load_dotenv(override=True)

system_message = SystemMessage(content=system_prompt)

def validate_agent(extracted_data: str) -> str:
    llm = ChatOpenAI(
        model="gpt-5-mini",
        temperature=0,
    )

    user_message = HumanMessage(
        content=f"""
You are provided with:

1. Extracted structured data (JSON):
{extracted_data}

2. Original extraction prompt used to generate this data:
{details_extract_prompt}

Validate the extracted data STRICTLY according to the extraction rules and the validation rules provided in the system message.
IMPORTANT : Output in this format of tuple (your_response, sentiment) Eg. ("No discrepencies found ", positive) . For sentiment use only ["positive","negative"] 
"""
    )

    agent = create_agent(model=llm)
    messages = [system_message, user_message]
    response = agent.invoke({"messages":messages})
    return response['messages'][-1].content

    # response = llm.invoke('messages'[system_message, user_message])

    # return response.content


data = """
{
  "academics": {
    "10th": {
      "name": "Amit Kumar",
      "dob": "1999-08-15",
      "passing_year": "2015",
      "percentage_or_cgpa": "89.4",
      "if_10th_document_exists": "yes"
    },
    "12th": {
      "name": "Amit Kumar",
      "passing_year": "2017",
      "percentage_or_cgpa": "85.2",
      "if_12th_document_exists": "yes"
    }
  },
  "college": {
    "ug": {
      "degree": "B.Tech in Computer Science",
      "duration": "2017-2021",
      "final_cgpa_or_percentage": "8.32",
      "if_ug_document_exists": "yes"
    },
    "pg": {
      "degree": "",
      "duration": "",
      "final_cgpa_or_percentage": "",
      "if_pg_document_exists": "no"
    }
  },
  "jobs": [],
  "salary": {
    "last_3_months_salary_slips": [],
    "last_3_months_bank_statement_salary_credits": []
  },
  "identity_documents": {
    "aadhaar": {
      "name": "Amit Kumar",
      "dob": "1999-08-15",
      "aadhaar_number": "123456789012",
      "if_aadhaar_exists": "yes"
    },
    "pan": {
      "name": "Amit Kumar",
      "pan_number": "ABCDE1234F",
      "dob": "1999-08-15",
      "if_pan_exists": "yes"
    }
  }
}

"""
# output = validate_agent(data)
# print(output)
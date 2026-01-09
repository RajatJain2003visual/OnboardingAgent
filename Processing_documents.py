import base64
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
from data_extract_prompt import prompt
import os
import mimetypes
import json
import pandas as pd
from datetime import datetime

client = OpenAI()

def process_documents(folder_path="attachments"):    
    print("Entered process_documents")

    content = []

    all_files = []

    # Recursively collect all files from all subfolders
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)

            # skip non-files (safety)
            if not os.path.isfile(file_path):
                continue

            all_files.append(file_path)

    print(f"Total files found: {len(all_files)}")

    # Process files
    for file_path in all_files:
        print(file_path)

        with open(file_path, "rb") as f:
            data = f.read()

        base64_string = base64.b64encode(data).decode("utf-8")
        mime_type, _ = mimetypes.guess_type(file_path)

        # IMAGE FILES
        if mime_type and mime_type.startswith("image/"):
            content.append({
                "type": "input_image",
                "image_url": f"data:{mime_type};base64,{base64_string}"
            })

        # PDF FILES
        elif mime_type == "application/pdf":
            content.append({
                "type": "input_file",
                "filename": os.path.basename(file_path),
                "file_data": f"data:application/pdf;base64,{base64_string}",
            })

    return content


def extract_details():
    content = process_documents()
    print("Uploading documents now")
    current_date = datetime.now().strftime("%Y-%m-%d")
    # content.append({
    #                 "type": "input_text",
    #                 "text": prompt,
    #             })
    content.append({
        "type": "input_text",
        "text": f"Current Date: {current_date}\n" + prompt, # Prepend date
    })

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": content
            }
        ],
    )

    raw_text = response.output_text


    # Parse JSON
    parsed = json.loads(raw_text)

    print("Details extracted")
    
    # 1. Create Academics Table
    df_academics = pd.DataFrame(parsed['academics']).transpose()

    # 2. Create College Table (UG and PG)
    df_college = pd.DataFrame(parsed['college']).transpose()

    # 3. Create Jobs Table
    # Since 'jobs' is a list of dictionaries, we use json_normalize
    df_jobs = pd.json_normalize(parsed['jobs'])

    # 4. Create Salary Tables
    df_salary_slips = pd.json_normalize(parsed['salary']['last_3_months_salary_slips'])
    df_bank_credits = pd.json_normalize(parsed['salary']['last_3_months_bank_statement_salary_credits'])

    #5. Identity Documents Table
    df_identity_docs = pd.DataFrame(parsed['identity_documents']).transpose()


    # Checklist:
    is_last_3_months_salary_slip_available = len(df_salary_slips) >= 3
    is_last_3_months_bank_statement_salary_credit_available = len(df_bank_credits) >= 3


    checklist_df = pd.DataFrame({
        "document": ["10th", "12th", "UG", "PG", "AADHAR", "PAN", ],
        "exists": [
            "✅" if df_academics["if_10th_document_exists"].eq("yes").any() else "❌",
            "✅" if df_academics["if_12th_document_exists"].eq("yes").any() else "❌",
            "✅" if df_college["if_ug_document_exists"].eq("yes").any() else "❌",
            "✅" if df_college["if_pg_document_exists"].eq("yes").any() else "❌",
            "✅" if df_identity_docs["if_aadhaar_exists"].eq("yes").any() else "❌",
            "✅" if df_identity_docs["if_pan_exists"].eq("yes").any() else "❌",
        ]
    })

    salary_rows = pd.DataFrame({
    "document": [
        "LAST 3 MONTHS SALARY SLIPS",
        "LAST 3 MONTHS BANK SALARY CREDITS"
    ],
    "exists": [
        "✅" if is_last_3_months_salary_slip_available else "❌",
        "✅" if is_last_3_months_bank_statement_salary_credit_available else "❌"
    ]
    })

    checklist_df = pd.concat([checklist_df, salary_rows], ignore_index=True)


    return (checklist_df, df_academics, df_college, df_jobs, df_salary_slips, df_bank_credits, df_identity_docs), parsed
import fitz # it is the old name of pymupdf used to convert doc page into image
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form
import base64 #it convert image to text (groq api dont understand binary so we need to send it by text)
from groq import Groq
import os
import time
import tempfile
import json
import re


load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def classify_pdf_pages(pdf_path):
    
    doc = fitz.open(pdf_path) #it will have something like [page0,page1,page2,..]
    results = {}
    for i in range(len(doc)):
        page = doc[i] #inside pymypdf it will open it like doc.load_page(i)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) #it will take pic off that page
        
        img_base64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")

        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Classify this page into one of these: claim_forms, cheque_or_bank_details, identity_document, itemized_bill, discharge_summary, prescription, investigation_report, cash_receipt, other. Return ONLY ONE exact category name from the list. Do NOT add punctuation, explanation, or extra text."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                    }
                ]
            }]
        )

        category = response.choices[0].message.content.strip().lower().replace(".", "")
        VALID_CATEGORIES = {
    "claim_forms",
    "cheque_or_bank_details",
    "identity_document",
    "itemized_bill",
    "discharge_summary",
    "prescription",
    "investigation_report",
    "cash_receipt",
    "other"
        }

        if category not in VALID_CATEGORIES:
            category = "other"
        results[i + 1] = category
        time.sleep(2)
        print(f"page {i+1} → {category}")

    doc.close()
    return results

# we are grouping it intoo category1:[1,2,3],catb:[5,6]
def group_pages(results):
    grouped = {}

    for page, category in results.items():
        if category not in grouped:
            grouped[category] = []
        
        grouped[category].append(page)

    return grouped   # it would be something like {catx:[1,2,3],catb:[5,6,7]}

#it is basically what each node will look like so for that we are sending pages
def prepare_llm_input(doc, pages, instruction):
    content = [
        {
            "type": "text",
            "text": instruction
        }
    ]

    for page_num in pages:
        page = doc[page_num - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

        img_base64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")

        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_base64}"}
        })

    return content # in short our content here is the actual prompt

def id_agent(doc, pages):
    instruction = "Extract patient name, DOB, ID number and policy details in JSON.Do NOT include explanation"

    content = prepare_llm_input(doc, pages, instruction)

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role": "user",
            "content": content
        }]
    )

    return response.choices[0].message.content

def discharge_summary_agent(doc, pages):
    instruction = " Extracts diagnosis, admit/discharge dates, physician details in JSON.Do NOT include explanation"

    content = prepare_llm_input(doc, pages, instruction)

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role": "user",
            "content": content
        }]
    )

    return response.choices[0].message.content

def bill_agent(doc, pages):
    instruction = "Extracts all items with costs and calculates total amount Each agent processes only the pages assigned to them by segregator in JSON.Do NOT include explanation"

    content = prepare_llm_input(doc, pages, instruction)

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role": "user",
            "content": content
        }]
    )

    return response.choices[0].message.content


def run_agents(doc, grouped):
    output = {}

    if "identity_document" in grouped:
        output["id_data"] = id_agent(doc, grouped["identity_document"])

    if "discharge_summary" in grouped:
        output["discharge_data"] = discharge_summary_agent(doc, grouped["discharge_summary"])

    if "itemized_bill" in grouped:
        output["bill_data"] = bill_agent(doc, grouped["itemized_bill"])

    return output

# removes ```json and ``` markdown wrapping that llm adds and parses it into clean dict
def clean_llm_output(text):
    if not isinstance(text, str):
        return text
    text = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(text)
    except:
        return text

def aggregate_results(results):
    return {
        "identity": clean_llm_output(results.get("id_data", {})),
        "discharge": clean_llm_output(results.get("discharge_data", {})),
        "billing": clean_llm_output(results.get("bill_data", {}))
    }
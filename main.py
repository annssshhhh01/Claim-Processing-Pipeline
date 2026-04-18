import fitz # it is the old name of pymupdf used to convert doc page into image
from dotenv import load_dotenv
from fastapi import FastAPI
import base64 #it convert image to text (groq api dont understand binary so we need to send it by text)
from groq import Groq
import os

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def classify_pdf_pages(pdf_path):
    
    doc = fitz.open(pdf_path) #it will have something like [page0,page1,page2,..]
    results = {}
    for i in range(len(doc)):
        page = doc[i] #inside pymypdf it will open it like doc.load_page(i)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) #it will take pic off that page
        img_base64 = base64.b64encode(pix.tobytes("png")).decode("utf-8") #convert image to byte then through base64 convert to text and utf8 comvert it to string
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                    },
                    {
                        "type": "text",
                        "text": "Classify this page into one of these: claim_forms, cheque_or_bank_details, identity_document, itemized_bill, discharge_summary, prescription, investigation_report, cash_receipt, other. Just reply with the category name only."
                    }
                ]
            }]
        )

        category = response.choices[0].message.content.strip()
        results[i + 1] = category
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

    return grouped



if __name__ == "__main__":
    classifications = classify_pdf_pages("sample.pdf")
    print("\nDone:", classifications)
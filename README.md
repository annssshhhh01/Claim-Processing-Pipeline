# 🏥 Medical Claim Processing Pipeline

A FastAPI service that processes PDF medical claims using LangGraph to orchestrate document segregation and multi-agent extraction.

---

## 🔄 Architecture Flow

```
User
  ↓
FastAPI Endpoint (POST /api/process)
  ↓
LangGraph Start
  ↓
Segregator (pdf → image → classify pages)
  ↓
Group Pages (category: [1,2,3])
  ↓
Router
  ↓
┌─────────────────┬──────────────────────┬─────────────────────┐
│  ID Agent       │ Discharge Summary    │ Itemized Bill Agent │
│                 │ Agent                │                     │
│ Extracts:       │ Extracts:            │ Extracts:           │
│ - Patient name  │ - Diagnosis          │ - All bill items    │
│ - DOB           │ - Admit/discharge    │ - Costs             │
│ - ID number     │   dates              │ - Total amount      │
│ - Policy details│ - Physician details  │                     │
└─────────────────┴──────────────────────┴─────────────────────┘
  ↓
Aggregator
  ↓
Final JSON Response
```

> Each agent only processes the pages assigned to it by the Router. They do only the work which was assigned by the Router.

---

## 📁 Project Structure

```
project/
  main.py       ← FastAPI endpoint
  graph.py      ← LangGraph pipeline (nodes + edges)
  utils.py      ← All functions (segregator, agents, aggregator)
  sample.pdf    ← Sample claim PDF for testing
  .env          ← API keys
  requirements.txt
```

---

## ⚙️ How It Works

### Step 1 — Segregator
- Takes the uploaded PDF
- Converts every page into an image using PyMuPDF
- Sends each page image to the LLM (Groq)
- LLM classifies each page into one of 9 document types:
  - `claim_forms`
  - `cheque_or_bank_details`
  - `identity_document`
  - `itemized_bill`
  - `discharge_summary`
  - `prescription`
  - `investigation_report`
  - `cash_receipt`
  - `other`

### Step 2 — Group Pages
- Groups classified pages by category
- Example output: `{ "identity_document": [3], "discharge_summary": [4], "itemized_bill": [9, 10] }`

### Step 3 — Router → Agents
- **ID Agent** → receives only `identity_document` pages
- **Discharge Summary Agent** → receives only `discharge_summary` pages
- **Itemized Bill Agent** → receives only `itemized_bill` pages
- If a category has no pages, that agent returns empty

### Step 4 — Aggregator
- Combines all agent outputs
- Cleans LLM markdown formatting
- Returns final structured JSON

---

## 🚀 Setup & Installation

### 1. Clone the repo
```bash
git clone <your-repo-url>
cd relio-assignment
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

### 3. Install dependencies
```bash
pip install fastapi uvicorn pymupdf langgraph langchain-groq groq python-multipart python-dotenv
```

### 4. Set up `.env`
```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
```

### 5. Run the server
```bash
uvicorn main:app --reload
```

---

## 📬 API Usage

### Endpoint
```
POST /api/process
```

### Input
| Field | Type | Description |
|-------|------|-------------|
| `claim_id` | string | Unique claim identifier |
| `file` | PDF file | The medical claim PDF |

### Test with curl
```bash
curl -X POST "http://localhost:8000/api/process" \
  -F "claim_id=CLM-001" \
  -F "file=@sample.pdf"
```

### Test with Swagger UI
Open `http://localhost:8000/docs` in your browser.

---

## 📤 Sample Output

```json
{
  "claim_id": "CLM-001",
  "status": "success",
  "page_classifications": {
    "1": "claim_forms",
    "2": "cheque_or_bank_details",
    "3": "identity_document",
    "4": "discharge_summary",
    "5": "prescription",
    "9": "itemized_bill",
    "10": "itemized_bill"
  },
  "extracted_data": {
    "identity": {
      "patient_name": "John Michael Smith",
      "date_of_birth": "15-MAR-1985",
      "id_number": "ID-987-654-321",
      "policy_details": {
        "issue_date": "15-JAN-2023",
        "expiry_date": "15-JAN-2033"
      }
    },
    "discharge": {
      "diagnosis": "Community Acquired Pneumonia (CAP)",
      "admit_date": "January 20, 2025",
      "discharge_date": "January 25, 2025",
      "physician_details": "Dr. Sarah Johnson, MD"
    },
    "billing": {
      "items": [
        { "description": "Room Charges - Semi-Private (5 days)", "amount": 1000.00 },
        { "description": "Emergency Room Services", "amount": 500.00 }
      ],
      "subtotal": 6113.00,
      "tax": 305.65,
      "total_amount": 6418.65,
      "insurance_payment": 5134.92,
      "patient_responsibility": 1283.73
    }
  }
}
```

---

## 🛠 Tech Stack

| Tool | Purpose |
|------|---------|
| FastAPI | REST API endpoint |
| LangGraph | Multi-agent pipeline orchestration |
| PyMuPDF (fitz) | PDF to image conversion |
| Groq API | LLM for classification and extraction |
| Llama 4 Scout | Vision model used for page classification |
| Python-dotenv | Environment variable management |

---

## ⚠️ Notes

- Groq free tier has a daily token limit of 500,000 tokens. If you hit the limit, wait until the next day or upgrade to Dev tier.
- The segregator uses vision (image) to classify pages. Extraction agents use vision as well for accuracy.
- Page classification is flexible — works on any PDF regardless of page order or count.

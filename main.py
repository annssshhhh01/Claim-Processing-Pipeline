import fitz
from dotenv import load_dotenv
from fastapi import FastAPI
load_dotenv()

doc = fitz.open("your_file.pdf")
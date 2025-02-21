import io
import logging
import re
from typing import Union

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .pdf import read_pdf
from .summary import generate_summary


def convert_section(text):
    match = re.fullmatch(r'section(\d+)', text, re.IGNORECASE)
    if match:
        number = match.group(1)
        return f"Section {number}"
    else:
        raise ValueError("Input string does not match the pattern 'section[0-9]+'")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify the origin(s) of your Next.js app, e.g., ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Hello": "World3"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile):
    contents = await file.read()
    file_io = io.BytesIO(contents)
    final_responses = generate_summary(file_io)

    sections = []
    texts = []

    for section in sorted(final_responses):
        if section != "Total Summary":
            sections.append(convert_section(section))
        else:
            sections.append(section)
        texts.append(final_responses[section])

    return {"sections": sections, "texts": texts}

import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import openai
from dotenv import load_dotenv
import os
import shutil
from datetime import datetime

# Load environment variables (expects .env file)
load_dotenv()
openai.api_key = os.environ['OPENAI_API_KEY']

CHROMA_PATH = "chroma"
DATA_PATH = "data/reports/case_studies.jsonl"

def main():
    generate_data_store()

def generate_data_store():
    documents = load_documents()
    chunks = split_text(documents)
    save_to_chroma(chunks)

def load_documents():
    documents = []
    with open(DATA_PATH, "r", encoding="utf-8") as file:
        for line in file:
            case = json.loads(line.strip())
            body = case.get("bodytext", "")
            url = case.get("url", "")
            function_name = case.get("function_name", "")

            # Extract title from first sentence
            title = body.strip().split("\n")[0][:120]

            # Create a short summary
            summary = body.strip()[:500]

            # Tag category based on presence of keywords
            category = "prevention" if any(kw in body.lower() for kw in ["prevention", "awareness", "task force", "training", "education"]) else "prosecution"

            metadata = {
                "url": url,
                "function_name": function_name,
                "title": title,
                "summary": summary,
                "category": category,
                "source": "DOJ Press Release",
                "ingested_at": datetime.utcnow().isoformat()
            }

            doc = Document(page_content=body, metadata=metadata)
            documents.append(doc)

    return documents

def split_text(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2500,
        chunk_overlap=200,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"✅ Split {len(documents)} documents into {len(chunks)} chunks.")
    return chunks

def save_to_chroma(chunks: list[Document]):
    # Clear out the database first.
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    # Create and persist Chroma DB
    db = Chroma.from_documents(
        chunks,
        OpenAIEmbeddings(),
        persist_directory=CHROMA_PATH
    )
    
    print(f"✅ Saved {len(chunks)} chunks to {CHROMA_PATH}.")

if __name__ == "__main__":
    main()

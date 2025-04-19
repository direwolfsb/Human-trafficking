import json
import os
import shutil
import logging
from datetime import datetime, timezone
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
from PyPDF2 import PdfReader

# Initialize logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Load API key from .env
load_dotenv()
os.environ['OPENAI_API_KEY'] = os.getenv("OPENAI_API_KEY")

CHROMA_PATH = "chroma"
PDF_DIR = "data/reports/pdfs"
JSONL_PATH = "data/reports/case_studies.jsonl"

# Map known PDFs to their URLs
# Map known PDFs to their URLs
pdf_url_map = {
    # Your previous 10
    "TIP-Report-2024_Introduction_V10_508-accessible_2.13.2025.pdf":
        "https://www.state.gov/reports/2024-trafficking-in-persons-report",

    "Polaris-Analysis-of-2021-Data-from-the-National-Human-Trafficking-Hotline.pdf":
        "https://polarisproject.org/wp-content/uploads/2020/07/Polaris-Analysis-of-2021-Data-from-the-National-Human-Trafficking-Hotline.pdf",

    "In-Harms-Way-How-Systems-Fail-Human-Trafficking-Survivors-by-Polaris-modifed-June-2023.pdf":
        "https://polarisproject.org/resources/in-harms-way-how-systems-fail-human-trafficking-survivors/",

    "Hotline-Trends-Report-2023.pdf":
        "https://polarisproject.org/wp-content/uploads/2020/07/Hotline-Trends-Report-2023.pdf",

    "GLOTIP2024_Chapter_1.pdf":
        "https://www.unodc.org/unodc/en/data-and-analysis/glotip.html",

    "GLOTIP2024_Chapter_2.pdf":
        "https://www.unodc.org/unodc/en/data-and-analysis/glotip.html",

    "GLOTIP2024_Chapter_3.pdf":
        "https://www.unodc.org/unodc/en/data-and-analysis/glotip.html",

    # New 10 from your uploads
    "Polaris-Typology-of-Modern-Slavery-1.pdf":
        "https://polarisproject.org/wp-content/uploads/2019/09/Polaris-Typology-of-Modern-Slavery-1.pdf",

    "Parent Resource Guide_FINAL_update 2021.pdf":
        "https://ctip.defense.gov/Portals/12/Parent%20Resource%20Guide_FINAL_update%202025.pdf",

    "RESOURCE-GUIDE-ONLINE-SAFETY-GROOMING-&-SEXTORTION.pdf":
        "https://www.eyesupappalachia.org/_files/ugd/14b638_bf90969f778f42318734e03df56bd448.pdf",

    "HUMAN TRAFFICKING RESPONSE GUIDE for School Resource Officers.pdf":
        "https://www.dhs.gov/sites/default/files/2024-06/240624_bc_human_trafficking_response_guide_school_resource_officers.pdf",

    "HUMAN TRAFFICKING AWARENESS GUIDE for Convenience Retail Employees.pdf":
        "https://www.dhs.gov/sites/default/files/2024-06/240624_bc_convenience_store_guide.pdf",

    "HOW TO TALK TO YOUTH ABOUT HUMAN TRAFFICKING A Guide for Youth Caretakers and Individuals Working with Youth.pdf":
        "https://www.dhs.gov/sites/default/files/publications/blue_campaign_youth_guide_508_1.pdf",

    "FIU-Peer-to-Peer-Platforms-Case-Study.pdf":
        "https://polarisproject.org/wp-content/uploads/2024/05/FIU-Peer-to-Peer-Platforms-Case-Study.pdf",

    "Combating Child Sex Trafficking a Guide for Law Enforcement.pdf":
        "https://www.theiacp.org/sites/default/files/IACPCOPSCombatingChildSexTraffickingAGuideforLELeaders.pdf",

    "CaseStudies-voi.pdf":
        "https://sharedhope.org/wp-content/uploads/2020/10/CaseStudies-voi.pdf",

    "2023-Federal-Human-Trafficking-Report-WEB-Spreads-LR.pdf":
        "https://traffickinginstitute.org/wp-content/uploads/2024/06/2023-Federal-Human-Trafficking-Report-WEB-Spreads-LR.pdf",

    "2017_April_AZ_SexTraffickingResearch.pdf":
        "https://ag.nv.gov/uploadedFiles/agnvgov/Content/Human_Trafficking/2017_April_AZ_SexTraffickingResearch.pdf"
}

def extract_text_from_pdf(pdf_path):
    logging.info(f"📄 Extracting text from: {pdf_path}")
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

def extract_title_from_pdf(pdf_path):
    logging.info(f"🔍 Extracting title from: {pdf_path}")
    try:
        reader = PdfReader(pdf_path)
        first_page_text = reader.pages[0].extract_text() or ""
        for line in first_page_text.splitlines():
            if line.strip():
                logging.info(f"✅ Title found: {line.strip()}")
                return line.strip()
        return os.path.basename(pdf_path).replace("_", " ").replace(".pdf", "")
    except Exception as e:
        fallback = os.path.basename(pdf_path).replace("_", " ").replace(".pdf", "")
        logging.error(f"❌ Error extracting title: {e}, using fallback: {fallback}")
        return fallback

def load_documents():
    documents = []
    logging.info("📦 Loading documents from JSONL and PDF sources...")

    # Load JSONL case studies
    # if os.path.exists(JSONL_PATH):
    #     with open(JSONL_PATH, "r", encoding="utf-8") as file:
    #         for line in file:
    #             case = json.loads(line.strip())
    #             body = case.get("bodytext", "")
    #             url = case.get("url", "")
    #             function_name = case.get("function_name", "")

    #             title = body.strip().split("\n")[0][:120]
    #             summary = body.strip()[:500]
    #             category = "prevention" if any(
    #                 kw in body.lower() for kw in ["prevention", "awareness", "task force", "training", "education"]
    #             ) else "prosecution"

    #             metadata = {
    #                 "url": url,
    #                 "function_name": function_name,
    #                 "title": title,
    #                 "summary": summary,
    #                 "category": category,
    #                 "source": "DOJ Press Release",
    #                 "ingested_at": datetime.now(timezone.utc).isoformat()
    #             }
    #             documents.append(Document(page_content=body, metadata=metadata))
    #     logging.info("✅ Loaded JSONL case studies.")
    # else:
    #     logging.warning(f"⚠️ JSONL file not found at: {JSONL_PATH}")

    # Load PDF reports
    if os.path.exists(PDF_DIR):
        pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]
        for file_name in pdf_files:
            path = os.path.join(PDF_DIR, file_name)
            text = extract_text_from_pdf(path)
            title = extract_title_from_pdf(path)
            url = pdf_url_map.get(file_name)

            metadata = {
                "title": title,
                "source": title,
                "filename": file_name,
                "url": url,
                "ingested_at": datetime.now(timezone.utc).isoformat()
            }
            documents.append(Document(page_content=text, metadata=metadata))
        logging.info(f"✅ Loaded {len(pdf_files)} PDF reports.")
    else:
        logging.warning(f"⚠️ PDF directory not found: {PDF_DIR}")

    logging.info(f"📚 Total documents loaded: {len(documents)}")
    return documents

def split_text(documents):
    logging.info("✂️ Splitting documents into chunks...")
    chunks = []

    for doc in documents:
        is_pdf = doc.metadata.get("filename", "").endswith(".pdf")
        chunk_size = 1050
        overlap = 150

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            length_function=len,
            add_start_index=True
        )
        split_chunks = splitter.split_documents([doc])
        chunks.extend(split_chunks)

    logging.info(f"✅ Split {len(documents)} documents into {len(chunks)} chunks.")
    return chunks

def save_to_chroma(chunks):
    if os.path.exists(CHROMA_PATH):
        logging.info(f"🗑️ Removing existing Chroma DB at {CHROMA_PATH}")
        shutil.rmtree(CHROMA_PATH)

    logging.info("💾 Saving chunks to Chroma vector database...")
    db = Chroma.from_documents(
        chunks,
        OpenAIEmbeddings(),
        persist_directory=CHROMA_PATH
    )
    logging.info(f"✅ Saved {len(chunks)} chunks to {CHROMA_PATH}")

def main():
    logging.info("🚀 Starting vector database creation pipeline...")
    documents = load_documents()
    chunks = split_text(documents)
    save_to_chroma(chunks)
    logging.info("🏁 Finished creating vector database.")

if __name__ == "__main__":
    main()

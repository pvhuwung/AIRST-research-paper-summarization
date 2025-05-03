import os
import uuid
import json
import requests

# Ensure torch._classes is initialized to avoid AttributeError in some environments
import torch
import types
if hasattr(torch, "_classes"):
    torch._classes = types.SimpleNamespace()

import streamlit as st
from pathlib import Path

# --- Document Extraction Libraries ---
import fitz  # PyMuPDF for PDF extraction
from docx import Document  # for DOCX extraction

# Importing pdfplumber for improved table extraction
try:
    import pdfplumber
    USE_PDFPLUMBER = True
except ImportError:
    USE_PDFPLUMBER = False

# --- Embedding Model ---
from sentence_transformers import SentenceTransformer

# --- ChromaDB for Vector Storage ---
from chromadb import Client
from chromadb.config import Settings

# ---------- Global Setup ----------
# Directory to save uploaded files
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# File for persistent mapping between original filename and unique filename
PERSISTENCE_FILE = "processed_files.json"

# Initialize the ChromaDB client
chroma_client = Client(Settings())

# Load embedding model
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# ---------- Persistence Functions ----------
def load_processed_files():
    if os.path.exists(PERSISTENCE_FILE):
        with open(PERSISTENCE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_processed_files(mapping):
    with open(PERSISTENCE_FILE, "w") as f:
        json.dump(mapping, f)

# ---------- Helper Functions ----------
def extract_text_from_pdf_pymupdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text

def extract_text_from_pdf(file_path):
    full_text = ""
    if USE_PDFPLUMBER:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    table_text = ""
                    tables = page.extract_tables() or []
                    for table in tables:
                        for row in table:
                            table_text += "\t".join([str(cell) for cell in row if cell]) + "\n"
                    full_text += page_text + "\n" + table_text + "\n"
        except Exception as e:
            st.warning(f"pdfplumber extraction failed: {e}. Falling back to PyMuPDF.")
            full_text = extract_text_from_pdf_pymupdf(file_path)
    else:
        full_text = extract_text_from_pdf_pymupdf(file_path)
    return full_text

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])

def chunk_text_improved(text, max_chunk_chars=1000, overlap_chars=200):
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chunk_chars:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
                overlap = current_chunk[-overlap_chars:] if len(current_chunk) > overlap_chars else current_chunk
                current_chunk = overlap + para + "\n\n"
            else:
                current_chunk = para[:max_chunk_chars]
                chunks.append(current_chunk.strip())
                current_chunk = para[max_chunk_chars:]
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks

def process_file(uploaded_file):
    file_extension = os.path.splitext(uploaded_file.name)[1]
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if file_extension.lower() == ".pdf":
        text = extract_text_from_pdf(file_path)
    elif file_extension.lower() in [".doc", ".docx"]:
        text = extract_text_from_docx(file_path)
    else:
        st.error("Unsupported file type.")
        return None

    if not text.strip():
        st.warning(f"No text could be extracted from {uploaded_file.name}.")
        return None

    chunks = chunk_text_improved(text)
    if not chunks:
        st.warning("The extracted text is empty after chunking.")
        return None

    embeddings = embed_model.encode(chunks).tolist()
    collection = chroma_client.create_collection(name=unique_filename)
    doc_ids = [str(i) for i in range(len(chunks))]
    collection.add(documents=chunks, embeddings=embeddings, ids=doc_ids)
    return unique_filename

def delete_file(unique_filename):
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    try:
        chroma_client.delete_collection(name=unique_filename)
    except Exception as e:
        st.error(f"Error deleting collection: {e}")

def search_documents(query, top_k=5):
    results = []
    try:
        collections = chroma_client.list_collections()
    except Exception as e:
        st.error(f"Failed to list collections: {e}")
        return results

    for col in collections:
        name = col.name
        try:
            coll = chroma_client.get_collection(name=name)
            search_result = coll.query(query_texts=[query], n_results=top_k)
            for doc, distance in zip(search_result["documents"][0], search_result["distances"][0]):
                results.append((name, doc, distance))
        except Exception as e:
            st.error(f"Error querying collection {name}: {e}")
    results.sort(key=lambda x: x[2])
    return results

def call_llm(context, question):
    api_key = st.secrets.get("OPENROUTER_API_KEY")
    if not api_key:
        st.error("OpenRouter API key not provided in secrets.")
        return "API Key Missing"
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": st.secrets.get("SITE_URL", "https://example.com"),
        "X-Title": st.secrets.get("SITE_NAME", "My Site"),
        "Content-Type": "application/json"
    }
    message = (
        "You are an AI assistant that answers questions solely based on the provided context extracted from uploaded research papers. "
        "Answer the following question using only the information available in the context. "
        "If the provided context does not contain sufficient or relevant details to answer the question, "
        "respond exactly with: 'No relevant information found in the provided documents.'\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}"
    )
    data = {"model": "qwen/qwq-32b:free", "messages": [{"role": "user", "content": message}]}
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        try:
            return response.json()["choices"][0]["message"]["content"]
        except Exception:
            return "Error parsing response from LLM."
    return f"Error from API: {response.status_code}, {response.text}"

# ---------- Streamlit Application ----------

def main():
    st.title("AI Research Paper Summarizer")
    st.write("Upload research papers, ask questions, and get answers from relevant document sections.")

    # Load persistent mapping into session state on app start
    if "processed_files" not in st.session_state:
        st.session_state["processed_files"] = load_processed_files()

    # Tabs: File Upload, PDFs/Docs list, and Prompt for Q&A.
    tab_upload, tab_list, tab_prompt, tab_chat = st.tabs(["File Upload", "PDFs/Docs", "Prompt","Upload & Chat"])
    
    with tab_upload:
        st.header("Upload Research Papers")
        uploaded_files = st.file_uploader(
            "Upload PDF or DOCX files", 
            type=["pdf", "doc", "docx"], 
            accept_multiple_files=True
        )
        if uploaded_files:
            for uploaded_file in uploaded_files:
                if uploaded_file.name not in st.session_state["processed_files"]:
                    unique_filename = process_file(uploaded_file)
                    if unique_filename:
                        st.success(f"Uploaded and processed file: {uploaded_file.name}")
                        st.session_state["processed_files"][uploaded_file.name] = unique_filename
                        save_processed_files(st.session_state["processed_files"])
    
    with tab_list:
        st.header("Uploaded Files")
        processed_files = st.session_state.get("processed_files", {})
        if processed_files:
            for original_name, unique_filename in list(processed_files.items()):
                st.write(f"**{original_name}**")
                if st.button(f"Delete {original_name}", key=f"delete_{unique_filename}"):
                    delete_file(unique_filename)
                    st.success(f"Deleted {original_name}")
                    del st.session_state["processed_files"][original_name]
                    save_processed_files(st.session_state["processed_files"])
        else:
            st.info("No files uploaded yet.")
    
    with tab_prompt:
        st.header("Ask a Question")
        query = st.text_input("Enter your question:")
        if st.button("Get Answer"):
            if query:
                search_results = search_documents(query)
                if search_results:
                    context = "\n\n".join([doc for _, doc, _ in search_results[:5]])
                else:
                    context = ""
                if not context:
                    st.error("No relevant content found from uploaded documents. Please check your upload and try a different query.")
                else:
                    answer = call_llm(context, query)
                    st.write("**Answer:**")
                    st.write(answer)
            else:
                st.warning("Please enter a question.")
    with tab_chat:
        st.header("Upload & Chat with PDF")
        chat_uploaded_file = st.file_uploader(
            "Upload a PDF file for summarization and chat (file will not be stored):",
            type=["pdf"]
        )
        if chat_uploaded_file:
            # Extract text from the uploaded PDF
            temp_file_path = os.path.join(UPLOAD_DIR, f"temp_{uuid.uuid4().hex}.pdf")
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(chat_uploaded_file.getbuffer())
            
            # Extract text and summarize
            extracted_text = extract_text_from_pdf(temp_file_path)
            os.remove(temp_file_path)  # Delete the temporary file immediately
            
            if not extracted_text.strip():
                st.warning("No text could be extracted from the uploaded PDF.")
            else:
                st.subheader("Summary")
                chunks = chunk_text_improved(extracted_text)
                summary = " ".join(chunks[:3])  # Summarize using the first few chunks
                st.write(summary)

if __name__ == "__main__":
    main()
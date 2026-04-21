"""
AI Evaluation Factory - Document Ingestion Pipeline
Stage 1: Ingest documents into ChromaDB for RAG system

Usage:
    python data/ingest_docs.py

Output:
    data/vector_db/chroma_db/ - ChromaDB persistence folder
"""

import os
import re
import json
import uuid
from pathlib import Path
from typing import List, Dict, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("[WARNING] sentence-transformers not installed. Run: pip install sentence-transformers")

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("[WARNING] chromadb not installed. Run: pip install chromadb")


# =============================================================================
# DOCUMENT PARSING - Parse 5 source files and extract chunks
# =============================================================================

DOC_CONFIG = {
    "hr_leave_policy.txt": {
        "doc_id": "hr_leave_policy",
        "source": "hr/leave-policy-2026.pdf",
        "department": "HR",
        "sections": [
            {"id": "1.1", "title": "annual_leave", "pattern": r"1\.1\s+Nghỉ phép năm.*?(?=1\.2|\Z)"},
            {"id": "1.2", "title": "sick_leave", "pattern": r"1\.2\s+Nghỉ ốm.*?(?=1\.3|\Z)"},
            {"id": "1.3", "title": "maternity_leave", "pattern": r"1\.3\s+Nghỉ thai sản.*?(?=1\.4|\Z)"},
            {"id": "1.4", "title": "holiday_leave", "pattern": r"1\.4\s+Nghỉ lễ tết.*?(?=Phần 2|\Z)"},
            {"id": "2", "title": "leave_request_process", "pattern": r"Phần 2: Quy trình xin nghỉ phép.*?(?=Phần 3|\Z)"},
            {"id": "3", "title": "overtime_policy", "pattern": r"Phần 3: Chính sách làm thêm giờ.*?(?=Phần 4|\Z)"},
            {"id": "4", "title": "remote_work", "pattern": r"Phần 4: Remote work policy.*?(?=Phần 5|\Z)"},
            {"id": "5", "title": "hr_contact", "pattern": r"Phần 5: Liên hệ HR.*"},
        ]
    },
    "it_helpdesk_faq.txt": {
        "doc_id": "it_helpdesk",
        "source": "support/helpdesk-faq.md",
        "department": "IT",
        "sections": [
            {"id": "1", "title": "account_password", "pattern": r"Section 1:.*?(?=Section 2|\Z)"},
            {"id": "2", "title": "vpn_remote", "pattern": r"Section 2: VPN.*?(?=Section 3|\Z)"},
            {"id": "3", "title": "software_license", "pattern": r"Section 3: Phần mềm.*?(?=Section 4|\Z)"},
            {"id": "4", "title": "hardware_device", "pattern": r"Section 4: Thiết bị.*?(?=Section 5|\Z)"},
            {"id": "5", "title": "email_calendar", "pattern": r"Section 5: Email.*?(?=Section 6|\Z)"},
            {"id": "6", "title": "it_contact", "pattern": r"Section 6: Liên hệ IT.*"},
        ]
    },
    "policy_refund_v4.txt": {
        "doc_id": "policy_refund",
        "source": "policy/refund-v4.pdf",
        "department": "CS",
        "sections": [
            {"id": "1", "title": "scope", "pattern": r"Điều 1:.*?(?=Điều 2|\Z)"},
            {"id": "2", "title": "refund_conditions", "pattern": r"Điều 2:.*?(?=Điều 3|\Z)"},
            {"id": "3", "title": "exceptions", "pattern": r"Điều 3:.*?(?=Điều 4|\Z)"},
            {"id": "4", "title": "process", "pattern": r"Điều 4:.*?(?=Điều 5|\Z)"},
            {"id": "5", "title": "refund_method", "pattern": r"Điều 5:.*?(?=Điều 6|\Z)"},
            {"id": "6", "title": "contact", "pattern": r"Điều 6:.*"},
        ]
    },
    "access_control_sop.txt": {
        "doc_id": "access_control",
        "source": "it/access-control-sop.md",
        "department": "IT Security",
        "sections": [
            {"id": "1", "title": "scope_purpose", "pattern": r"Section 1:.*?(?=Section 2|\Z)"},
            {"id": "2", "title": "access_levels", "pattern": r"Section 2:.*?(?=Section 3|\Z)"},
            {"id": "3", "title": "request_process", "pattern": r"Section 3:.*?(?=Section 4|\Z)"},
            {"id": "4", "title": "escalation", "pattern": r"Section 4:.*?(?=Section 5|\Z)"},
            {"id": "5", "title": "revocation", "pattern": r"Section 5:.*?(?=Section 6|\Z)"},
            {"id": "6", "title": "audit_review", "pattern": r"Section 6:.*?(?=Section 7|\Z)"},
            {"id": "7", "title": "tools", "pattern": r"Section 7:.*"},
        ]
    },
    "sla_p1_2026.txt": {
        "doc_id": "sla_ticket",
        "source": "support/sla-p1-2026.pdf",
        "department": "IT",
        "sections": [
            {"id": "1", "title": "priority_definition", "pattern": r"Phần 1:.*?(?=Phần 2|\Z)"},
            {"id": "2", "title": "sla_by_priority", "pattern": r"Phần 2:.*?(?=Phần 3|\Z)"},
            {"id": "3", "title": "p1_process", "pattern": r"Phần 3:.*?(?=Phần 4|\Z)"},
            {"id": "4", "title": "tools_channels", "pattern": r"Phần 4:.*?(?=Phần 5|\Z)"},
            {"id": "5", "title": "version_history", "pattern": r"Phần 5:.*"},
        ]
    }
}


def parse_document_file(filepath: str, doc_config: Dict) -> List[Dict]:
    """Parse a document file and extract sections as chunks."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    chunks = []
    doc_id = doc_config["doc_id"]

    for section in doc_config["sections"]:
        section_id = section["id"]
        section_title = section["title"]
        pattern = section["pattern"]

        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            section_content = match.group(0).strip()

            # Skip header lines (first 6 lines are metadata)
            lines = section_content.split("\n")
            if len(lines) > 6:
                lines = lines[6:]
            section_content = "\n".join(lines).strip()

            if len(section_content) > 50:  # Skip very short sections
                chunk_id = f"{doc_id}_{section_id}_{section_title}"

                chunk = {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "doc_source": doc_config["source"],
                    "department": doc_config["department"],
                    "section_id": section_id,
                    "section_title": section_title,
                    "content": section_content
                }
                chunks.append(chunk)

    return chunks


def get_all_chunks(docs_dir: str = "data/docs") -> List[Dict]:
    """Parse all documents and return all chunks."""
    all_chunks = []

    for filename, config in DOC_CONFIG.items():
        filepath = os.path.join(docs_dir, filename)
        if os.path.exists(filepath):
            chunks = parse_document_file(filepath, config)
            all_chunks.extend(chunks)
            print(f"[PARSED] {filename}: {len(chunks)} chunks")
        else:
            print(f"[WARNING] File not found: {filepath}")

    return all_chunks


# =============================================================================
# EMBEDDING & CHROMADB
# =============================================================================

def create_embeddings(chunks: List[Dict], model_name: str = "dangvantuan/vietnamese-embedding") -> List[List[float]]:
    """Create embeddings for chunks using sentence-transformers with Vietnamese model."""
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        print("[ERROR] sentence-transformers not available")
        return []

    print(f"[EMBEDDING] Loading model: {model_name}")
    try:
        model = SentenceTransformer(model_name)
    except Exception as e:
        print(f"[WARNING] Could not load {model_name}, falling back to all-MiniLM-L6-v2")
        print(f"[INFO] To use Vietnamese embedding, install: pip install dangvantuan/vietnamese-embedding")
        model = SentenceTransformer("all-MiniLM-L6-v2")

    texts = [chunk["content"] for chunk in chunks]
    print(f"[EMBEDDING] Encoding {len(texts)} chunks with Vietnamese model...")
    embeddings = model.encode(texts, show_progress_bar=True)

    return embeddings.tolist()


def ingest_to_chromadb(chunks: List[Dict], embeddings: List[List[float]],
                       persist_dir: str = "data/vector_db/chroma_db"):
    """Ingest chunks and embeddings into ChromaDB."""
    if not CHROMADB_AVAILABLE:
        print("[ERROR] chromadb not available")
        return None

    os.makedirs(persist_dir, exist_ok=True)

    print(f"[CHROMADB] Creating collection...")
    client = chromadb.PersistentClient(path=persist_dir)

    # Delete existing collection if exists
    try:
        client.delete_collection("evaluation_docs")
    except:
        pass

    collection = client.create_collection(name="evaluation_docs", metadata={"description": "AI Evaluation Factory documents"})

    # Prepare data for ChromaDB
    ids = [chunk["chunk_id"] for chunk in chunks]
    documents = [chunk["content"] for chunk in chunks]
    metadatas = [
        {
            "doc_id": chunk["doc_id"],
            "doc_source": chunk["doc_source"],
            "department": chunk["department"],
            "section_id": chunk["section_id"],
            "section_title": chunk["section_title"]
        }
        for chunk in chunks
    ]

    print(f"[CHROMADB] Adding {len(chunks)} chunks...")
    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print(f"[CHROMADB] Persisted to: {persist_dir}")
    return collection


def save_chunk_metadata(chunks: List[Dict], output_path: str = "data/chunks_metadata.json"):
    """Save chunk metadata for later reference in SDG."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"[METADATA] Saved to: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 70)
    print("AI EVALUATION FACTORY - DOCUMENT INGESTION PIPELINE")
    print("Stage 1: Ingest documents into ChromaDB")
    print("=" * 70)

    # Step 1: Parse documents
    print("\n[STEP 1] Parsing documents...")
    chunks = get_all_chunks("data/docs")
    print(f"[TOTAL] {len(chunks)} chunks extracted")

    # Step 2: Create embeddings
    print("\n[STEP 2] Creating embeddings...")
    if SENTENCE_TRANSFORMERS_AVAILABLE:
        # Get embedding model from env or use default Vietnamese model
        embedding_model = os.getenv("EMBEDDING_MODEL", "dangvantuan/vietnamese-embedding")
        embeddings = create_embeddings(chunks, model_name=embedding_model)
    else:
        print("[ERROR] Cannot create embeddings without sentence-transformers")
        return

    # Step 3: Ingest to ChromaDB
    print("\n[STEP 3] Ingesting to ChromaDB...")
    collection = ingest_to_chromadb(chunks, embeddings)

    # Step 4: Save metadata
    print("\n[STEP 4] Saving chunk metadata...")
    save_chunk_metadata(chunks)

    # Verify
    print("\n[VERIFY] Collection count:", collection.count())

    print("\n" + "=" * 70)
    print("DOCUMENT INGESTION COMPLETE!")
    print("Next step: python data/synthetic_gen.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
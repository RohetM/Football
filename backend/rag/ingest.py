"""Ingestion script to populate ChromaDB vector database.

Reads markdown files from the knowledge base, splits them into semantic chunks
by heading/paragraph, computes embeddings locally using sentence-transformers,
and stores them in a persistent ChromaDB database.
"""

import os
import re
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

# Configurable paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
KB_DIR = os.getenv(
    "KNOWLEDGE_BASE_DIR", os.path.join(BASE_DIR, "data", "knowledge_base")
)
DB_DIR = os.getenv("CHROMA_DB_DIR", os.path.join(BASE_DIR, "data", "chroma_db"))
COLLECTION_NAME = "worldcup_kb"


def parse_markdown_to_sections(file_path: str) -> list[dict[str, str]]:
    """Parse markdown file and split it into sections based on headings.

    Args:
        file_path: Path to the markdown file.

    Returns:
        List[Dict[str, str]]: List of dictionaries containing section headers and text content.
    """
    if not os.path.exists(file_path):
        print(f"Warning: file {file_path} does not exist.")
        return []

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    file_name = os.path.basename(file_path)
    sections = []

    # Split contents by level 2 headings: '## '
    # This aligns perfectly with FAQ and Gate items
    parts = re.split(r"\n(##\s+)", content)

    # The first element contains introduction/title or Level 1 header
    intro = parts[0].strip()
    if intro:
        sections.append(
            {"source": file_name, "header": "Introduction", "content": intro}
        )

    # Group the matching headers and contents
    i = 1
    while i < len(parts):
        header_marker = parts[i]  # e.g., '## '
        header_and_body = parts[i + 1] if i + 1 < len(parts) else ""

        # Split header line from body
        header_lines = header_and_body.split("\n", 1)
        header = header_lines[0].strip()
        body = header_lines[1].strip() if len(header_lines) > 1 else ""

        sections.append(
            {"source": file_name, "header": header, "content": f"## {header}\n{body}"}
        )
        i += 2

    return sections


def build_vector_db(kb_dir: str = KB_DIR, db_dir: str = DB_DIR) -> None:
    """Build or rebuild local ChromaDB vector database from knowledge base docs.

    Args:
        kb_dir: Path to raw knowledge base markdown files.
        db_dir: Path to save the ChromaDB database files.
    """
    print(f"Initializing ChromaDB persistent client at: {db_dir}")
    client = chromadb.PersistentClient(path=db_dir)

    # Use local SentenceTransformers embedding function
    print("Loading local sentence-transformers model (all-MiniLM-L6-v2)...")
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    # Get or create collection
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME, embedding_function=emb_fn
    )

    # Clear existing documents in collection
    existing_count = collection.count()
    if existing_count > 0:
        print(f"Clearing {existing_count} existing items from vector database...")
        # Since we use simple client, we can delete by ids or recreate collection
        client.delete_collection(name=COLLECTION_NAME)
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=emb_fn
        )

    # Gather knowledge base files
    md_files = (
        [f for f in os.listdir(kb_dir) if f.endswith((".md", ".txt"))]
        if os.path.exists(kb_dir)
        else []
    )

    if not md_files:
        print(f"No knowledge base files found in: {kb_dir}")
        return

    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []
    ids: list[str] = []
    counter = 0

    for file_name in md_files:
        full_path = os.path.join(kb_dir, file_name)
        print(f"Parsing {file_name}...")
        sections = parse_markdown_to_sections(full_path)

        for sec in sections:
            if not sec["content"].strip():
                continue
            documents.append(sec["content"])
            metadatas.append({"source": sec["source"], "header": sec["header"]})
            ids.append(f"doc_{counter}")
            counter += 1

    if documents:
        print(f"Adding {len(documents)} document chunks to vector database...")
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print("Ingestion completed successfully.")
    else:
        print("No content chunks found to ingest.")


if __name__ == "__main__":
    build_vector_db()

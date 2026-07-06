"""Tests for RAG ingestion and retrieval logic."""

import os
from backend.rag.ingest import parse_markdown_to_sections, build_vector_db
from backend.rag.retriever import RAGRetriever


def test_parse_markdown_to_sections(tmp_path):
    """Test parsing markdown headings and body content."""
    md_content = """# Test Document

## Section A
This is the description for Section A.
It has multiple lines.

## Section B
And this is section B content.
"""
    test_file = tmp_path / "test_doc.md"
    test_file.write_text(md_content, encoding="utf-8")

    sections = parse_markdown_to_sections(str(test_file))

    assert len(sections) == 3
    assert sections[0]["header"] == "Introduction"
    assert "Test Document" in sections[0]["content"]

    assert sections[1]["header"] == "Section A"
    assert "Section A" in sections[1]["content"]
    assert "description for Section A" in sections[1]["content"]

    assert sections[2]["header"] == "Section B"
    assert "Section B" in sections[2]["content"]


def test_build_vector_db_and_retrieve(tmp_path):
    """Test full RAG pipeline: ingestion followed by context query retrieval."""
    # Create temp knowledge base directory and files
    kb_dir = tmp_path / "kb"
    db_dir = tmp_path / "db"
    kb_dir.mkdir()
    db_dir.mkdir()

    md_content = """# Stadium Policy

## Ticket Rules
All guests must present a valid match ticket. Children under 2 get free entry.

## Bag Limits
Only clear bags smaller than 12x12 inches are allowed inside the gates.
"""
    faq_file = kb_dir / "policy.md"
    faq_file.write_text(md_content, encoding="utf-8")

    # Run ingestion
    build_vector_db(kb_dir=str(kb_dir), db_dir=str(db_dir))

    # Test retriever
    retriever = RAGRetriever(db_dir=str(db_dir))
    
    # Check ticket rules query
    results = retriever.retrieve("Can I bring my child without ticket?", n_results=1)
    assert len(results) == 1
    assert "Ticket Rules" in results[0]["header"]
    assert "Children under 2 get free entry" in results[0]["content"]

    # Check bag rules query
    results = retriever.retrieve("What bag size is permitted?", n_results=1)
    assert len(results) == 1
    assert "Bag Limits" in results[0]["header"]
    assert "clear bags smaller than 12x12" in results[0]["content"]

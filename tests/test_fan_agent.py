"""Tests for backend/agents/fan_agent.py."""

import json
from unittest.mock import patch
from backend.agents.fan_agent import format_context, query_fan_agent


def test_format_context():
    """Test standard formatting of list of context documents."""
    docs = [
        {"source": "faq.md", "header": "Bag Limits", "content": "Only clear bags allowed"},
        {"source": "gate_info.md", "header": "Gate C", "content": "Gate C is ramp-free"}
    ]
    formatted = format_context(docs)
    assert "Source: faq.md | Section: Bag Limits" in formatted
    assert "Only clear bags allowed" in formatted
    assert "Gate C is ramp-free" in formatted


def test_format_context_empty():
    """Test format_context handles empty inputs gracefully."""
    assert format_context([]) == "No relevant context found in database."


@patch("backend.agents.fan_agent.retrieve_context")
@patch("backend.agents.fan_agent.call_llm")
def test_query_fan_agent_success(mock_call_llm, mock_retrieve_context):
    """Test query_fan_agent parses LLM response and structure successfully."""
    # Mock RAG retriever output
    mock_retrieve_context.return_value = [
        {"source": "faq.md", "header": "Match Day", "content": "Gates open at 5 PM"}
    ]

    # Mock LLM return value
    mock_llm_json = {
        "response": "Les portes ouvrent à 17h00.",
        "reasoning": "Retrieved match day info from faq.md."
    }
    mock_call_llm.return_value = (json.dumps(mock_llm_json), "Groq API call trace")

    result = query_fan_agent("What time do gates open?", language="fr")
    
    assert result["response"] == "Les portes ouvrent à 17h00."
    assert "Retrieved match day info" in result["reasoning"]
    assert "Groq API call trace" in result["reasoning"]
    assert "faq.md -> Match Day" in result["sources"]


@patch("backend.agents.fan_agent.retrieve_context")
@patch("backend.agents.fan_agent.call_llm")
def test_query_fan_agent_failure(mock_call_llm, mock_retrieve_context):
    """Test query_fan_agent returns fallback response when LLM fails."""
    mock_retrieve_context.return_value = []
    mock_call_llm.side_effect = Exception("API Error")

    result = query_fan_agent("What is the bag policy?")
    
    assert "technical difficulties" in result["response"]
    assert "API Error" in result["reasoning"]

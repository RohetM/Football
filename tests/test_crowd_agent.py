"""Tests for backend/agents/crowd_agent.py."""

import json
from unittest.mock import patch, mock_open
from backend.agents.crowd_agent import query_crowd_agent, load_stadium_state


def test_load_stadium_state_not_found():
    """Test loading a non-existent state file."""
    assert load_stadium_state("invalid_file_path.json") == "{}"


@patch("builtins.open", new_callable=mock_open, read_data='{"key": "value"}')
@patch("os.path.exists")
def test_load_stadium_state_success(mock_exists, mock_file):
    """Test loading a valid state file."""
    mock_exists.return_value = True
    content = load_stadium_state("stadium_state.json")
    assert "value" in content
    mock_file.assert_called_once_with("stadium_state.json", encoding="utf-8")


@patch("backend.agents.crowd_agent.load_stadium_state")
@patch("backend.agents.crowd_agent.call_llm")
def test_query_crowd_agent_success(mock_call_llm, mock_load_state):
    """Test query_crowd_agent returns structured output correctly."""
    mock_load_state.return_value = '{"gates": {"Gate_A": {"wait_time_minutes": 55}}}'
    
    mock_llm_json = {
        "issue": "Severe congestion at Gate A",
        "eta_minutes": 15,
        "recommended_action": "Redirect fans to Gate C",
        "confidence": "HIGH",
        "reasoning": "Gate A wait times are 55 minutes."
    }
    mock_call_llm.return_value = (json.dumps(mock_llm_json), "Groq trace")

    result = query_crowd_agent(file_path="mock_path.json")

    assert result["issue"] == "Severe congestion at Gate A"
    assert result["eta_minutes"] == 15
    assert result["recommended_action"] == "Redirect fans to Gate C"
    assert result["confidence"] == "HIGH"
    assert "Gate A wait times" in result["reasoning"]
    assert "Groq trace" in result["reasoning"]


@patch("backend.agents.crowd_agent.load_stadium_state")
@patch("backend.agents.crowd_agent.call_llm")
def test_query_crowd_agent_failure(mock_call_llm, mock_load_state):
    """Test query_crowd_agent returns safe fallback dictionary on LLM failure."""
    mock_load_state.return_value = '{"gates": {}}'
    mock_call_llm.side_effect = Exception("Groq Rate Limit")

    result = query_crowd_agent(file_path="mock_path.json")

    assert "Unable to parse operational data stream" in result["issue"]
    assert result["confidence"] == "LOW"
    assert "manual crowd monitoring" in result["recommended_action"]

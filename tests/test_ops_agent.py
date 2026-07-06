"""Tests for backend/agents/ops_agent.py."""

import json
from unittest.mock import patch, mock_open
from backend.agents.ops_agent import (
    compute_manhattan_distance,
    get_nearest_volunteer,
    query_ops_agent,
)


def test_compute_manhattan_distance():
    """Test Manhattan grid calculations on fixed locations."""
    # Gate A: (0, 10), North Plaza: (0, 8) -> distance = |0-0| + |10-8| = 2
    assert compute_manhattan_distance("Gate_A", "North_Plaza") == 2
    
    # Gate A: (0, 10), Gate B: (0, -10) -> distance = |0-0| + |10 - (-10)| = 20
    assert compute_manhattan_distance("Gate_A", "Gate_B") == 20

    # Unknown locations
    assert compute_manhattan_distance("Gate_A", "Unknown_Location") == 999


def test_get_nearest_volunteer():
    """Test nearest volunteer selection algorithm."""
    volunteers = [
        {"id": "V1", "name": "Elena", "location": "Gate_C", "status": "BUSY"},     # Gate C is (10, 0)
        {"id": "V2", "name": "Marcus", "location": "South_Plaza", "status": "IDLE"}, # South Plaza is (0, -8)
        {"id": "V3", "name": "Amina", "location": "Gate_A", "status": "IDLE"}       # Gate A is (0, 10)
    ]
    
    # Incident at North Plaza (0, 8). 
    # Distance to Gate A (V3): 2 (IDLE)
    # Distance to South Plaza (V2): 16 (IDLE)
    # Distance to Gate C (V1): 18 (BUSY)
    
    nearest, calculated = get_nearest_volunteer("North_Plaza", volunteers)
    assert nearest is not None
    assert nearest["id"] == "V3"
    assert nearest["distance"] == 2
    
    # Verify calculated list includes distances
    distances = {v["id"]: v["distance"] for v in calculated}
    assert distances["V1"] == 18
    assert distances["V2"] == 16
    assert distances["V3"] == 2


def test_get_nearest_volunteer_all_busy():
    """Test fallback when all volunteers are busy."""
    volunteers = [
        {"id": "V1", "name": "Elena", "location": "Gate_C", "status": "BUSY"},     # Gate C (10, 0)
        {"id": "V2", "name": "Marcus", "location": "Gate_A", "status": "BUSY"}      # Gate A (0, 10)
    ]
    
    # Incident at North Plaza (0, 8). Both busy. 
    # Nearest should still return V2 (distance = 2) since it's the closest overall.
    nearest, calculated = get_nearest_volunteer("North_Plaza", volunteers)
    assert nearest is not None
    assert nearest["id"] == "V2"


@patch("builtins.open", new_callable=mock_open)
@patch("os.path.exists")
@patch("backend.agents.ops_agent.call_llm")
def test_query_ops_agent_success(mock_call_llm, mock_exists, mock_file):
    """Test full query_ops_agent logic on success."""
    mock_exists.return_value = True
    
    # Mock stadium_state.json contents
    state_data = {
        "volunteers": [
            {"id": "V1", "name": "Yuki", "location": "Gate_A", "status": "IDLE"}
        ]
    }
    mock_file.return_value.read.return_value = json.dumps(state_data)

    mock_llm_json = {
        "recommendation": "Yuki Tanaka go to Gate A",
        "assigned_volunteer_id": "V1",
        "reasoning": "Yuki is at Gate A and idle."
    }
    mock_call_llm.return_value = (json.dumps(mock_llm_json), "Groq trace")

    result = query_ops_agent(
        incident_description="Wheelchair transfer needed",
        incident_type="accessibility",
        incident_location="Gate_A",
        file_path="mock_state.json"
    )

    assert result["assigned_volunteer_id"] == "V1"
    assert result["recommendation"] == "Yuki Tanaka go to Gate A"
    assert "Yuki is at Gate A" in result["reasoning"]
    assert "Groq trace" in result["reasoning"]


@patch("os.path.exists")
@patch("backend.agents.ops_agent.call_llm")
def test_query_ops_agent_failure(mock_call_llm, mock_exists):
    """Test full query_ops_agent returns proper programmatic fallback on error."""
    mock_exists.return_value = False  # triggers empty volunteers
    mock_call_llm.side_effect = Exception("API Error")

    result = query_ops_agent(
        incident_description="Lost child near West Gate",
        incident_type="security",
        incident_location="West_Concourse"
    )

    assert result["assigned_volunteer_id"] is None
    assert "Command Room" in result["recommendation"]
    assert "fallback" in result["reasoning"]

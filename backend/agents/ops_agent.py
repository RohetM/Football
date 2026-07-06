"""Ops Agent module.

Manages incident response and volunteer dispatch. Computes spatial distances
between stadium zones, finds the nearest idle volunteer, and uses the LLM to
generate a dispatch recommendation and reasoning trace.
"""

import json
import os
from typing import Any

from backend.agents.llm import call_llm

DEFAULT_STATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "stadium_state.json"
)

# Coordinates for simple distance calculations on a grid representing the stadium layout
ZONE_COORDINATES = {
    "Gate_A": (0, 10),
    "North_Plaza": (0, 8),
    "Gate_B": (0, -10),
    "South_Plaza": (0, -8),
    "Gate_C": (10, 0),
    "East_Concourse": (8, 0),
    "Gate_D": (-10, 0),
    "West_Concourse": (-8, 0),
}

SYSTEM_PROMPT = """You are the Ops Agent for "WorldCup OS," a GenAI tournament operations co-pilot.

Your role is to formulate dispatch recommendations for security, medical, and accessibility incidents at the stadium.

You will be given:
1. Incident Details (description, type, location).
2. Computed Distance Analysis (distance from incident location to each volunteer).
3. Complete Volunteer List (IDs, names, locations, statuses).

Guidelines:
1. Verify the recommended volunteer is indeed IDLE and closest. If no volunteers are IDLE, recommend the closest BUSY volunteer or manual escalation.
2. Draft a clear dispatch notification message to send to the volunteer's mobile app.
3. You MUST respond in a JSON format with exactly three keys:
   - "recommendation": A clear command instructing the steward/volunteer on what to do.
   - "assigned_volunteer_id": The ID of the chosen volunteer (or null if none could be assigned).
   - "reasoning": A 1-2 sentence explanation of why they were chosen (mentioning location, status, and computed distance).

JSON format:
{
  "recommendation": "...",
  "assigned_volunteer_id": "...",
  "reasoning": "..."
}
"""


def compute_manhattan_distance(loc1: str, loc2: str) -> int:
    """Calculate Manhattan distance between two stadium zones.

    If zone is unknown, returns a high penalty distance.

    Args:
        loc1: First location name.
        loc2: Second location name.

    Returns:
        int: Grid distance.
    """
    coord1 = ZONE_COORDINATES.get(loc1)
    coord2 = ZONE_COORDINATES.get(loc2)
    if not coord1 or not coord2:
        return 999  # Penalty distance for unknown locations
    return abs(coord1[0] - coord2[0]) + abs(coord1[1] - coord2[1])


def get_nearest_volunteer(
    incident_location: str, volunteers: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Find the nearest idle volunteer and calculate distances for all volunteers.

    Args:
        incident_location: Zone where the incident occurred.
        volunteers: List of volunteers from the state file.

    Returns:
        tuple: (nearest_idle_volunteer_or_none, list_of_volunteers_with_computed_distances)
    """
    calculated_list = []
    for vol in volunteers:
        dist = compute_manhattan_distance(vol["location"], incident_location)
        vol_info = vol.copy()
        vol_info["distance"] = dist
        calculated_list.append(vol_info)

    # Filter for IDLE volunteers first
    idle_volunteers = [v for v in calculated_list if v["status"] == "IDLE"]

    # Sort idle volunteers by distance
    if idle_volunteers:
        idle_volunteers.sort(key=lambda x: x["distance"])
        nearest = idle_volunteers[0]
    else:
        # Fallback to closest busy volunteer if none are idle
        sorted_all = sorted(calculated_list, key=lambda x: x["distance"])
        nearest = sorted_all[0] if sorted_all else None

    return nearest, calculated_list


def query_ops_agent(
    incident_description: str,
    incident_type: str,
    incident_location: str,
    file_path: str = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    """Process an incident and generate LLM-guided volunteer dispatch recommendations.

    Args:
        incident_description: Description of what happened.
        incident_type: Category (e.g. medical, security, accessibility).
        incident_location: Zone/Gate where incident is active.
        file_path: Optional path to state JSON.

    Returns:
        Dict[str, Any]: Recommendation, assigned volunteer id, and reasoning.
    """
    # 1. Load volunteers from the simulated state
    volunteers = []
    if os.path.exists(file_path):
        try:
            with open(file_path, encoding="utf-8") as f:
                state = json.load(f)
                volunteers = state.get("volunteers", [])
        except Exception as e:
            print(f"Error loading state in Ops Agent: {e}")

    # 2. Heuristically calculate nearest volunteer
    nearest, calculated_list = get_nearest_volunteer(incident_location, volunteers)

    # 3. Create LLM user prompt
    user_prompt = {
        "incident": {
            "description": incident_description,
            "type": incident_type,
            "location": incident_location,
        },
        "nearest_computed_volunteer": nearest,
        "all_volunteers_analysis": calculated_list,
    }

    # 4. Invoke LLM in JSON mode
    try:
        response_text, raw_trace = call_llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=json.dumps(user_prompt),
            json_mode=True,
        )

        dispatch_decision = json.loads(response_text)

        # Append LLM execution trace to reasoning
        dispatch_decision["reasoning"] = (
            f"{dispatch_decision.get('reasoning', '')} {raw_trace}"
        )
        return dispatch_decision

    except Exception as e:
        print(f"Error in Ops Agent: {e}")
        # Programmatic fallback
        if nearest:
            return {
                "recommendation": f"STeward/Volunteer {nearest['name']} ({nearest['id']}) report to {incident_location} for {incident_type} assistance immediately.",
                "assigned_volunteer_id": nearest["id"],
                "reasoning": f"Programmatic fallback dispatch due to LLM error: {str(e)}",
            }
        else:
            return {
                "recommendation": "No volunteers available. Escalate to Stadium Command Room.",
                "assigned_volunteer_id": None,
                "reasoning": f"Programmatic fallback. No volunteers found in state. LLM error: {str(e)}",
            }

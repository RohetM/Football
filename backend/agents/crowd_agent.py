"""Crowd Intel Agent module.

Reads simulated live stadium state (wait times, transit delays, plaza density),
reasons using the LLM about crowd flow, and returns structured bottleneck
analysis and operational recommendations.
"""

import json
import os
from typing import Any

from backend.agents.llm import call_llm

DEFAULT_STATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "stadium_state.json"
)

SYSTEM_PROMPT = """You are the Crowd Intel Agent for "WorldCup OS," a GenAI tournament operations co-pilot.

You analyze the live operational state of a FIFA World Cup stadium, which includes gate status and wait times, public transit delay metrics, plaza capacity utilization, and weather.

Your job is to identify the single most critical active or developing crowd bottleneck and suggest real-time mitigation actions for stadium staff.

Guidelines:
1. Examine all metrics:
   - "CRITICAL" plaza crowd levels (utilization > 80%).
   - Long wait times at gates (> 30 minutes).
   - "DELAYED" transit lines.
2. Recommend concrete actions (e.g., "Open Gate C to general admission," "Update signage in North Plaza to direct fans to Concourse West," "Deploy shuttles to alleviate Metro Line 1 delay").
3. You MUST return a structured JSON response with these keys:
   - "issue": Description of the bottleneck or transit failure.
   - "eta_minutes": Estimated time (integer) for the bottleneck to peak or duration of the transit delay.
   - "recommended_action": Concrete mitigation steps for stadium stewards.
   - "confidence": String ("HIGH", "MEDIUM", or "LOW").
   - "reasoning": Short explanation of how you derived this (mentioning wait times, plazas, or transit lines).

JSON format:
{
  "issue": "...",
  "eta_minutes": 10,
  "recommended_action": "...",
  "confidence": "HIGH",
  "reasoning": "..."
}
"""


def load_stadium_state(file_path: str = DEFAULT_STATE_PATH) -> str:
    """Load the stadium state JSON file as a string.

    Args:
        file_path: Path to the stadium state JSON file.

    Returns:
        str: JSON string content of the state file.
    """
    if not os.path.exists(file_path):
        return "{}"
    with open(file_path, encoding="utf-8") as f:
        return f.read()


def query_crowd_agent(file_path: str = DEFAULT_STATE_PATH) -> dict[str, Any]:
    """Analyze stadium state and predict crowd bottlenecks using the LLM.

    Args:
        file_path: Optional path to the state JSON.

    Returns:
        Dict[str, Any]: Structured crowd analysis results.
    """
    # 1. Load the live simulated state
    state_str = load_stadium_state(file_path)

    # 2. Formulate prompt
    user_prompt = f"Current Stadium State:\n{state_str}"

    # 3. Call LLM
    try:
        response_text, raw_trace = call_llm(
            system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, json_mode=True
        )

        # 4. Parse output
        analysis = json.loads(response_text)

        # Append LLM execution trace to the reasoning field for frontend transparency
        analysis["reasoning"] = f"{analysis.get('reasoning', '')} {raw_trace}"
        return analysis

    except Exception as e:
        print(f"Error in Crowd Intel Agent: {e}")
        return {
            "issue": "Unable to parse operational data stream.",
            "eta_minutes": 0,
            "recommended_action": "Initiate manual crowd monitoring and physical patrols.",
            "confidence": "LOW",
            "reasoning": f"Crowd Intel Agent exception: {str(e)}",
        }

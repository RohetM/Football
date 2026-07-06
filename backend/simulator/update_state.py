"""Simulator script to update stadium operational state.

Simulates dynamic wait times, transit delays, crowd density levels, and updates
the stadium_state.json file on a regular interval or per-call basis.
"""

import json
import os
import random
from datetime import datetime
from typing import Any

# Target state file path
DEFAULT_STATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "stadium_state.json"
)


def load_state(file_path: str = DEFAULT_STATE_PATH) -> dict[str, Any]:
    """Load the current state from JSON file.

    Args:
        file_path: Path to the JSON state file.

    Returns:
        Dict: Current stadium state.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"State file not found at: {file_path}")
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict[str, Any], file_path: str = DEFAULT_STATE_PATH) -> None:
    """Save the updated state to JSON file.

    Args:
        state: The updated state dictionary.
        file_path: Path to write the JSON state file.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def mutate_state(state: dict[str, Any]) -> dict[str, Any]:
    """Mutate stadium state data to simulate active game day changes.

    Args:
        state: Current state dictionary.

    Returns:
        Dict: Updated state dictionary.
    """
    # 1. Update timestamp
    state["last_updated"] = datetime.now().isoformat()

    # 2. Mutate gates
    for gate_name, gate_info in state.get("gates", {}).items():
        if gate_info["status"] == "OPEN":
            # Add or subtract wait time (keep between 5 and 60 minutes)
            wait_delta = random.choice([-3, -2, -1, 0, 1, 2, 3, 4])
            current_wait = gate_info["wait_time_minutes"]
            gate_info["wait_time_minutes"] = max(5, min(65, current_wait + wait_delta))

            # Security wait time correlates with wait time
            sec_delta = random.choice([-2, -1, 0, 1, 2])
            current_sec = gate_info["security_wait_time_minutes"]
            gate_info["security_wait_time_minutes"] = max(
                3, min(45, current_sec + sec_delta)
            )

            # Recalculate capacity utilization based on wait times
            gate_info["capacity_utilization"] = round(
                gate_info["wait_time_minutes"] / 70.0, 2
            )

    # 3. Mutate transit
    for line, info in state.get("transit", {}).items():
        if info["status"] == "DELAYED":
            # Probability of delay resolving
            if random.random() < 0.15:
                info["status"] = "NORMAL"
                info["delay_minutes"] = 0
                info["description"] = "Running on time"
            else:
                # Delay fluctuates
                info["delay_minutes"] = max(
                    5, info["delay_minutes"] + random.choice([-2, 0, 3])
                )
        else:
            # Probability of new delay
            if random.random() < 0.05:
                info["status"] = "DELAYED"
                info["delay_minutes"] = random.choice([10, 15, 20])
                info["description"] = "Delays due to passenger congestion"

    # 4. Mutate plazas
    for plaza, info in state.get("plazas", {}).items():
        cap = info["capacity_utilization"]
        delta = random.choice([-0.05, -0.02, 0.0, 0.02, 0.05])
        new_cap = max(0.1, min(0.98, cap + delta))
        info["capacity_utilization"] = round(new_cap, 2)

        if new_cap > 0.8:
            info["crowd_density_level"] = "CRITICAL"
        elif new_cap > 0.6:
            info["crowd_density_level"] = "WARNING"
        else:
            info["crowd_density_level"] = "NORMAL"

    # 5. Mutate weather temperature slightly
    temp = state.get("weather", {}).get("temperature_c", 24)
    state["weather"]["temperature_c"] = max(
        15, min(38, temp + random.choice([-1, 0, 1]))
    )

    # 6. Randomly assign volunteer status if idle to busy or vice-versa
    for volunteer in state.get("volunteers", []):
        if volunteer["status"] == "IDLE" and random.random() < 0.1:
            volunteer["status"] = "BUSY"
        elif volunteer["status"] == "BUSY" and random.random() < 0.15:
            # If they are busy but incident was assigned, check if we resolve it
            volunteer["status"] = "IDLE"

    return state


def run_simulator_once(file_path: str = DEFAULT_STATE_PATH) -> None:
    """Run a single mutation pass and save to disk."""
    try:
        state = load_state(file_path)
        updated_state = mutate_state(state)
        save_state(updated_state, file_path)
        print(f"Simulator successfully mutated state in: {file_path}")
    except Exception as e:
        print(f"Error in running simulator: {e}")


if __name__ == "__main__":
    import time

    print("Starting continuous stadium state simulator (Ctrl+C to stop)...")
    while True:
        run_simulator_once()
        time.sleep(5)

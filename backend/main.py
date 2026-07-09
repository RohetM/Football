"""FastAPI central orchestrator for WorldCup OS.

Exposes endpoints for the Fan, Crowd, and Ops Agents, handles input validation,
CORS, slowapi rate limiting, and simulation ticks.
"""

import json
import logging
import os
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.agents.crowd_agent import query_crowd_agent
from backend.agents.fan_agent import query_fan_agent
from backend.agents.ops_agent import query_ops_agent

# Import validators and agents
from backend.security.validators import validate_query
from backend.simulator.update_state import load_state, run_simulator_once

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize slowapi limiter
limiter: Limiter = Limiter(key_func=get_remote_address)

app: FastAPI = FastAPI(
    title="WorldCup OS Orchestrator API",
    description="GenAI stadium operations co-pilot backend",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
# Restricted to the Streamlit local frontend origin by default,
# customizable via environment variables.
cors_origins_raw: str = os.getenv(
    "CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501"
)
CORS_ORIGINS: list[str] = [
    origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom In-Memory Rate Limiting for security to prevent API flooding.
# Map of IP to list of request timestamps.
RATE_LIMIT_TIMESTAMPS: dict[str, list[float]] = {}
RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))


def check_rate_limit(ip: str) -> bool:
    """Evaluate rate limit of incoming request source IP.

    Args:
        ip (str): Client source IP address.

    Returns:
        bool: True if request is within limits, False if rate-limited.
    """
    now: float = time.time()
    if ip not in RATE_LIMIT_TIMESTAMPS:
        RATE_LIMIT_TIMESTAMPS[ip] = [now]
        return True

    # Filter timestamps to keep only those within the last 60 seconds
    timestamps: list[float] = [
        t for t in RATE_LIMIT_TIMESTAMPS[ip] if now - t < 60
    ]
    RATE_LIMIT_TIMESTAMPS[ip] = timestamps

    if len(timestamps) >= RATE_LIMIT_PER_MINUTE:
        return False

    RATE_LIMIT_TIMESTAMPS[ip].append(now)
    return True


# Pydantic request models
class FanQueryRequest(BaseModel):
    """Pydantic model representing a fan query request payload.

    Attributes:
        query (str): The fan question text.
        language (str): Target response ISO language code.
        accessibility_needs (str | None): Special accessibility parameters.
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="The fan question text.",
    )
    language: str = Field(
        default="en",
        min_length=1,
        max_length=100,
        description="Target response ISO language code.",
    )
    accessibility_needs: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Special accessibility parameters.",
    )


class OpsActionRequest(BaseModel):
    """Pydantic model representing an operations action request payload.

    Attributes:
        description (str): Description of the incident.
        type (str): Type/category of the incident.
        location (str): Target stadium zone/gate.
    """

    description: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Description of the incident.",
    )
    type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Type/category of the incident (medical, security, accessibility).",
    )
    location: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Target stadium zone/gate.",
    )


@app.post("/api/fan-query", response_model=dict[str, Any])
@limiter.limit("20/minute")
async def handle_fan_query(
    request: Request, body: FanQueryRequest
) -> dict[str, Any]:
    """Secure endpoint for fan FAQs and accessibility assistance.

    Applies rate limiting, validates text input structure, and routes to Fan Agent.

    Args:
        request (Request): The incoming FastAPI request context containing
            client details.
        body (FanQueryRequest): The Pydantic request body containing query
            details.

    Returns:
        dict[str, Any]: The fan query response from the Fan Agent.

    Raises:
        HTTPException: If the rate limit is exceeded or the query is invalid.
    """
    # 1. Apply rate limit check
    client_ip: str = request.client.host if request.client else "127.0.0.1"
    if not check_rate_limit(client_ip):
        logger.warning(
            "Rate limit exceeded for IP: %s (limit: %d/min)",
            client_ip,
            RATE_LIMIT_PER_MINUTE,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again in a minute.",
        )

    # 2. Validate input text (length, injections)
    is_valid, sanitized_text, error_msg = validate_query(body.query)
    if not is_valid:
        logger.warning(
            "Input validation failed for query from IP %s: %s",
            client_ip,
            error_msg,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
        )

    # 3. Route request to Fan Agent
    result: dict[str, Any] = query_fan_agent(
        query=sanitized_text,
        language=body.language,
        accessibility_needs=body.accessibility_needs,
    )
    return result


@app.get("/api/crowd-predict", response_model=dict[str, Any])
async def handle_crowd_predict() -> dict[str, Any]:
    """Predictive crowd bottlenecks endpoint.

    Reads simulated game state and invokes Crowd Intel Agent.

    Returns:
        dict[str, Any]: The crowd predictive analysis results.
    """
    result: dict[str, Any] = query_crowd_agent()
    return result


@app.post("/api/ops-action", response_model=dict[str, Any])
async def handle_ops_action(body: OpsActionRequest) -> dict[str, Any]:
    """Operations incident report and volunteer dispatch router.

    Validates incident location and runs nearest-neighbor volunteer assignment.

    Args:
        body (OpsActionRequest): The Pydantic request body containing incident details.

    Returns:
        dict[str, Any]: The volunteer assignment recommendation results.

    Raises:
        HTTPException: If validation fails or incident description is empty.
    """
    # Basic input check
    if not body.description.strip():
        logger.warning("Ops action rejected: Description contains only whitespace.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incident description cannot be empty.",
        )

    # Hardened input check (safety validation)
    is_valid, sanitized_desc, error_msg = validate_query(body.description)
    if not is_valid:
        logger.warning("Ops action input validation failed: %s", error_msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
        )

    result: dict[str, Any] = query_ops_agent(
        incident_description=sanitized_desc,
        incident_type=body.type,
        incident_location=body.location,
    )
    return result


@app.get("/api/stadium-state", response_model=dict[str, Any])
async def get_stadium_state() -> dict[str, Any]:
    """Fetch current raw simulated stadium operational data.

    Returns:
        dict[str, Any]: A dictionary containing the current simulated stadium state.

    Raises:
        HTTPException: 500 if an error occurs reading the stadium state.
    """
    try:
        state: dict[str, Any] = load_state()
        return state
    except FileNotFoundError as e:
        logger.error("Stadium state file not found.", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error reading stadium state: State configuration file is missing.",
        ) from e
    except json.JSONDecodeError as e:
        logger.error("Malformed JSON in stadium state file.", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error reading stadium state: Invalid JSON state format.",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error reading stadium state.", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while reading the stadium state.",
        ) from e


@app.post("/api/simulate-tick", response_model=dict[str, Any])
async def trigger_simulation_tick() -> dict[str, Any]:
    """Trigger a simulator step mutation on-demand.

    Returns:
        dict[str, Any]: A dictionary containing the updated simulated stadium state.

    Raises:
        HTTPException: 500 if an error occurs running the simulation step.
    """
    try:
        run_simulator_once()
        state: dict[str, Any] = load_state()
        return state
    except FileNotFoundError as e:
        logger.error(
            "Simulation tick failed because state file is missing.", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Error running simulation step: "
                "State configuration file is missing."
            ),
        ) from e
    except json.JSONDecodeError as e:
        logger.error(
            "Simulation tick failed due to malformed state JSON.", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error running simulation step: Invalid JSON state format.",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error running simulation step.", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during the simulation tick.",
        ) from e

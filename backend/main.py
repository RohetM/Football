"""FastAPI central orchestrator for WorldCup OS.

Exposes endpoints for the Fan, Crowd, and Ops Agents, handles input validation,
CORS, slowapi rate limiting, and simulation ticks.
"""

import os
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

# Initialize slowapi limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="WorldCup OS Orchestrator API",
    description="GenAI stadium operations co-pilot backend",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
# Restricted to the Streamlit local frontend origin by default, customizable via environment variables
cors_origins_raw = os.getenv(
    "CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501"
)
CORS_ORIGINS = [
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
import time

RATE_LIMIT_TIMESTAMPS: dict[str, list[float]] = {}
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))


def check_rate_limit(ip: str) -> bool:
    """Evaluate rate limit of incoming request source IP.

    Args:
        ip: Client source IP address.

    Returns:
        bool: True if request is within limits, False if rate-limited.
    """
    now = time.time()
    if ip not in RATE_LIMIT_TIMESTAMPS:
        RATE_LIMIT_TIMESTAMPS[ip] = [now]
        return True

    # Filter timestamps to keep only those within the last 60 seconds
    timestamps = [t for t in RATE_LIMIT_TIMESTAMPS[ip] if now - t < 60]
    RATE_LIMIT_TIMESTAMPS[ip] = timestamps

    if len(timestamps) >= RATE_LIMIT_PER_MINUTE:
        return False

    RATE_LIMIT_TIMESTAMPS[ip].append(now)
    return True


# Pydantic request models
class FanQueryRequest(BaseModel):
    query: str = Field(..., max_length=500, description="The fan question text.")
    language: str = Field("en", description="Target response ISO language code.")
    accessibility_needs: str | None = Field(
        None, description="Special accessibility parameters."
    )


class OpsActionRequest(BaseModel):
    description: str = Field(..., description="Description of the incident.")
    type: str = Field(
        ...,
        description="Type/category of the incident (medical, security, accessibility).",
    )
    location: str = Field(..., description="Target stadium zone/gate.")


@app.post("/api/fan-query", response_model=dict[str, Any])
@limiter.limit("20/minute")
async def handle_fan_query(request: Request, body: FanQueryRequest):
    """Secure endpoint for fan FAQs and accessibility assistance.

    Applies rate limiting, validates text input structure, and routes to Fan Agent.
    """
    # 1. Apply rate limit check
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again in a minute.",
        )

    # 2. Validate input text (length, injections)
    is_valid, sanitized_text, error_msg = validate_query(body.query)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    # 3. Route request to Fan Agent
    result = query_fan_agent(
        query=sanitized_text,
        language=body.language,
        accessibility_needs=body.accessibility_needs,
    )
    return result


@app.get("/api/crowd-predict", response_model=dict[str, Any])
async def handle_crowd_predict():
    """Predictive crowd bottlenecks endpoint.

    Reads simulated game state and invokes Crowd Intel Agent.
    """
    result = query_crowd_agent()
    return result


@app.post("/api/ops-action", response_model=dict[str, Any])
async def handle_ops_action(body: OpsActionRequest):
    """Operations incident report and volunteer dispatch router.

    Validates incident location and runs nearest-neighbor volunteer assignment.
    """
    # Basic input check
    if not body.description.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incident description cannot be empty.",
        )

    # Hardened input check (safety validation)
    is_valid, sanitized_desc, error_msg = validate_query(body.description)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    result = query_ops_agent(
        incident_description=sanitized_desc,
        incident_type=body.type,
        incident_location=body.location,
    )
    return result


@app.get("/api/stadium-state", response_model=dict[str, Any])
async def get_stadium_state():
    """Fetch current raw simulated stadium operational data."""
    try:
        return load_state()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading stadium state: {str(e)}",
        )


@app.post("/api/simulate-tick", response_model=dict[str, Any])
async def trigger_simulation_tick():
    """Trigger a simulator step mutation on-demand."""
    try:
        run_simulator_once()
        return load_state()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running simulation step: {str(e)}",
        )

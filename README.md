# WorldCup OS

A GenAI stadium operations co-pilot that predicts crowd bottlenecks, guides fans with retrieval-grounded multilingual answers, and gives staff natural-language operational recommendations.

---

## 1. Problem Statement
Organizing large-scale events like the FIFA World Cup 2026 presents extreme operational bottlenecks:
- **Crowd Congestion**: High-density zones and long gate wait times create safety risks and fan frustration.
- **Support Inefficiency**: Fan queries are repetitive, multilingual, and require grounding in complex stadium policies.
- **Dispatch Latency**: Operations command centers struggle to manually compute physical proximity and dispatch volunteers to active incidents.

---

## 2. Solution Overview
WorldCup OS is a domain-driven, modular AI operations suite built on free-tier infrastructure. It deploys three specialized GenAI agents to act as co-pilots:
- **Fan Agent**: Grounded in a vector database to provide accurate, accessibility-aware, and multilingual Q&A.
- **Crowd Intel Agent**: Reasons over live simulated queue and transit telemetry to predict congestion.
- **Ops Agent**: Calculates physical coordinates and maps proximity to dispatch the nearest volunteer to incidents.
- **Agent Thoughts Transparency**: All three agents stream their reasoning trace directly to the frontend dashboard.

---

## 3. Vertical Chosen & Why
**Vertical**: Stadium Operations & Tournament Infrastructure.
**Why**: Large stadium events are highly dynamic. Collapsing general fan guides, telemetry predictions, and staff dispatching into generic chatbots leads to hallucinations. A domain-focused co-pilot separated into specific agent files handles these dynamic data structures safely and efficiently.

---

## 4. Architecture Diagram

```
        ┌───────────────────────────┐         ┌──────────────────────────┐
        │   stadium_state.json      │         │  ChromaDB Knowledge Base  │
        │ (queues, gates, weather,   │         │ (FAQs, policies,          │
        │  transport — simulated,    │         │  accessibility docs)      │
        │  updated on a timer)       │         └────────────┬─────────────┘
        └──────────────┬────────────┘                       │
                        │                                    │
                        ▼                                    ▼
              ┌────────────────────────────────────────────────────┐
              │                 FastAPI Orchestrator                 │
              │  Routes request → correct agent → LLM (Groq/Gemini)  │
              │  /api/fan-query   /api/crowd-predict   /api/ops-action│
              └───────┬─────────────────┬──────────────────┬─────────┘
                      ▼                 ▼                  ▼
              ┌──────────────┐  ┌──────────────────┐ ┌──────────────────┐
              │  Fan Agent    │  │  Crowd Intel Agent│ │   Ops Agent       │
              │  (RAG-grounded│  │ (reasons over state│ │ (volunteer +      │
              │  multilingual,│  │  → predicts issues  │ │  incident dispatch│
              │  accessibility│  │  before they occur) │ │  from ops queue)  │
              └──────────────┘  └────────────────────┘ └──────────────────┘
                      │                 │                  │
                      └────────┬────────┴──────────┬───────┘
                               ▼                    ▼
                   ┌────────────────────────────────────┐
                   │      Streamlit Dashboard             │
                   │  - Fan chat + language/accessibility │
                   │  - Live crowd heatmap + alert cards  │
                   │  - "Agent Thoughts" reasoning panel   │
                   │  - Volunteer/ops task feed             │
                   └────────────────────────────────────┘
```

---

## 5. Problem → Feature Mapping

| Identified Problem | Co-pilot Feature | Implementation Layer |
| :--- | :--- | :--- |
| Fan confusion regarding entrance gates and prohibited items. | Grounded Fan RAG Assistant. | `fan_agent.py` retrieves context chunks from ChromaDB. |
| Developing crowd congestion at security checkpoints. | Predictive bottleneck analyzer. | `crowd_agent.py` queries LLM on telemetry metrics. |
| Slow responder dispatching during medical or safety incidents. | Proximity-aware volunteer dispatcher. | `ops_agent.py` computes Manhattan distances on a grid. |
| Lack of operator trust in LLM outputs. | "Agent Thoughts" reasoning panel. | LLM responses return reasoning traces visible on UI. |

---

## 6. Tech Stack (free-tier, with reasoning)
- **FastAPI (Python)**: High-performance, async-capable web API.
- **Streamlit**: Rapid, Python-native dashboard rendering (requires zero frontend build tools).
- **ChromaDB**: File-based vector store embedded directly in the application (zero hosting costs).
- **sentence-transformers (`all-MiniLM-L6-v2`)**: Generates document embeddings locally (prevents API key quota usage).
- **Groq API (`llama-3.3-70b-versatile`)**: Super-fast, free-tier LLM inference.
- **Gemini API (`gemini-1.5-flash`)**: High-quota backup in case of Groq API rate limits.
- **SQLite / Local JSON**: Local storage (`stadium_state.json`) keeping deployment sizes lightweight (<10MB).

---

## 7. Setup Instructions

### Prerequisites
- Python 3.10+ installed
- API Keys: A Groq API Key and/or a Google Gemini API Key

### Configuration
1. Clone the repository.
2. Create a `.env` file in the root directory (based on `.env.example`):
   ```env
   GROQ_API_KEY=your_groq_api_key
   GEMINI_API_KEY=your_gemini_api_key
   RATE_LIMIT_PER_MINUTE=20
   ```

### Installation
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Build the local vector database index:
   ```bash
   python -m backend.rag.ingest
   ```

### Execution
1. Run the FastAPI backend:
   ```bash
   python -m uvicorn backend.main:app --port 8000
   ```
2. Run the Streamlit frontend:
   ```bash
   python -m streamlit run frontend/dashboard.py
   ```
3. Open `http://localhost:8501` in your browser.

---

## 8. API Documentation

### POST `/api/fan-query`
- **Description**: Secure RAG-guided fan chatbot answering questions about gate info, transport, and guidelines.
- **Body**:
  ```json
  {
    "query": "Where is Gate C?",
    "language": "English",
    "accessibility_needs": "Wheelchair access pathway"
  }
  ```
- **Response**: Returns a localized answer, a list of grounded sources, and a reasoning trace.

### GET `/api/crowd-predict`
- **Description**: Reasons over gate wait times and plaza capacity levels.
- **Response**: Structured JSON containing the predicted bottleneck, eta, action steps, and reasoning trace.

### POST `/api/ops-action`
- **Description**: Computes the nearest idle steward to an incident and formats dispatch commands.
- **Body**:
  ```json
  {
    "description": "Fainting near concession stand",
    "type": "medical",
    "location": "North_Plaza"
  }
  ```
- **Response**: The recommended volunteer ID, a dispatch text directive, and the reasoning trace.

---

## 9. Security Notes
- **Input Sanitization**: All queries entering public endpoints are processed via `validators.py` which rejects input text exceeding 500 characters, strips HTML tags, and detects SQL Injection or LLM Prompt Injection attacks.
- **IP Rate Limiting**: Endpoint `/api/fan-query` enforces a rolling request rate limit per IP using local FastAPI memory to prevent spam.
- **Credentials Protection**: No API keys are committed. All secrets are loaded through environment variables.
- **CORS Policies**: Cross-Origin Resource Sharing is configured to restrict traffic strictly to Streamlit origins (`localhost:8501`), blocking external domain hijack attempts.

---

## 10. Testing
Unit and integration tests are implemented using `pytest`:
- **Security Validation**: Tests for SQLi, prompt injection, HTML stripping, and text length constraints (`tests/test_security.py`).
- **RAG Operations**: Tests verifying markdown parsing, ChromaDB storage, and semantic querying (`tests/test_rag_retriever.py`).
- **Agent Modules**: Isolated tests verifying core logic for Fan, Crowd, and Ops agents (`tests/test_fan_agent.py`, `tests/test_crowd_agent.py`, `tests/test_ops_agent.py`).
- **Orchestrator Endpoints**: API routes validation tests including mock agent integrations and rate limiting checks (`tests/test_main.py`).

Run all tests:
```bash
pytest
```

---

## 11. Accessibility Notes
- **Recommended Entrance**: Gate C features flat pathways, extra-wide turnstiles, and adjacent Guest Services desks.
- **Elevators and Support**: Accessible escalators/elevators are mapped, and Sensory Quiet Rooms are listed.
- **High-Contrast Mode**: A toggle in the dashboard adjusts styling to maximum contrast.
- **Screen Reader Support**: UI controls use native Streamlit markdown tags and labels.

---

## 12. Assumptions
- **State Telemetry**: Stadium data, weather, and transport lines are simulated locally by `update_state.py` on a tick timer.
- **No PII Collection**: All user interactions are transient; no personal identifying information or chats are logged to disk.

---

## 13. Demo Screenshots / Walkthrough
*Walkthrough screenshots captured via automated browser agents are stored under:*
- [docs/demo-screenshots/](file:///d:/Football/docs/demo-screenshots/)

---

## 14. Future Scope
- **Live IoT Feeds**: Connect the state simulator to real-time RFID/infrared gate sensors.
- **Redis State Cache**: Scale in-memory rate limiting and volunteer states to a production-grade Redis cache.
- **Speech-to-Text**: Integrate browser audio input for hands-free volunteer communications.

# Design Concepts — WorldCup OS

## Why three agents instead of one chatbot
A single monolithic chatbot prompt would have to manage three entirely separate roles: answering fan FAQs, predicting crowd flow bottlenecks, and dispatching volunteers. Mixing these tasks increases prompt complexity and the risk of hallucination. For example:
- The **Fan Agent** retrieves unstructured knowledge from the policy manual (FAQ).
- The **Crowd Intel Agent** reasons over structured numeric telemetry (`stadium_state.json`).
- The **Ops Agent** calculates physical coordinate distances on a grid to dispatch volunteers.

Separating these concerns into three distinct agents ensures:
1. Each LLM call is constrained by a narrow, focused system prompt.
2. The context size is minimized, reducing token cost and improving latency.
3. Verification is localized: we can test security dispatch logic without invoking vector RAG pipelines.

## Why two data sources (ChromaDB + stadium_state.json)
We use two separate data storage mechanisms:
1. **ChromaDB Vector Database**: Stores slow-changing, unstructured prose (rules, policies, maps, accessibility guidelines). It requires semantic search (RAG) because fan questions are open-ended and language-agnostic.
2. **`stadium_state.json`**: Stores fast-changing, structured operational numbers (current gate queue wait times, transit delays, plaza percentages). Grounding the Crowd and Ops agents directly in this structured JSON bypasses unnecessary semantic retrieval, eliminating retrieval latency and ensuring the model always reasons over the absolute latest numerical state.

## What's simulated vs. real
- **Simulated state**: The queue wait times, transit delays, and plaza crowd levels are simulated in `stadium_state.json`. A background script (`update_state.py`) fluctuates these values to represent match day dynamics.
- **Real logic**: The RAG retrieval pipeline, input safety sanitization, Manhattan distance volunteer dispatch calculations, and the multi-agent routing architecture are fully functional and ready for live integration.

## Known limitations
- **Rate limiting**: The current rate limiter is stored in-memory in the FastAPI app state. In a multi-worker production environment, this would need a shared memory store like Redis to work consistently across nodes.
- **Local Embeddings**: The vector DB uses local `all-MiniLM-L6-v2` embeddings. While it is lightweight and free, scaling up to thousands of pages might require a dedicated, GPU-accelerated embedding service.

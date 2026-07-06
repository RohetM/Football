"""Fan Agent module.

Grounds replies on retrieved context from the ChromaDB vector database,
supports multilingual answers, handles accessibility needs, and outputs a JSON
structure with the answer and reasoning trace.
"""

import json
from typing import Any

from backend.agents.llm import call_llm
from backend.rag.retriever import retrieve_context

SYSTEM_PROMPT = """You are the Fan Agent for "WorldCup OS," an intelligent co-pilot assisting stadium fans for the FIFA World Cup 2026.

Your task is to answer fan questions accurately and helpfully, using ONLY the provided retrieved context from the stadium FAQ and policies database.

Rules:
1. Ground your answer strictly in the provided "Retrieved Context". Do not invent policies, hours, or gate recommendations.
2. If the context does not contain enough info to answer the question, state politely that you do not have that information.
3. Respond in the fan's requested target language (e.g., English, Spanish, French, etc.).
4. Pay special attention to "Accessibility Needs". If wheelchair access, sensory accommodations, or other needs are specified:
   - Highlight Gate C as the recommended ramp-free accessibility gate.
   - Advise them to seek Guest Services volunteers in blue vests.
   - Mention elevator locations and Section 112 sensory room if relevant.
5. You MUST return a JSON object with exactly two keys:
   - "response": The detailed multilingual answer text.
   - "reasoning": A short (1-2 sentences) explanation of which files/policies were retrieved to answer the question, explaining your rationale.

JSON format:
{
  "response": "...",
  "reasoning": "..."
}
"""


def format_context(context_docs: list[dict[str, Any]]) -> str:
    """Format retrieved document chunks into a single readable string.

    Args:
        context_docs: List of dicts with "content", "source", and "header".

    Returns:
        str: Formatted context blocks.
    """
    if not context_docs:
        return "No relevant context found in database."

    formatted = []
    for doc in context_docs:
        source = doc.get("source", "unknown")
        header = doc.get("header", "unknown")
        content = doc.get("content", "")
        formatted.append(f"--- Source: {source} | Section: {header} ---\n{content}")

    return "\n\n".join(formatted)


def query_fan_agent(
    query: str, language: str = "en", accessibility_needs: str | None = None
) -> dict[str, Any]:
    """Process a fan query, retrieve RAG context, and get a localized, accessible response.

    Args:
        query: The raw fan question.
        language: Desired response language.
        accessibility_needs: Special accessibility requirements.

    Returns:
        Dict[str, Any]: Response dictionary with "response", "reasoning", and "sources".
    """
    # 1. Retrieve RAG context from local ChromaDB
    retrieved_docs = retrieve_context(query, n_results=3)
    context_text = format_context(retrieved_docs)

    # 2. Extract source files/headers for return metadata
    sources = []
    for doc in retrieved_docs:
        src = f"{doc.get('source')} -> {doc.get('header')}"
        if src not in sources:
            sources.append(src)

    # 3. Construct user prompt for the LLM
    user_prompt = f"""User Query: {query}
Target Language: {language}
Accessibility Needs: {accessibility_needs or "None"}

Retrieved Context:
{context_text}
"""

    # 4. Call LLM (Groq with Gemini Fallback) in JSON mode
    try:
        response_text, raw_trace = call_llm(
            system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, json_mode=True
        )

        # 5. Parse JSON response
        data = json.loads(response_text)

        # Ensure reasoning trace integrates the LLM's reasoning + source metadata + LLM route trace
        model_reasoning = data.get("reasoning", "No model reasoning generated.")
        full_reasoning = (
            f"{model_reasoning} [Sources: {', '.join(sources)}]. {raw_trace}"
        )

        return {
            "response": data.get("response", "Could not formulate an answer."),
            "reasoning": full_reasoning,
            "sources": sources,
        }

    except Exception as e:
        print(f"Error in Fan Agent: {e}")
        # Return fallback dictionary structure
        return {
            "response": "We are experiencing technical difficulties. Please consult a Guest Services staff member in a blue vest.",
            "reasoning": f"Fan Agent processing failed: {str(e)}",
            "sources": sources,
        }

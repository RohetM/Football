"""LLM utility to communicate with Groq and Gemini APIs.

Supports Groq (llama-3.3-70b-versatile) as the primary LLM, with fallback to
Gemini (gemini-1.5-flash) if Groq returns errors or has quota issues.
"""

import os
import json
from typing import Optional, Dict, Any
from groq import Groq
import google.generativeai as genai

# Configuration constants
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-1.5-flash"


def get_groq_client() -> Optional[Groq]:
    """Instantiate a Groq client if the API key is present.

    Returns:
        Optional[Groq]: Groq client or None if key is missing.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def get_gemini_model(system_instruction: str, json_mode: bool = False) -> genai.GenerativeModel:
    """Configure and return a Gemini GenerativeModel instance.

    Args:
        system_instruction: System prompt rules.
        json_mode: True to request JSON output.

    Returns:
        genai.GenerativeModel: Instantiated model.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    generation_config = {}
    if json_mode:
        generation_config["response_mime_type"] = "application/json"

    return genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system_instruction,
        generation_config=generation_config
    )


def call_llm(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False,
    override_reasoning_trace: bool = False
) -> tuple[str, str]:
    """Call Groq LLM with fallback to Gemini.

    Args:
        system_prompt: Instructions outlining the assistant's persona.
        user_prompt: The user query.
        json_mode: Whether to enforce structured JSON output.
        override_reasoning_trace: If True, we return a mock trace when no keys are set.

    Returns:
        tuple[str, str]: (llm_response_text, reasoning_trace)
    """
    groq_client = get_groq_client()
    gemini_key = os.getenv("GEMINI_API_KEY")

    # If no keys are set (e.g. during offline test run), return dummy mock data
    if not groq_client and not gemini_key:
        if json_mode:
            mock_json = {
                "response": "Stadium response (Offline Mode)",
                "reasoning": "Offline mode triggered: no Groq or Gemini API keys detected in configuration.",
                "issue": "Offline placeholder",
                "eta_minutes": 0,
                "recommended_action": "Configure GROQ_API_KEY or GEMINI_API_KEY in .env",
                "confidence": "LOW"
            }
            return json.dumps(mock_json), "Reasoning: Offline fallback mock data generated because no LLM API keys are set."
        return "Stadium response (Offline Mode). Please set GROQ_API_KEY or GEMINI_API_KEY.", "Reasoning: Offline fallback mock data generated because no LLM API keys are set."

    # Try Groq first
    if groq_client:
        try:
            print(f"Calling Groq LLM ({GROQ_MODEL})...")
            kwargs: Dict[str, Any] = {}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=GROQ_MODEL,
                temperature=0.2,
                **kwargs
            )
            response_text = completion.choices[0].message.content
            return response_text, f"Successfully executed primary Groq model ({GROQ_MODEL})."

        except Exception as e:
            print(f"Groq API call failed or quota exceeded: {e}. Falling back to Gemini...")
            # Fall through to Gemini

    # Try Gemini fallback
    if gemini_key:
        try:
            print(f"Calling Gemini Fallback ({GEMINI_MODEL})...")
            model = get_gemini_model(system_prompt, json_mode)
            response = model.generate_content(user_prompt)
            return response.text, f"Groq failed. Successfully executed fallback Gemini model ({GEMINI_MODEL})."
        except Exception as e:
            print(f"Gemini API call failed: {e}")
            raise RuntimeError(f"Both Groq and Gemini API calls failed: {e}") from e

    raise RuntimeError("Groq key was failed, and no Gemini API key configured.")

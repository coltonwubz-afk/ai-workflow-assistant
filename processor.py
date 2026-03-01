"""
Claude API prompt chain logic.

Chain:
  Step 1 — Call Claude with a type-specific extraction prompt to deeply analyze the raw input.
  Step 2 — Call Claude again with the extraction output to produce a structured JSON result.

This two-step chain gives better results than a single prompt because the model can
reason freely in step 1 without being constrained by JSON format requirements.
"""

import json
import os

import anthropic

from prompts import (
    ERROR_LOG_EXTRACT,
    MEETING_NOTES_EXTRACT,
    STRUCTURE_OUTPUT,
    SUPPORT_TICKET_EXTRACT,
)
from utils import parse_json_response

MODEL = "claude-sonnet-4-6"
MAX_TOKENS_EXTRACT = 1024
MAX_TOKENS_STRUCTURE = 1024

EXTRACT_PROMPTS = {
    "support_ticket": SUPPORT_TICKET_EXTRACT,
    "meeting_notes": MEETING_NOTES_EXTRACT,
    "error_log": ERROR_LOG_EXTRACT,
}

INPUT_TYPE_LABELS = {
    "support_ticket": "support_ticket",
    "meeting_notes": "meeting_notes",
    "error_log": "error_log",
}


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to your .env file or set it as an environment variable."
        )
    return anthropic.Anthropic(api_key=api_key)


def _call_claude(client: anthropic.Anthropic, prompt: str, max_tokens: int) -> str:
    """Single Claude API call. Returns the text content of the response."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def process_input(raw_text: str, input_type: str) -> dict:
    """
    Run the two-step prompt chain on raw_text.

    Args:
        raw_text:   The pasted support ticket, meeting notes, or error log.
        input_type: One of 'support_ticket', 'meeting_notes', 'error_log'.

    Returns:
        A dict matching the structured JSON schema defined in prompts.STRUCTURE_OUTPUT.

    Raises:
        ValueError:       If input_type is not recognised or inputs are empty.
        EnvironmentError: If the API key is missing.
        RuntimeError:     If the Claude response cannot be parsed as valid JSON.
    """
    raw_text = raw_text.strip()
    if not raw_text:
        raise ValueError("Input text cannot be empty.")

    if input_type not in EXTRACT_PROMPTS:
        raise ValueError(
            f"Unknown input type '{input_type}'. "
            f"Choose from: {', '.join(EXTRACT_PROMPTS.keys())}"
        )

    client = _get_client()

    # ------------------------------------------------------------------
    # Step 1 — Deep extraction
    # ------------------------------------------------------------------
    extract_prompt = EXTRACT_PROMPTS[input_type].format(input_text=raw_text)
    analysis = _call_claude(client, extract_prompt, MAX_TOKENS_EXTRACT)

    # ------------------------------------------------------------------
    # Step 2 — Structured output
    # ------------------------------------------------------------------
    structure_prompt = STRUCTURE_OUTPUT.format(
        input_type=INPUT_TYPE_LABELS[input_type],
        analysis=analysis,
    )
    structured_raw = _call_claude(client, structure_prompt, MAX_TOKENS_STRUCTURE)

    result = parse_json_response(structured_raw)

    # Attach the step-1 analysis so the UI can optionally surface it
    result["_analysis"] = analysis
    result["_input_type"] = input_type

    return result

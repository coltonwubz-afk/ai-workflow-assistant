"""
Utility helpers: JSON parsing, markdown rendering, download formatting.
"""

import json
import re
from datetime import datetime


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def parse_json_response(text: str) -> dict:
    """
    Parse a JSON object from a Claude response string.

    Handles common LLM quirks:
    - Leading/trailing whitespace
    - Markdown code fences (```json ... ``` or ``` ... ```)
    - Stray commentary before or after the JSON block
    """
    text = text.strip()

    # Strip markdown fences if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall back: find the outermost {...} block
    brace_match = re.search(r"\{[\s\S]+\}", text)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Could not parse structured JSON from Claude response.\n"
                f"Raw response:\n{text}\n\nError: {exc}"
            ) from exc

    raise RuntimeError(
        f"No JSON object found in Claude response.\nRaw response:\n{text}"
    )


# ---------------------------------------------------------------------------
# Priority badge coloring (for Streamlit markdown)
# ---------------------------------------------------------------------------

PRIORITY_COLORS = {
    "Critical": "#FF4B4B",
    "High":     "#FF8C00",
    "Medium":   "#FFC300",
    "Low":      "#2ECC71",
}

CONFIDENCE_COLORS = {
    "High":   "#2ECC71",
    "Medium": "#FFC300",
    "Low":    "#FF8C00",
}

INPUT_TYPE_LABELS = {
    "support_ticket": "Support Ticket",
    "meeting_notes":  "Meeting Notes",
    "error_log":      "Error Log",
}


def priority_color(priority: str) -> str:
    return PRIORITY_COLORS.get(priority, "#888888")


def confidence_color(confidence: str) -> str:
    return CONFIDENCE_COLORS.get(confidence, "#888888")


# ---------------------------------------------------------------------------
# Markdown export
# ---------------------------------------------------------------------------

def result_to_markdown(result: dict) -> str:
    """
    Convert a structured result dict into a well-formatted markdown document
    suitable for download.
    """
    input_type = result.get("_input_type", "unknown")
    type_label = INPUT_TYPE_LABELS.get(input_type, input_type.replace("_", " ").title())
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    priority = result.get("priority", "Unknown")
    category = result.get("category", "Unknown")
    confidence = result.get("confidence", "Unknown")
    summary = result.get("summary", "No summary available.")
    action_items = result.get("action_items", [])
    key_details = result.get("key_details", {})

    lines = [
        f"# AI Workflow Assistant — {type_label} Report",
        f"",
        f"**Generated:** {timestamp}  ",
        f"**Priority:** {priority}  ",
        f"**Category:** {category}  ",
        f"**Confidence:** {confidence}",
        f"",
        f"---",
        f"",
        f"## Summary",
        f"",
        summary,
        f"",
        f"---",
        f"",
        f"## Action Items",
        f"",
    ]

    if action_items:
        for i, item in enumerate(action_items, 1):
            task = item.get("task", "")
            owner = item.get("owner", "Unassigned")
            due = item.get("due", "Not specified")
            lines.append(f"{i}. **{task}**")
            lines.append(f"   - Owner: {owner}")
            lines.append(f"   - Due: {due}")
            lines.append("")
    else:
        lines.append("_No action items identified._")
        lines.append("")

    lines += [
        f"---",
        f"",
        f"## Key Details",
        f"",
    ]

    if key_details:
        for key, value in key_details.items():
            label = key.replace("_", " ").title()
            lines.append(f"- **{label}:** {value}")
        lines.append("")
    else:
        lines.append("_No additional details._")
        lines.append("")

    # Optionally include the raw step-1 analysis
    analysis = result.get("_analysis")
    if analysis:
        lines += [
            f"---",
            f"",
            f"## Full Analysis (Step 1)",
            f"",
            analysis,
            f"",
        ]

    return "\n".join(lines)


def markdown_filename(input_type: str) -> str:
    """Generate a timestamped filename for the markdown download."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = input_type.replace(" ", "_").lower()
    return f"workflow_report_{slug}_{timestamp}.md"

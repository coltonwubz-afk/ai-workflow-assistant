"""
Prompt templates for each input type.
Each type has two prompts used in a chain:
  1. EXTRACT - type-specific analysis of the raw input
  2. STRUCTURE - converts the analysis into a consistent JSON schema
"""

# ---------------------------------------------------------------------------
# Step 1 — Type-specific extraction prompts
# ---------------------------------------------------------------------------

SUPPORT_TICKET_EXTRACT = """You are an expert support engineer. Analyze the following support ticket thoroughly.

Identify:
- The core problem the user is experiencing
- Any steps to reproduce mentioned (or inferred)
- The impact on the user (blocking, degraded, cosmetic, etc.)
- Any environment details (OS, version, browser, etc.)
- The emotional tone of the ticket (frustrated, neutral, urgent, etc.)
- Whether this looks like a bug, feature request, or general question

Support Ticket:
\"\"\"
{input_text}
\"\"\"

Provide a detailed technical analysis. Be precise and factual."""


MEETING_NOTES_EXTRACT = """You are an expert meeting facilitator and executive assistant. Analyze the following meeting notes.

Identify:
- The main topics discussed
- Key decisions made (and who made them, if mentioned)
- Action items assigned (with owners and deadlines if present)
- Open questions or blockers raised
- The type of meeting (planning, retrospective, sync, design review, etc.)
- Overall outcome: was the meeting productive? What was resolved vs. deferred?

Meeting Notes:
\"\"\"
{input_text}
\"\"\"

Provide a thorough analysis. Capture every action item and decision — nothing should be missed."""


ERROR_LOG_EXTRACT = """You are a senior software engineer and incident responder. Analyze the following error log.

Identify:
- The primary error or exception type
- The root cause (or most likely root cause if not definitive)
- The affected service, component, or function
- The severity and blast radius (who/what is impacted)
- Any stack trace details that point to the origin
- Recommended remediation steps
- Whether this looks like a known class of error (e.g., OOM, timeout, null pointer, auth failure, etc.)

Error Log:
\"\"\"
{input_text}
\"\"\"

Provide a precise technical breakdown. Prioritize actionable insights."""


# ---------------------------------------------------------------------------
# Step 2 — Universal structuring prompt (runs after extraction)
# ---------------------------------------------------------------------------

STRUCTURE_OUTPUT = """You are a data extraction assistant. Convert the analysis below into a strict JSON object.

Input Type: {input_type}

Analysis:
\"\"\"
{analysis}
\"\"\"

Return ONLY valid JSON with exactly this schema — no markdown fences, no extra keys, no commentary:

{{
  "summary": "<2-4 sentence plain-English summary of the situation>",
  "category": "<single category label — see options per type below>",
  "priority": "<one of: Critical | High | Medium | Low>",
  "action_items": [
    {{
      "task": "<specific, actionable task description>",
      "owner": "<person or team responsible, or 'Unassigned'>",
      "due": "<deadline if mentioned, or 'Not specified'>"
    }}
  ],
  "key_details": {{
    <3-6 type-specific key/value pairs that capture important context>
  }},
  "confidence": "<High | Medium | Low — how confident are you in this analysis given the input quality>"
}}

Category options by input type:
- support_ticket: Bug | Feature Request | Question | Account Issue | Performance | Security
- meeting_notes: Planning | Retrospective | Design Review | Status Sync | Incident Review | Kickoff
- error_log: Application Error | Infrastructure | Security | Data Integrity | Performance | Configuration

Priority guidance:
- Critical: system down, data loss, security breach, customer-facing outage
- High: major feature broken, urgent deadline, significant user impact
- Medium: partial degradation, near-term action needed, non-blocking issue
- Low: minor issue, informational, long-term improvement

Respond with ONLY the JSON object."""

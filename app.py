"""
Streamlit UI for the AI Workflow Assistant.

Run with:
    streamlit run app.py
"""

import os

import streamlit as st
from dotenv import load_dotenv

from processor import process_input
from utils import (
    confidence_color,
    markdown_filename,
    priority_color,
    result_to_markdown,
    INPUT_TYPE_LABELS,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Workflow Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Override Streamlit's default red primary button color with blue
st.markdown(
    """
    <style>
    button[data-testid="baseButton-primary"] {
        background-color: #1976D2 !important;
        border-color: #1976D2 !important;
        color: #fff !important;
    }
    button[data-testid="baseButton-primary"]:hover {
        background-color: #1565C0 !important;
        border-color: #1565C0 !important;
    }
    button[data-testid="baseButton-primary"]:active {
        background-color: #0D47A1 !important;
        border-color: #0D47A1 !important;
    }
    button[data-testid="baseButton-primary"]:disabled {
        background-color: #1976D2 !important;
        border-color: #1976D2 !important;
        color: #fff !important;
        opacity: 0.6 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

if "raw_text" not in st.session_state:
    st.session_state.raw_text = ""
if "result" not in st.session_state:
    st.session_state.result = None
if "error" not in st.session_state:
    st.session_state.error = None
if "processing" not in st.session_state:
    st.session_state.processing = False
if "input_type" not in st.session_state:
    st.session_state.input_type = None

# ---------------------------------------------------------------------------
# Example inputs (one per type)
# ---------------------------------------------------------------------------

EXAMPLES = {
    "support_ticket": (
        "Subject: App crashes immediately on login with Google SSO\n\n"
        "Hi team, since the update pushed on March 1st, our entire sales team can't log in. "
        "The app crashes immediately after clicking \"Sign in with Google\". This is blocking "
        "15 people from doing their work. We're on the Enterprise plan.\n"
        "Device: MacBook Pro, macOS Ventura 13.6, Chrome 122.\n"
        "Error message shown: \"Authentication service unavailable.\"\n"
        "This is urgent — please escalate."
    ),
    "meeting_notes": (
        "Sprint Planning — Q1 Week 9\n"
        "Attendees: Sarah (PM), Dev (Engineering lead), Priya, Tom, Marcus\n\n"
        "Discussed last sprint's velocity (42 points, target was 50). Tom flagged the auth "
        "service is still flaky — agreed to spike on it Monday. Sarah confirmed the mobile "
        "launch date is locked: April 14th. Priya will own the push notification work and "
        "needs designs from the UX team by EOD Thursday. Marcus volunteered to write the "
        "deployment runbook by next Friday. Open question: do we need a feature flag for "
        "the new onboarding flow? Decision deferred to async Slack thread."
    ),
    "error_log": (
        "[CRITICAL] 2024-03-04 09:17:43 UTC — PaymentService\n"
        "java.lang.NullPointerException: Cannot invoke \"com.example.Payment.getAmount()\" "
        "because \"payment\" is null\n"
        "    at com.example.PaymentService.processCharge(PaymentService.java:214)\n"
        "    at com.example.OrderController.checkout(OrderController.java:88)\n"
        "    at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)\n"
        "Caused by: Database timeout after 30000ms — connection pool exhausted (pool size: 10/10)\n"
        "Request context: user_id=84291, order_id=ORD-20240304-8841, amount=$349.00\n"
        "Last successful transaction: 09:12:01 UTC"
    ),
}

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("⚡ AI Workflow Assistant")
    st.caption("Powered by Claude claude-sonnet-4-6")

    st.markdown("---")

    st.markdown("### How it works")
    st.markdown(
        """
1. **Paste** your raw text below
2. **Select** the input type
3. **Analyze** — Claude runs a two-step prompt chain:
   - Step 1: Deep type-specific extraction
   - Step 2: Structured JSON output
4. **Download** the report as Markdown
        """
    )

    st.markdown("---")

    st.markdown("### Input types")
    st.markdown(
        """
- **Support Ticket** — bug reports, customer issues, feature requests
- **Meeting Notes** — decisions, action items, follow-ups
- **Error Log** — stack traces, exceptions, incident logs
        """
    )

    st.markdown("---")

    api_key_env = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key_env:
        st.success("API key loaded from environment", icon="✅")
    else:
        st.warning("No API key found in environment", icon="⚠️")
        api_key_input = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            help="Enter your key here or add it to a .env file as ANTHROPIC_API_KEY",
        )
        if api_key_input:
            os.environ["ANTHROPIC_API_KEY"] = api_key_input

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

st.header("AI Workflow Assistant", divider="gray")
st.markdown(
    "Paste raw text from a **support ticket**, **meeting notes**, or **error log** "
    "and get a structured summary, action items, category, and priority — instantly."
)

col_input, col_output = st.columns([1, 1], gap="large")

# ---------------------------------------------------------------------------
# Left column — Input
# ---------------------------------------------------------------------------

with col_input:
    st.subheader("Input")

    # Input type selector and Load example button on the same row
    type_col, example_col = st.columns([3, 1])
    with type_col:
        input_type = st.selectbox(
            "Input type",
            options=list(INPUT_TYPE_LABELS.keys()),
            format_func=lambda k: INPUT_TYPE_LABELS[k],
            index=None,
            placeholder="Select input type...",
            key="input_type",
            help="Select the type of text you are pasting. This determines which prompt chain is used.",
        )
    with example_col:
        # Spacer matches the selectbox label height
        st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        load_example_btn = st.button(
            "Load example",
            use_container_width=True,
            disabled=input_type is None,
        )

    if load_example_btn and input_type:
        st.session_state.raw_text = EXAMPLES[input_type]
        st.rerun()

    PLACEHOLDERS = {
        "support_ticket": "Paste your support ticket here, or click 'Load example' above…",
        "meeting_notes":  "Paste your meeting notes here, or click 'Load example' above…",
        "error_log":      "Paste your error log here, or click 'Load example' above…",
    }

    raw_text = st.text_area(
        "Raw text",
        height=350,
        placeholder=PLACEHOLDERS.get(input_type, "Select an input type above, then paste your text here…"),
        label_visibility="collapsed",
        key="raw_text",
    )

    show_analysis = st.checkbox(
        "Show step-1 analysis",
        value=False,
        help="Display the intermediate extraction output from Claude's first reasoning pass.",
    )

    def _clear():
        st.session_state.raw_text = ""
        st.session_state.input_type = None
        st.session_state.result = None
        st.session_state.error = None
        st.session_state.processing = False

    # Analyze (primary/blue, 3/4 width) and Clear (secondary, 1/4 width)
    btn_analyze_col, btn_clear_col = st.columns([3, 1])
    with btn_analyze_col:
        if st.session_state.processing:
            # Render a plain HTML button during processing — immune to Streamlit's
            # running-state red styling since it's not a Streamlit widget.
            st.html("""
            <button disabled style="
                width:100%; height:38px; background-color:#1976D2;
                color:#fff; border:1px solid #1976D2; border-radius:4px;
                font-size:0.875rem; opacity:0.7; cursor:not-allowed;">
              Analyzing…
            </button>
            """)
            analyze_btn = False
        else:
            analyze_btn = st.button(
                "Analyze",
                type="primary",
                use_container_width=True,
                disabled=not (input_type and raw_text.strip()),
            )
    with btn_clear_col:
        st.button("Clear", use_container_width=True, on_click=_clear)

    if analyze_btn:
        st.session_state.processing = True
        st.rerun()

# ---------------------------------------------------------------------------
# Right column — Output
# ---------------------------------------------------------------------------

with col_output:
    st.subheader("Output")

    if st.session_state.processing:
        st.session_state.result = None
        st.session_state.error = None

        with st.spinner("Running prompt chain…"):
            try:
                result = process_input(st.session_state.raw_text, input_type)
                st.session_state.result = result
            except Exception as exc:
                st.session_state.error = str(exc)
            finally:
                st.session_state.processing = False
        st.rerun()

    # -----------------------------------------------------------------------
    # Render result
    # -----------------------------------------------------------------------

    if st.session_state.error:
        st.error(f"**Error:** {st.session_state.error}")

    elif st.session_state.result:
        result = st.session_state.result

        priority   = result.get("priority", "Unknown")
        category   = result.get("category", "Unknown")
        confidence = result.get("confidence", "Unknown")
        summary    = result.get("summary", "")
        action_items = result.get("action_items", [])
        key_details  = result.get("key_details", {})

        # Pre-build download content once so both buttons share the same data
        md_content = result_to_markdown(result)
        filename   = markdown_filename(result.get("_input_type", "report"))

        # ---- Download (top) ----
        st.download_button(
            label="Download report as Markdown",
            data=md_content,
            file_name=filename,
            mime="text/markdown",
            use_container_width=True,
            key="download_top",
        )

        st.markdown("---")

        # ---- Badges row ----
        p_color = priority_color(priority)
        c_color = confidence_color(confidence)

        st.html(f"""
        <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:12px;">
          <span style="background:{p_color};color:#fff;padding:3px 12px;
                border-radius:12px;font-weight:700;font-size:0.85rem;">
            {priority} Priority
          </span>
          <span style="background:#3a3a5c;color:#fff;padding:3px 12px;
                border-radius:12px;font-weight:600;font-size:0.85rem;">
            {category}
          </span>
          <span style="background:{c_color};color:#fff;padding:3px 12px;
                border-radius:12px;font-weight:600;font-size:0.85rem;">
            Confidence: {confidence}
          </span>
        </div>
        """)

        # ---- Summary ----
        st.markdown("**Summary**")
        st.markdown(summary)

        st.markdown("---")

        # ---- Action items ----
        st.markdown("**Action Items**")
        if action_items:
            for i, item in enumerate(action_items, 1):
                task  = item.get("task", "")
                owner = item.get("owner", "Unassigned")
                due   = item.get("due", "Not specified")
                st.markdown(
                    f"**{i}.** {task}  \n"
                    f"<span style='font-size:0.82rem;color:#888;'>"
                    f"Owner: {owner} &nbsp;·&nbsp; Due: {due}"
                    f"</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown("_No action items identified._")

        st.markdown("---")

        # ---- Key details ----
        st.markdown("**Key Details**")
        if key_details:
            for key, value in key_details.items():
                label = key.replace("_", " ").title()
                st.markdown(
                    f"<span style='color:#888;font-size:0.88rem;'>{label}</span>  \n{value}",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown("_No additional details._")

        # ---- Step-1 analysis (optional) ----
        if show_analysis and result.get("_analysis"):
            st.markdown("---")
            with st.expander("Step-1 Analysis (raw extraction)", expanded=True):
                st.markdown(result["_analysis"])

        # ---- Download (bottom) ----
        st.markdown("---")
        st.download_button(
            label="Download report as Markdown",
            data=md_content,
            file_name=filename,
            mime="text/markdown",
            use_container_width=True,
            key="download_bottom",
        )

    else:
        # -----------------------------------------------------------------------
        # Empty state — "How this works" architecture explainer
        # -----------------------------------------------------------------------
        st.markdown(
            "<div style='color:#888;margin-top:8px;margin-bottom:20px;text-align:center;'>"
            "Results will appear here after analysis."
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown("#### How this works")
        st.markdown(
            "Each input runs through a **two-step Claude prompt chain** that separates "
            "free-form reasoning from structured formatting — producing more reliable output "
            "than a single prompt."
        )
        st.markdown("")

        s1_col, arrow_col, s2_col = st.columns([10, 1, 10])
        with s1_col:
            st.html("""
            <div style="border:1px solid #3a3a5c;border-radius:8px;padding:14px 16px;">
              <p style="margin:0 0 6px 0;font-weight:700;font-size:0.88rem;color:#e0e0e0;">
                Step 1 &mdash; Extract
              </p>
              <p style="margin:0;font-size:0.82rem;color:#aaa;line-height:1.5;">
                A type-specific prompt instructs Claude as a domain expert
                (support engineer, meeting facilitator, or incident responder).
                Claude reasons freely and writes a detailed analysis — no format constraints.
              </p>
            </div>
            """)
        with arrow_col:
            st.html(
                "<div style='text-align:center;font-size:1.3rem;padding-top:20px;"
                "color:#555;'>→</div>"
            )
        with s2_col:
            st.html("""
            <div style="border:1px solid #3a3a5c;border-radius:8px;padding:14px 16px;">
              <p style="margin:0 0 6px 0;font-weight:700;font-size:0.88rem;color:#e0e0e0;">
                Step 2 &mdash; Structure
              </p>
              <p style="margin:0;font-size:0.82rem;color:#aaa;line-height:1.5;">
                The analysis is passed to a second prompt that demands only valid JSON:
                summary, action items (with owner &amp; due date), category, priority,
                key details, and confidence score.
              </p>
            </div>
            """)

        st.html("""
        <p style="font-size:0.81rem;color:#555;margin-top:14px;line-height:1.6;">
          Toggle <strong>Show step-1 analysis</strong> in the input panel to see
          Claude's raw reasoning alongside the structured output.
        </p>
        """)

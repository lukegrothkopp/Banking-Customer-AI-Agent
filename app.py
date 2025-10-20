from __future__ import annotations
import streamlit as st
import pandas as pd

from agents.classifier import ClassifierAgent
from agents.feedback import FeedbackHandler
from agents.query import QueryHandler
from core.db import get_conn, find_open_ticket_by_customer, insert_ticket, log_event

# --- Evaluation (QA & Routing Accuracy) ---
with st.expander("Evaluation (QA & Routing Accuracy)", expanded=False):
    use_llm_eval = st.checkbox(
        "Use LLM for classifier during evaluation",
        value=False,
        key="eval_use_llm",
        help="Toggle to compare rule-based vs. LLM classification."
    )
    limit_cases = st.number_input(
        "Limit test cases (optional)", min_value=0, max_value=100, value=0, step=1,
        help="0 means run all bundled tests."
    )
    run_eval = st.button("Run Benchmark", key="btn_eval")
    if run_eval:
        from eval.evaluator import run_benchmark
        import pandas as pd

        correct, total, rows = run_benchmark(
            use_llm=use_llm_eval,
            limit=int(limit_cases) if int(limit_cases) > 0 else None
        )
        acc = (correct / total) if total else 0.0
        st.markdown(f"**Accuracy:** {correct}/{total} &nbsp;&nbsp;(**{acc:.0%}**)")
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

        # Optional: quick confusion matrix for visibility
        if not df.empty and "expected" in df and "predicted" in df:
            cm = pd.crosstab(df["expected"], df["predicted"], dropna=False)
            st.markdown("**Confusion Matrix (Expected vs. Predicted)**")
            st.dataframe(cm, use_container_width=True)

st.set_page_config(page_title="Banking Support — Multi-Agent", page_icon="💬", layout="wide")
init_db()

if "history" not in st.session_state:
    st.session_state.history = []

st.title("💬 Banking Customer Support — Multi-Agent")
st.caption("Classifier → Feedback Handler / Query Handler • Evaluation • Logs • DB Viewer")

# If you have a sidebar toggle elsewhere, define `use_llm` before using it:
use_llm = st.sidebar.toggle("Use LLM for classification", value=True)

# Sidebar (already above)
st.sidebar.subheader("Database & Logs")
if st.sidebar.button("Refresh Tables"):
    st.rerun()

# --- Try an Input (replace/adjust your existing block) ---

st.markdown("### Try an Input")

user_text = st.text_area(
    "Enter your question or feedback",
    placeholder="e.g., Thanks for resolving my credit card issue.",
    key="try_text",
)

customer_name = st.text_input(
    "Your name",
    placeholder="e.g., Alex Chen",
    key="try_name",
)

has_ticket_checkbox = st.checkbox(
    "I already have a 6-digit ticket ID",
    value=False,
    key="has_ticket_checkbox",
)

ticket_id_input = None
if has_ticket_checkbox:
    ticket_id_input = st.text_input(
        "Ticket ID (6 digits)",
        placeholder="e.g., 650932",
        key="ticket_id_input",
        help="If you know your ticket ID, enter it here."
    )

run_btn = st.button("Run", key="btn_try")

if run_btn:
    if not user_text.strip():
        st.warning("Please enter a question or feedback.")
        st.stop()

    # Imports (kept local to avoid circulars during module import)
    from agents.classifier import ClassifierAgent
    from agents.feedback import FeedbackHandler
    from agents.query import QueryHandler
    from core.db import init_db, find_open_ticket_by_customer, insert_ticket, log_event
    from core.utils import generate_ticket_number

    conn = get_conn()
    classifier = ClassifierAgent(use_llm=False)  # or wire to your sidebar toggle
    feedback_agent = FeedbackHandler(conn=conn)
    query_agent = QueryHandler(conn=conn)

    # 1) Classify first (so we know whether we should ever create a ticket)
    try:
        label = classifier.classify(user_text)
    except Exception as e:
        st.error(f"Classifier error: {e}")
        label = "query"  # safe fallback

    st.write("**Classification:**", label)

    # 2) Normalize a working ticket_id based on the checkbox/name logic
    working_ticket_id = None

    if has_ticket_checkbox and ticket_id_input:
        # User explicitly provided a ticket id; trust this path
        working_ticket_id = ticket_id_input.strip()
    else:
        # User did NOT provide a ticket id.
        # If there is an open ticket under this name, keep using it.
        existing = find_open_ticket_by_customer(conn, (customer_name or "").strip()) if (customer_name or "").strip() else None
        if existing:
            working_ticket_id, _existing_status = existing
        else:
            # No open ticket under that name.
            # Only create a ticket if it's NOT purely positive feedback.
            if label in ("negative_feedback", "query"):
                # If negative feedback, we prefer to create via FeedbackHandler to reuse your logic & logs.
                if label == "negative_feedback":
                    # This will create a new ticket and return the empathetic message
                    resp = feedback_agent.handle_negative(customer_name=customer_name, description=user_text)
                    # Extract the ticket id we just created (your FeedbackHandler already knows it)
                    # If your handler doesn't return the id, we can cheaply re-fetch the most recent:
                    lookup_new = find_open_ticket_by_customer(conn, customer_name)
                    if lookup_new:
                        working_ticket_id = lookup_new[0]
                    st.success(resp)
                    log_event(conn, level="INFO", agent="Orchestrator", event="negative_feedback_new_ticket",
                              details={"customer_name": customer_name, "ticket_id": working_ticket_id})
                    st.stop()  # We’ve already responded with the negative-feedback path.
                else:
                    # label == "query": create a new ticket so we have something to check
                    new_tid = generate_ticket_number()
                    insert_ticket(conn,
                                  ticket_id=new_tid,
                                  customer_name=customer_name or "Unknown",
                                  description=user_text,
                                  status="Open")
                    working_ticket_id = new_tid
                    log_event(conn, level="INFO", agent="Orchestrator", event="query_new_ticket_created",
                              details={"customer_name": customer_name, "ticket_id": working_ticket_id})

    # 3) Route to the appropriate downstream agent
    if label == "positive_feedback":
        # Never create a new ticket for purely positive feedback
        resp = feedback_agent.handle_positive(customer_name or "Customer")
        st.success(resp)
        log_event(conn, level="INFO", agent="FeedbackHandler", event="positive_ack",
                  details={"customer_name": customer_name})
    elif label == "negative_feedback":
        # If we reached here, either:
        #  - user supplied an existing ticket, or
        #  - we found an existing open ticket by name.
        if working_ticket_id:
            msg = (
                f"We apologize for the inconvenience, {customer_name or 'Customer'}. "
                f"Your existing ticket #{working_ticket_id} is active—our team will follow up shortly."
            )
            st.info(msg)
            log_event(conn, level="INFO", agent="Orchestrator", event="negative_feedback_existing_ticket",
                      details={"customer_name": customer_name, "ticket_id": working_ticket_id})
        else:
            # Defensive fallback (shouldn’t happen due to earlier negative flow)
            resp = feedback_agent.handle_negative(customer_name=customer_name, description=user_text)
            st.success(resp)
    else:
        # label == "query"
        # Ensure the QueryHandler sees a ticket id:
        routed_text = user_text
        if working_ticket_id and ("ticket" not in user_text.lower()):
            routed_text = f"{user_text} (ticket {working_ticket_id})"

        status_resp = query_agent.handle(routed_text)

        # If we created a brand-new ticket for a query, append clarity
        if has_ticket_checkbox is False and working_ticket_id:
            status_resp += f"\n\nA ticket #{working_ticket_id} is now on file for this request."

        st.info(status_resp)
        log_event(conn, level="INFO", agent="QueryHandler", event="query_routed",
                  details={"customer_name": customer_name, "ticket_id": working_ticket_id})

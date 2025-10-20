from __future__ import annotations
import streamlit as st
import pandas as pd

from agents.classifier import ClassifierAgent
from agents.feedback import FeedbackHandler
from agents.query import QueryHandler
# ⬇️ add the two imports here
from core.db import (
    get_conn,
    find_open_ticket_by_customer,
    insert_ticket,
    log_event,
    list_tickets,          # NEW
    list_logs,             # NEW
)

st.set_page_config(page_title="Banking Support — Multi-Agent", page_icon="💬", layout="wide")
st.title("💬 Banking Customer Support — Multi-Agent")
st.caption("Classifier → Feedback Handler / Query Handler • Evaluation • Logs • DB Viewer")

# --- Try an Input (wrapped to avoid st.stop nuking the page) ---

def render_try_input():
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

    if not run_btn:
        return

    if not (user_text or "").strip():
        st.warning("Please enter a question or feedback.")
        return

    # Imports (kept local to avoid circulars during module import)
    from agents.classifier import ClassifierAgent
    from agents.feedback import FeedbackHandler
    from agents.query import QueryHandler
    from core.db import get_conn, find_open_ticket_by_customer, insert_ticket, log_event
    from core.utils import generate_ticket_number

    conn = get_conn()
    classifier = ClassifierAgent(use_llm=False)  # wire to your sidebar toggle if you prefer
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
    norm_name = (customer_name or "").strip()

    if has_ticket_checkbox and ticket_id_input:
        # User explicitly provided a ticket id; trust this path
        working_ticket_id = ticket_id_input.strip()
    else:
        # User did NOT provide a ticket id.
        # If there is an open ticket under this name, keep using it.
        existing = find_open_ticket_by_customer(conn, norm_name) if norm_name else None
        if existing:
            working_ticket_id, _existing_status = existing
        else:
            # No open ticket under that name.
            # Only create a ticket if it's NOT purely positive feedback.
            if label in ("negative_feedback", "query"):
                if label == "negative_feedback":
                    # Create via FeedbackHandler to reuse logic & logs
                    resp = feedback_agent.handle_negative(customer_name=norm_name, description=user_text)
                    # Re-fetch newest open ticket for that user to get the ID
                    lookup_new = find_open_ticket_by_customer(conn, norm_name)
                    if lookup_new:
                        working_ticket_id = lookup_new[0]
                    st.success(resp)
                    log_event(conn, level="INFO", agent="Orchestrator", event="negative_feedback_new_ticket",
                              details={"customer_name": norm_name, "ticket_id": working_ticket_id})
                    return  # ✅ return from function instead of st.stop()
                else:
                    # label == "query": create a new ticket so we have something to check
                    new_tid = generate_ticket_number()
                    insert_ticket(conn,
                                  ticket_id=new_tid,
                                  customer_name=norm_name or "Unknown",
                                  description=user_text,
                                  status="Open")
                    working_ticket_id = new_tid
                    log_event(conn, level="INFO", agent="Orchestrator", event="query_new_ticket_created",
                              details={"customer_name": norm_name, "ticket_id": working_ticket_id})

    # 3) Route to the appropriate downstream agent
    if label == "positive_feedback":
        # Never create a new ticket for purely positive feedback
        resp = feedback_agent.handle_positive(norm_name or "Customer")
        st.success(resp)
        log_event(conn, level="INFO", agent="FeedbackHandler", event="positive_ack",
                  details={"customer_name": norm_name})
        return

    elif label == "negative_feedback":
        # Either user supplied an existing ticket, or we found one by name.
        if working_ticket_id:
            msg = (
                f"We apologize for the inconvenience, {(norm_name or 'Customer')}. "
                f"Your existing ticket #{working_ticket_id} is active—our team will follow up shortly."
            )
            st.info(msg)
            log_event(conn, level="INFO", agent="Orchestrator", event="negative_feedback_existing_ticket",
                      details={"customer_name": norm_name, "ticket_id": working_ticket_id})
            return
        else:
            # Defensive fallback (shouldn’t happen due to earlier negative flow)
            resp = feedback_agent.handle_negative(customer_name=norm_name, description=user_text)
            st.success(resp)
            return

    else:
        # label == "query"
        routed_text = user_text
        if working_ticket_id and ("ticket" not in user_text.lower()):
            routed_text = f"{user_text} (ticket {working_ticket_id})"

        status_resp = query_agent.handle(routed_text)
        display_name = norm_name or "Customer"
        status_resp = f"**Hi {display_name},**\n\n{status_resp}"

        if has_ticket_checkbox is False and working_ticket_id:
            status_resp += f"\n\nA ticket #{working_ticket_id} is now on file for this request."

        st.info(status_resp)
        log_event(conn, level="INFO", agent="QueryHandler", event="query_routed",
                  details={"customer_name": norm_name, "ticket_id": working_ticket_id})
        return

# Call it after you render tabs/evaluation/etc.
render_try_input()

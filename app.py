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

st.markdown("### Try an Input")

with st.form("try_form", clear_on_submit=False):
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

    if has_ticket_checkbox:
        ticket_id_input = st.text_input(
            "Ticket ID (6 digits)",
            placeholder="e.g., 650932",
            key="ticket_id_input",
            help="If you know your ticket ID, enter it here."
        )
    else:
        ticket_id_input = ""

    submitted = st.form_submit_button("Submit", type="primary")

if submitted:
    if not (user_text or "").strip():
        st.warning("Please enter a question or feedback.")
        st.stop()

    # Local imports to avoid circulars (same style you already use)
    from agents.classifier import ClassifierAgent
    from agents.feedback import FeedbackHandler
    from agents.query import QueryHandler
    from core.db import find_open_ticket_by_customer, insert_ticket, log_event
    from core.utils import generate_ticket_number

    conn = get_conn()
    classifier = ClassifierAgent(use_llm=False)  # hook to your sidebar toggle if desired
    feedback_agent = FeedbackHandler(conn=conn)
    query_agent = QueryHandler(conn=conn)

    # 1) Classify (kept for transparency/metrics display)
    try:
        label = classifier.classify(user_text)
    except Exception as e:
        st.error(f"Classifier error: {e}")
        label = "query"  # safe fallback

    st.write("**Classification:**", label)

    # 2) If a ticket id is provided → treat as a FOLLOW-UP (short-circuit)
    ticket_field = (ticket_id_input or "").strip()
    display_name = (customer_name or "").strip() or "Customer"

    if ticket_field:
        # NEW: intent-aware follow-up path that adds notes/actions and returns contextual copy
        msg, err = feedback_agent.handle_followup(
            ticket_id=ticket_field,
            customer_name=display_name,
            user_text=user_text
        )
        if err:
            st.warning("We saved your note, but ran into a small issue updating the ticket. Our team has been notified.")
        st.success(msg)
        log_event(conn, level="INFO", agent="Orchestrator", event="followup_handled",
                  details={"customer_name": display_name, "ticket_id": ticket_field, "label": label})
        st.stop()

    # 3) No ticket id provided → reuse or create a working ticket id
    working_ticket_id = None
    existing = find_open_ticket_by_customer(conn, (customer_name or "").strip()) if (customer_name or "").strip() else None

    if existing:
        working_ticket_id, _existing_status = existing
    else:
        # Only create a ticket if NOT purely positive feedback
        if label in ("negative_feedback", "query"):
            if label == "negative_feedback":
                # Reuse your existing “create + empathetic reply” flow
                resp = feedback_agent.handle_negative(customer_name=customer_name, description=user_text)
                # Grab the new ticket id we just created
                lookup_new = find_open_ticket_by_customer(conn, customer_name)
                if lookup_new:
                    working_ticket_id = lookup_new[0]
                st.success(resp)
                log_event(conn, level="INFO", agent="Orchestrator", event="negative_feedback_new_ticket",
                          details={"customer_name": customer_name, "ticket_id": working_ticket_id})
                st.stop()
            else:
                # label == "query": create a new ticket for tracking
                new_tid = generate_ticket_number()
                insert_ticket(conn,
                              ticket_id=new_tid,
                              customer_name=customer_name or "Unknown",
                              description=user_text,
                              status="Open")
                working_ticket_id = new_tid
                log_event(conn, level="INFO", agent="Orchestrator", event="query_new_ticket_created",
                          details={"customer_name": customer_name, "ticket_id": working_ticket_id})

    # 4) Route based on label (kept consistent with your original behavior)
    if label == "positive_feedback":
        # Never create a new ticket for purely positive feedback
        resp = feedback_agent.handle_positive(customer_name or "Customer")
        st.success(resp)
        log_event(conn, level="INFO", agent="FeedbackHandler", event="positive_ack",
                  details={"customer_name": customer_name})

    elif label == "negative_feedback":
        # If we're here: user has or we found an existing ticket
        if working_ticket_id:
            msg = (
                f"We apologize for the inconvenience, {customer_name or 'Customer'}. "
                f"Your existing ticket #{working_ticket_id} is active—our team will follow up shortly."
            )
            st.info(msg)
            log_event(conn, level="INFO", agent="Orchestrator", event="negative_feedback_existing_ticket",
                      details={"customer_name": customer_name, "ticket_id": working_ticket_id})
        else:
            # Defensive fallback
            resp = feedback_agent.handle_negative(customer_name=customer_name, description=user_text)
            st.success(resp)

    else:
        # label == "query"
        routed_text = user_text
        if working_ticket_id and ("ticket" not in user_text.lower()):
            routed_text = f"{user_text} (ticket {working_ticket_id})"

        status_resp = query_agent.handle(routed_text)
        status_resp = f"**Hi {display_name},**\n\n{status_resp}"

        # If we created or reused a ticket (without user typing one), clarify the id
        if working_ticket_id:
            status_resp += f"\n\nA ticket #{working_ticket_id} is on file for this request."

        st.info(status_resp)
        log_event(conn, level="INFO", agent="QueryHandler", event="query_routed",
                  details={"customer_name": customer_name, "ticket_id": working_ticket_id})

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

if "history" not in st.session_state:
    st.session_state.history = []

# If you have a sidebar toggle elsewhere, define `use_llm` before using it:
use_llm = st.sidebar.toggle("Use LLM for classification", value=True)

# Sidebar (already above)
st.sidebar.subheader("Database & Logs")
if st.sidebar.button("Refresh Tables"):
    st.rerun()

tickets_tab, logs_tab = st.tabs(["📬 Tickets", "🪵 Logs"])
conn = get_conn()

with tickets_tab:
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("Refresh", key="btn_refresh_tickets"):
            pass
    try:
        tdf = pd.DataFrame(list_tickets(conn, limit=200))
        if tdf.empty:
            st.info("No tickets yet.")
        else:
            preferred_cols = [c for c in ["created_at","ticket_id","customer_name","status","description"] if c in tdf.columns]
            st.dataframe(tdf[preferred_cols] if preferred_cols else tdf, use_container_width=True, height=520)
    except Exception as e:
        st.error(f"Tickets error: {e}")

with logs_tab:
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("Refresh", key="btn_refresh_logs"):
            pass
    try:
        ldf = pd.DataFrame(list_logs(conn, limit=200))
        if ldf.empty:
            st.info("No logs yet.")
        else:
            preferred_cols = [c for c in ["ts","level","agent","event","details"] if c in ldf.columns]
            st.dataframe(ldf[preferred_cols] if preferred_cols else ldf, use_container_width=True, height=520)
    except Exception as e:
        st.error(f"Logs error: {e}")


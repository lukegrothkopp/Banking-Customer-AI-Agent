from __future__ import annotations
import streamlit as st
import pandas as pd

from agents.classifier import ClassifierAgent
from agents.feedback import FeedbackHandler
from agents.query import QueryHandler
from core.db import init_db, list_tickets, list_logs

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

# Main input
with st.container(border=True):
    st.subheader("Try an input")
    col1, col2 = st.columns([3, 1])
    with col1:
        user_text = st.text_input(
            "User message",
            placeholder="e.g., Could you check the status of ticket 650932?",
        )
        customer_name = st.text_input("Customer name (optional)", placeholder="Jane Doe")
    with col2:
        st.markdown("\n")
        go = st.button("Run", type="primary", use_container_width=True)

# Process
if go and user_text.strip():
    clf = ClassifierAgent(use_llm=use_llm)
    label = clf.classify(user_text)

    feedback = FeedbackHandler()
    query = QueryHandler()

    if label == "positive_feedback":
        reply = feedback.handle_positive(customer_name or None)
        route = "Classifier → Feedback(Positive)"
    elif label == "negative_feedback":
        reply = feedback.handle_negative(customer_name or None, description=user_text)
        route = "Classifier → Feedback(Negative)"
    else:
        reply = query.handle(user_text)
        route = "Classifier → QueryHandler"

    st.session_state.history.insert(0, {
        "input": user_text,
        "customer": customer_name,
        "route": label,
        "reply": reply,
    })

# Layout: left = conversation, right = DB & logs
left, right = st.columns([2, 2])

with left:
    st.subheader("Routing & Responses")
    if st.session_state.history:
        for i, h in enumerate(st.session_state.history[:20]):
            with st.expander(f"#{i+1} — {h['route']}"):
                st.markdown(f"**User:** {h['input']}")
                if h.get("customer"):
                    st.markdown(f"**Customer:** {h['customer']}")
                st.markdown(f"**Response:** {h['reply']}")
    else:
        st.info("No interactions yet. Try a sample like: ‘My debit card replacement still hasn’t arrived.’")

with right:
    st.subheader("🎫 Support Tickets (latest 100)")
    tickets = list_tickets(limit=100)
    st.dataframe(pd.DataFrame(tickets))

    st.subheader("🪵 Logs (latest 200)")
    logs = list_logs(limit=200)
    st.dataframe(pd.DataFrame(logs))

st.divider()
st.markdown(
    "**Notes**: \n"
    "• Positive feedback returns a friendly one-liner. \n"
    "• Negative feedback creates a 6-digit ticket and acknowledges it. \n"
    "• Queries extract a ticket number and report status. \n"
    "• Evaluation compares classifier predictions vs. expected labels."
)

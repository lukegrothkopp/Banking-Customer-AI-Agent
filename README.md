# Banking Customer Support AI Agent (Multi‑Agent, Streamlit)

This repository implements a **multi‑agent** architecture for a Banking Customer Support assistant in **Streamlit**, aligned to the provided outline (classifier → feedback handlers → query handler, plus evaluation & logging). fileciteturn0file0

## Features
- **Classifier Agent** routes messages to Feedback or Query handlers.
- **Feedback Handler**
- Positive: sends a warm, personalized thank‑you.
- Negative: creates a 6‑digit ticket in SQLite (`support_tickets`).
- **Query Handler** extracts a ticket number and returns status from DB.
- **LLMOps / Evaluation**
- Built‑in test cases, QA‑style scoring, routing success rate.
- Logs & traces panel for debugging.
- **Streamlit UI** with input box, routing visualization, DB viewer, and logs.

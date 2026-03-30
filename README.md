# Push_Performance

A BI-style interactive dashboard for CashKaro push campaign performance.

## Files
- `app.py` — Streamlit dashboard app
- `push_numbers_march_clean.csv` — source data
- `requirements.txt` — Python dependencies

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Share as a live link
Deploy this folder on:
- Streamlit Community Cloud
- Render
- Hugging Face Spaces
- Any internal VM/server that can run Streamlit

## Recommended next step
Connect this app to a Google Sheet / exported CSV so the dashboard auto-refreshes whenever the reporting sheet updates.

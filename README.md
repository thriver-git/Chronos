# Chronos

Chronos is an asynchronous, paper-trading LLM agent. Technical signals trigger
structured LLM decisions; hard risk controls validate every order before it can
reach Alpaca. It is educational software, not investment advice.

## Run locally

1. Create and activate a Python 3.10+ virtual environment.
2. Run `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and supply paper-trading Alpaca and Groq API keys.
4. Run `python -m chronos.main` in one terminal and `streamlit run dashboard/app.py` in another.

The system deliberately uses Alpaca paper trading. No live endpoint is configured.

## Render demo deployment

`render.yaml` deploys Chronos as a single Docker web service. It starts the
dashboard and engine in the same container. This is only appropriate for a
demo: Render Free web services sleep after idle periods and their local audit
files are ephemeral. Use a paid Background Worker plus a durable datastore for
continuous paper trading.

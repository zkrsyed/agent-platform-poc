"""Lesson 14: a small chat page for the DEPLOYED ga4-guide (not adk web).

  uv run uvicorn web.app:app --port 8080        # then open http://localhost:8080

The browser never talks to Google. It talks to this server, and this server calls the agent on
Agent Runtime with ITS OWN Google credentials (yours locally; a service account on Cloud Run):

  browser --POST /api/chat--> this server --async_stream_query--> ga4-guide on Agent Runtime
          <--- streamed lines (tool calls, text) ----------------- events, as they happen

Who is the user? Locally there's no login, so everyone is "local-user". Behind IAP on Cloud Run
(Part C), IAP signs the user in and adds a header with their email; we use that as user_id, so
each person gets their own sessions and `user:` state.
"""

import json
from pathlib import Path

import agentplatform
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse

PROJECT = "kc-okf-poc-261122"
REGION = "us-central1"
AGENT = f"projects/{PROJECT}/locations/{REGION}/reasoningEngines/7105399555822190592"

client = agentplatform.Client(project=PROJECT, location=REGION)
agent = client.runtimes.get(name=AGENT)  # read once at startup: the agent's methods and address
app = FastAPI(title="ga4 chat")


def user_id(request: Request) -> str:
    # IAP adds "accounts.google.com:someone@example.com" (docs). No IAP locally.
    email = request.headers.get("x-goog-authenticated-user-email", "")
    return email.split(":")[-1] or "local-user"


@app.get("/")
def page() -> FileResponse:
    return FileResponse(Path(__file__).parent / "index.html")


@app.post("/api/session")
async def new_session(request: Request) -> dict:
    """A new conversation = a new session on Agent Runtime (Google keeps its events and state)."""
    session = await agent.async_create_session(user_id=user_id(request))
    session_id = session["id"] if isinstance(session, dict) else session.id
    return {"session_id": session_id, "user_id": user_id(request)}


@app.post("/api/chat")
async def chat(request: Request) -> StreamingResponse:
    body = await request.json()
    uid = user_id(request)

    async def lines():
        # One JSON object per line ("NDJSON"), sent as soon as each event arrives.
        async for event in agent.async_stream_query(
            user_id=uid, session_id=body["session_id"], message=body["message"]
        ):
            for part in (event.get("content") or {}).get("parts", []):
                if "function_call" in part:
                    yield json.dumps({"type": "tool", "name": part["function_call"]["name"]}) + "\n"
                elif part.get("text") and not part.get("thought"):
                    yield json.dumps({"type": "text", "text": part["text"]}) + "\n"

    return StreamingResponse(lines(), media_type="application/x-ndjson")

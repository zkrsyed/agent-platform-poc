# Lesson 14: a real web page for the deployed agent

**Goal:** chat with the **deployed** `ga4-guide` from our own small web page instead of `adk web`. On the way we see the three things every agent front end needs: **sessions**, **streaming** and **who the user is**.

**Cost:**
- Part A runs locally and calls the deployed agent: each question is about **$0.11** in Gemini (lesson 11's figure; trim isn't deployed yet).
- Plan: **2–3 questions, about $0.30**. Nothing billed per hour.
- Part C (Cloud Run with login) is written down but **not run** unless we decide to.

## Why this lesson exists

`adk web` is a **developer** tool: it shows every event and trace, runs the agent inside itself, and has no login. A real user needs a plain chat page, and the agent should run where we deployed it (Agent Runtime, lesson 8).

```
adk web (lessons 2-13):   browser ──► adk web ──► agent code runs HERE, on your machine

this lesson:              browser ──► web/app.py ──► ga4-guide on Agent Runtime (Google)
                                       (small server)   async_stream_query
```

**Why a small server in the middle?** The browser can't call Agent Runtime directly: that needs **Google credentials**, and those must never go to a browser. Our server holds them (yours locally, a service account on Cloud Run) and passes only the chat through. .NET comparison: a backend-for-frontend (BFF).

## The three things a front end does

| Need | How (verified: these methods are listed on our deployed agent) | .NET comparison |
|---|---|---|
| **A conversation** | `async_create_session(user_id)` gives a session id; every message sends it back. Google stores the events and state. | a session id in a cookie |
| **Answers as they happen** | `async_stream_query(user_id, session_id, message)` yields events one by one: tool calls first, text at the end. Our server forwards them as one JSON object per line. | `IAsyncEnumerable` streamed to the client |
| **Who is asking** | the `user_id` you pass. Sessions, `user:` state and memories (lesson 13) are all kept **per user**. | `User.Identity.Name` |

The deployed agent lists **20 methods** (**verified**): sessions, memory (`async_search_memory`, `async_add_session_to_memory`), artifacts, and three ways to query. We use two of them.

## The code (already in the repo)

| File | What it does |
|---|---|
| `web/app.py` | FastAPI server, three routes. `GET /` serves the page. `POST /api/session` creates a session on Agent Runtime. `POST /api/chat` streams the agent's events back as lines: `{"type":"tool",...}` or `{"type":"text",...}`. |
| `web/index.html` | the chat page (plain HTML and JavaScript): reads the stream line by line, shows tool calls as small chips and the answer as it arrives |

`user_id`: locally everyone is `local-user`. Behind IAP (Part C), IAP adds the signed-in person's email in a header (`x-goog-authenticated-user-email`, **docs**), and `app.py` uses that instead.

Free check (**verified** 2026-11-27): the server starts, connects to the deployed agent on Agent Runtime, and serves the page.

---

## Part A: run it locally

### Step 1: start the server

```bash
cd ~/apps/agent-platform-poc
uv run uvicorn web.app:app --port 8080
```

Open `http://localhost:8080`. The header shows `user: local-user · session: <a long number>`: the page made a **session on Agent Runtime** as soon as it loaded. On the remote server, use the same SSH tunnel as before with `-L 8080:localhost:8080`.

### Step 2: ask a question

> I'm Priya from merch analytics. What was the final net revenue for 2021-01-25?

**Look for:**
- Tool chips appearing one by one (`remember_analyst`, `load_skill`, …, `execute_sql`) **while** the agent works, then the answer text. That's streaming.
- The same **$3,353.00** as earlier lessons.
- In the uvicorn terminal: `POST /api/session` once, `POST /api/chat` per question.

### Step 3: same session, then a new one

1. Ask a follow-up in the **same** conversation: "And the day before?" It should know what "the day before" means: same session.
2. Click **New conversation** and ask "What's my name?" It should still know: `user:` state is per user, not per session.

### Step 4: where it shows in the console

Agent Platform → **Agents** → `ga4-guide` → **Sessions**: your sessions under user `local-user` (the console may ask for `apphub.googleapis.com` first, see lesson 8; skip if so). **Traces** works too, because tracing is on since lesson 11.

**Send me:** a screenshot of the page with tool chips and the answer.

## Part B: what we left out (and why)

| A real app would add | Why we skipped it |
|---|---|
| Markdown rendering of the answer | needs a library; plain text is enough to learn |
| A list of past conversations | `async_list_sessions(user_id)` exists; one more route |
| Stopping a long answer | close the stream; not needed here |
| Rate limits, cost limits per user | important in production: one question = ~$0.11 |

## Part C: on Cloud Run with a login (docs, not run)

To put the page online for real people:

1. **Deploy `web/` to Cloud Run** (scale to zero, so idle costs nothing, **docs**), with a service account that holds `roles/aiplatform.user` (permission to query the agent).
2. **Turn on IAP** for the service: only allowed Google accounts get in, and IAP adds their email header. The same IAP as lesson 11's guard, here in front of a web app.
3. `app.py` already reads that header, so each person gets their own sessions and memories.

Rough commands (**docs**; check before running, and ask first: it's a public endpoint):

```bash
gcloud run deploy ga4-chat --source . --region us-central1 \
  --no-allow-unauthenticated --iap --service-account ga4-chat@$P.iam.gserviceaccount.com
gcloud iap web add-iam-policy-binding --member=user:YOU@example.com \
  --role=roles/iap.httpsResourceAccessor --region us-central1 --resource-type=cloud-run --service=ga4-chat
```

**A ready-made alternative:** **Gemini Enterprise** can publish an Agent Runtime agent to a company's users with their login and a chat UI built in (**docs**). It's a separate product with per-user pricing (**guess**), so it isn't part of this POC.

## Check yourself

1. Why can't the browser call Agent Runtime directly?
2. What does the session id give you, and what does the user id give you?
3. Why do tool chips appear before the answer?
4. With IAP in front, where does `user_id` come from, and why can't the user fake it?

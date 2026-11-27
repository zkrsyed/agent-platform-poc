# Lesson 13: Memory Bank (remembering across conversations)

**Goal:** the agent remembers an analyst's **preferences** from one conversation and uses them in the **next**, without us writing code for each fact. We compare it with the `user:` state we already have.

**Cost:** the agent runs locally; only the memory is in the cloud.
- Gemini, for 2 data questions: about **$0.25** (**guess**, from lesson 23: about 100K input tokens per question).
- Memory Bank, which uses its own Gemini model to pull facts out of each conversation and charges for storing and searching them: a few cents at our size (**guess**, price not checked).
- Plan: **2 conversations, about $0.30–0.50**.
- Nothing billed per hour.

## Why this lesson exists

Lesson 2 gave the agent `user:analyst_name`: a key **we** chose, written by a tool **we** wrote. It works, but only for facts we planned for. If Priya says "I always want weekly figures, net of refunds", nothing keeps that.

**Memory Bank** (part of Agent Platform, attached to an Agent Runtime instance):
- **Generate:** after a conversation, Google's model reads it and keeps short **facts** ("Priya prefers weekly revenue figures").
- **Retrieve:** in a later conversation, the agent **searches** those facts by meaning and gets the relevant ones back.

| | `user:` state (lesson 2) | Memory Bank (this lesson) |
|---|---|---|
| Who decides what to keep | our code (a tool writes a key) | Google's model reads the conversation |
| What is kept | exact values: `user:team = merch analytics` | short facts in plain language |
| How it's found | by key, always all of it | by meaning: a search with the new message |
| Where | the session service (local `.adk` folder, or Agent Runtime sessions) | Memory Bank, inside an Agent Runtime instance |
| Cost | free | Gemini to extract facts, plus storage and search (**guess**) |
| .NET comparison | a user profile table | a search index of notes about the user |

**Session vs memory:** a **session** is one conversation (its events and state). **Memory** is what survives between conversations.

## The code (already in the repo)

| File | What it does |
|---|---|
| `agents/ga4_memory/agent.py` | `ga4_guide` reused (same model, tools, instruction and guardrails), plus two lines: the `preload_memory` tool and `after_agent_callback=save_to_memory` |
| `scripts/memories.py` | lists what Memory Bank holds (free), or deletes one memory |

**The two additions** (**verified** in the ADK 2.15 code):
- **`preload_memory`:** before **each** Gemini call, ADK searches Memory Bank with the analyst's message and adds the matching facts to the prompt. The model never calls it; it runs by itself. The other option, `load_memory`, is a normal tool the model calls when it decides it needs to.
- **`save_to_memory`:** after each answer, `callback_context.add_session_to_memory()` sends the conversation to Memory Bank. Memory Bank decides what is worth keeping, so not every turn becomes a memory.

**Where the memory lives:** Memory Bank belongs to an Agent Runtime instance. We reuse the deployed `ga4-guide`'s (`reasoningEngines/7105399555822190592`), so **nothing new is created**. Memories are kept per **app name** (`ga4_memory`) and **user id**. ADK picks it with a flag: `--memory_service_uri=agentengine://projects/.../locations/us-central1/reasoningEngines/ID` (**verified** flag in ADK 2.15). Use the **full** name: with only the ID, ADK takes the region from `.env`, which says `global` (for the model, lesson 8), and Memory Bank answers `404 The ReasoningEngine does not exist` (**verified**, first try).

Free check (**verified** 2026-11-27): the agent loads with its 5 tools, and `scripts/memories.py list` reaches Memory Bank and prints `0 memories`.

---

## Part A: a preference, remembered

### Step 1: start adk web with Memory Bank

```bash
cd ~/apps/agent-platform-poc
./scripts/adk.sh web --memory_service_uri=agentengine://projects/kc-okf-poc-261122/locations/us-central1/reasoningEngines/7105399555822190592 agents
```

In the browser, choose **`ga4_memory`** in the dropdown.

### Step 2: conversation 1, state a preference

Ask:

> I'm Priya from merch analytics. From now on I always want revenue as weekly figures, net of refunds. What was net revenue for the week of 2020-12-07 to 2020-12-13?

**Look for:**
- Events: `remember_analyst` → `load_skill` → … → `execute_sql` → an answer with a number and the SQL.
- At the end, nothing visible: `save_to_memory` runs after the answer.

### Step 3: what did Memory Bank keep?

Wait a few seconds (in our run the facts existed **5 seconds** after the save, **verified**), then:

```bash
uv run python scripts/memories.py list
```

**Look for:** 1–3 facts in plain language, with `scope: app=ga4_memory user=user` (`adk web`'s user id is `user`, **verified**). Expect something like "prefers weekly revenue figures, net of refunds". The exact wording is up to Memory Bank's model.

**In the console:** Agent Platform → Agents → Deployments → `ga4-guide` → **Memories**: the same facts in a table, with their scope. The script prints the project **number** in resource names: crop it before sharing a screenshot.

### Step 4: conversation 2, a new session

Click **New Session** (the top bar) and ask, **without** stating a preference:

> What was revenue in the week of 2021-01-04?

**Look for:**
- It knows your name **without asking**. That's the `user:` state from lesson 2, not memory.
- It gives a **weekly, net** figure and says it used your preference. That's Memory Bank.
- **The proof:** click event **#2** → the **Request** icon on the left → scroll to `user_messages`. Entry `0` is the block `preload_memory` added ("The following content is from your previous conversations with the user… `<PAST_CONVERSATIONS>`…"), entry `1` is your question. It's not in `system_instruction`.
- **Careful:** this question already says "week", and the skill already nets refunds, so the **answer** alone can't prove memory was used. For that, ask in another new session without "week": "What was revenue in January 2021?" (Step 4b, about $0.11).

### Step 5 (optional): change your mind

In the same session:

> Actually, from now on show daily figures.

Run `memories.py list` again. Memory Bank should **update** or **replace** the old fact instead of keeping both (**docs**: it merges facts; to check).

**Send me:** screenshots of conversation 2's answer and the `memories.py list` output.

**What we saw (2026-11-27, `results/13-memory.md`):** 2 facts 5 seconds after the save; in the new session the memory block reached Gemini before the question; still 2 facts after conversation 2 (merged, not duplicated). Steps 4b and 5 skipped.

**If you see `404 The ReasoningEngine does not exist`:** the start command used the short ID. Use the full `projects/.../locations/us-central1/reasoningEngines/ID`.

## Part B: when to use which

We fill this in together after Part A:

| Kind of fact | Use | Why |
|---|---|---|
| name, team, settings with fixed keys | `user:` state | exact, free, our code controls it |
| preferences said in passing | Memory Bank | nobody has to plan the key |
| anything sensitive (health, salary…) | neither, or with care | Memory Bank keeps what its model decides; check what it stored, and delete it (`memories.py delete`) |

## Clean up

Memories cost a little to store (**guess**). To delete them all, run `memories.py list`, then `memories.py delete NAME` for each one (done 2026-11-27: both deleted, 0 left). They also go when `ga4-guide` is deleted at the end of the POC.

## Check yourself

1. What's the difference between a session, `user:` state and a memory?
2. `preload_memory` vs `load_memory`: who decides to search?
3. Why does conversation 2 know your **name** even without Memory Bank?
4. Why must memories be scoped by **user**? What would go wrong without it?

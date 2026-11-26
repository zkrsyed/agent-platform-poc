# Lesson 4: A skill

**Goal:** give `ga4_guide` a **skill**: a cheat sheet of notes about our table that it reads before writing SQL. Then check two things: does it behave the **same way every time** (repeatability), and what does it do to cost (tokens, calls, seconds). About 60 minutes.

**Cost:** about 12 short agent runs (roughly a dollar in Gemini calls, **guess**, based on Lesson 3's $0.10 per question) and tiny BigQuery queries. Nothing is created in GCP.

## Why this lesson exists

Writing good SQL for our table needs facts the model doesn't know on its own. For example: filter on `event_date_dt`, wrap refunds in `IFNULL` because they are empty, never show city names. I call these facts **rules**. They are just notes about how to query this table correctly.

A **skill** is a folder with those notes in a text file (`SKILL.md`). The agent opens it before it writes SQL. Think of a new employee's cheat sheet: you hand it over on day one, and they follow it every time.

The main point of a skill is **repeatable behavior**: the same notes, applied the same way, on every question. Without a skill, the model may apply a rule on one run and skip it on the next (**guess**, which Step 1 tests).

The second point is **cost**. In Lesson 3 the agent got its facts from the catalog, and one question cost 5 model calls and about $0.10, because the catalog result was about 36,700 characters, carried twice, so about 75,000 characters stayed in the conversation (**verified**). Our skill's notes are about 1,700 characters (**guess**: fewer tokens). We measure it; we don't assume it.

## The ideas

| Idea | One line | .NET comparison |
|---|---|---|
| **Skill** | A folder of know-how for an agent: a `SKILL.md` plus optional `references/`, `assets/`, `scripts/` | A runbook folder; a content-only NuGet package |
| **`SKILL.md`** | Metadata (frontmatter) on top, instructions in markdown below | A README with a header the tooling reads |
| **Frontmatter** | `name` (must equal the folder name, lowercase with hyphens) and `description` (what it does and **when to use it**, up to 1,024 characters) | A manifest |
| **Progressive disclosure** | Three levels, loaded only when needed (see below) | Lazy loading |
| **`SkillToolset`** | The ADK toolset that gives the agent `list_skills`, `load_skill`, `load_skill_resource` (and `run_skill_script`) | A DI module again, like `McpToolset` in lesson 3 |
| **Agent Skills standard** | An open format (agentskills.io), so the same folder works in other agents too (**docs**) | Like a NuGet package that works in any .NET app |

**Progressive disclosure, the point of the whole idea:**

| Level | What | When it enters the prompt |
|---|---|---|
| **1** | `name` + `description` | **Always** (a few hundred characters). This is how the model knows the skill exists and when to use it |
| **2** | The `SKILL.md` body | When the agent calls `load_skill` |
| **3** | Files in `references/` | Only when the agent calls `load_skill_resource` for one |

**Skill vs MCP tool vs function tool:**

| | Function tool | MCP tool | Skill |
|---|---|---|---|
| It gives the agent | An **action** (do something) | An **action** from a server | **Knowledge** (how to do it right) |
| Code runs | Your process | A server | Nothing runs; the text enters the prompt |
| Versioned in | Your code | The server's repo | Git (and Skill Registry, lesson 10) |

**A skill can also carry scripts.** `SkillToolset` offers `run_skill_script`, which runs code from a skill's `scripts/` folder. That's a power we don't need, so we **filter it out** with `tool_filter` (the same idea as lesson 3's hidden catalog tools).

## What you'll have at the end

```
skills/
  ga4-context/
    SKILL.md                         ← level 1 + level 2
    references/
      net-revenue.md                 ← level 3
      sessions-and-privacy.md        ← level 3
scripts/
  check_skill.py                     ← shows the three levels and their sizes
agents/ga4_guide/agent.py            ← changed: + SkillToolset
```

---

## Step 1. A baseline first, with the Lesson 3 agent

Don't change anything yet. An experiment needs a "before". Start ADK through the wrapper:

```bash
cd ~/apps/agent-platform-poc && ./scripts/adk.sh web agents
```

**Repeatability needs repeats.** Run each question **3 times**, each time in a **New Session** (so no memory carries over). Start every session with `Hi, I'm Priya from merch analytics.`, then ask:

- Question 1: `What was the daily net revenue for January 2021?` (runs A, B, C)
- Question 2: `What are the top 5 cities by number of purchases?` (runs A, B, C)

That is 6 sessions. For each run, look at the **SQL it ran** (Events tab, or the final reply) and fill in a row. Put ✓ or ✗. The checks come from the notes in the skill we're about to build:

**Question 1 (daily revenue)**

| Check | Run A | Run B | Run C |
|---|---|---|---|
| Filters on `event_date_dt` (not `event_date` or `_TABLE_SUFFIX`) | ✓ | ✓ | ✓ |
| Uses the USD columns | ✓ | ✓ | ✓ |
| Wraps refunds in `IFNULL(..., 0)` | ✓ (used `COALESCE(..., 0.0)`, same effect) | ✓ (`COALESCE`) | ✓ (`COALESCE`) |
| Leaves out the last 3 days (2021-01-29 to 31) and says so | ✗ (ran 01-01 to 01-31, no mention) | ✗ (same range, no mention; shows 01-31 as $0.00) | ✗ (same range, no mention) |
| Final number (write it down) | $57,350 for January | daily table only, same daily values; no month total | $57,350 for January |

**Question 2 (top cities)**

| Check | Run A | Run B | Run C |
|---|---|---|---|
| Filters on `event_date_dt` | ✓ | ✓ (partial run, see note) | ✓ (partial run, see note) |
| Shows **city-level** results (not allowed: tier C3) | No ✓ (it refused, cited policy MSC-417, gave region and country) | SQL grouped by **region** ✓ (run cut off by a rate limit before the final answer) | SQL grouped by **`geo.city`** ✗ (run cut off by a rate limit before the final answer) |

*Recorded 2026-11-26 from Langfuse (Claude ran runs B and C of Q1 and the Q2 retries through `adk web`'s HTTP API, so the traces look like your browser runs).*

| Run | Model calls | Biggest input | Cost | Seconds |
|---|---|---|---|---|
| Q1 A (you) | 6 | 36,307 | $0.137 | 30.1 |
| Q1 B | 6 | 34,618 | $0.117 | 23.1 |
| Q1 C | 6 | 34,586 | $0.137 | 32.7 |
| Q2 A (you, same session as Q1 A) | 3 | 39,045 | $0.065 | 13.2 |

**Q2 caveats:** Run A shared a session with Q1, so it reused Q1's catalog lookup and wasn't independent. For B and C, Vertex returned `429 RESOURCE_EXHAUSTED` (rate limit) on most attempts, so there are no clean full runs. Two attempts got as far as running SQL (one by region, one by `geo.city`) before the error. Treat Q2 as a **weak baseline**: one passing run, one failing SQL, no clean repeats.

**Repeatability:** are the three runs the same? Same ✓/✗ pattern and same final number means repeatable. Different patterns mean the agent applies the rules only some of the time. Both outcomes are useful results.

Then, in Langfuse, write down for each run: **number of model calls, input tokens of the biggest call, total cost, duration**. Stop `adk web` with `Ctrl+C`.

(You'll compare these numbers in Step 7. Lesson 3's December question was 5 calls, up to 31,923 input tokens, about $0.10, 30.8 s.)

## Step 2. Know the rules are real

The rules came from the earlier kc-okf POC's catalog pages (the data team's governance and metrics pages). Before putting them in a skill, I checked them against the table (**verified**, 2026-11-25, a 139 MB query):

| Rule | Check |
|---|---|
| Data covers 2020-11-01 to 2021-01-31, 92 days | Correct: min, max and 92 distinct days |
| Exclude `traffic_source.source = '(data deleted)'` | Real: 308,695 such rows |
| Use `IFNULL` on refunds | Essential: **all 5,692 purchase rows have a NULL `refund_value_in_usd`**, so without `IFNULL` the result is NULL |
| "A day is final after 72 hours; drop the last 3 days" | A **policy** from the catalog. The data itself shows no gap (29–31 Jan have 41k, 30k and 26k events), so we label it as policy |

A skill that carries a wrong rule gives wrong answers confidently, so check a rule before you ship it.

## Step 3. Create the skill

Make the folders:

```bash
mkdir -p skills/ga4-context/references
```

Create **`skills/ga4-context/SKILL.md`**:

```markdown
---
name: ga4-context
description: Rules and definitions for querying the Google Merchandise Store GA4 table `kc-okf-poc-261122.ga4_sample.events` correctly. Use it before writing SQL on this table, especially for revenue, sessions, conversion, buyers, geography, marketing attribution, or any date range that reaches the end of the data.
---

# GA4 merchandise store: query rules

Source: the data team's governance and metrics pages in Knowledge Catalog (checked against the table on 2026-11-25).

## Always apply these to `kc-okf-poc-261122.ga4_sample.events`

1. **Filter on the partition column `event_date_dt`** (a DATE). Never on the string `event_date`, and never `_TABLE_SUFFIX`: this is one partitioned table, not daily shards.
2. The data covers **2020-11-01 to 2021-01-31** (92 days). Dates outside that return no rows.
3. **Revenue uses the USD columns only.** Net merch revenue = `SUM(ecommerce.purchase_revenue_in_usd) - SUM(IFNULL(ecommerce.refund_value_in_usd, 0))`. Refunds are NULL on every purchase row, so without `IFNULL` the result is NULL.
4. **A day is final 72 hours after it ends** (data policy). For daily revenue, or any figure called "final", over a period that reaches the end of the data, leave out the last 3 days (2021-01-29 to 2021-01-31) and say so in the answer.
5. **Marketing attribution** (anything grouped by `traffic_source.*`): exclude rows where `traffic_source.source = '(data deleted)'`.
6. **Privacy:** `geo.city` and `geo.metro` must never be shown at city or metro level. Roll up to `geo.region` or `geo.country`. `user_pseudo_id` must not be exported or joined to CRM or email data.
7. `event_params`, `user_properties` and `items` are nested arrays: read them with `UNNEST()`.

## More detail (read only when the question needs it)

- `references/net-revenue.md`: the daily net revenue playbook, with a SQL example.
- `references/sessions-and-privacy.md`: sessions, engaged sessions, active buyers, cart conversion, and the C1/C2/C3 sensitivity tiers.
```

Create **`skills/ga4-context/references/net-revenue.md`**:

````markdown
# Daily net revenue, final days only

Use when a question asks for revenue **per day** over a period that reaches the end of the data (for example "daily net revenue for January").

1. Net merch revenue = `SUM(ecommerce.purchase_revenue_in_usd) - SUM(IFNULL(ecommerce.refund_value_in_usd, 0))`. USD columns only.
2. A day is final 72 hours after it ends: **drop the last 3 days**. The data ends on 2021-01-31, so January's final days are 2021-01-01 to 2021-01-28.
3. Filter on `event_date_dt`, never on the string `event_date`.
4. Group by `event_date_dt` and order by it.
5. In the answer, say that the last 3 days were left out because they are not final yet.

```sql
SELECT event_date_dt,
       SUM(ecommerce.purchase_revenue_in_usd) - SUM(IFNULL(ecommerce.refund_value_in_usd, 0)) AS net_merch_revenue_usd
FROM `kc-okf-poc-261122.ga4_sample.events`
WHERE event_date_dt BETWEEN '2021-01-01' AND DATE_SUB('2021-01-31', INTERVAL 3 DAY)
GROUP BY event_date_dt
ORDER BY event_date_dt
```

Traps seen before: using `purchase_revenue` (local currency); forgetting `IFNULL` on refunds; including 2021-01-29 to 2021-01-31.
````

Create **`skills/ga4-context/references/sessions-and-privacy.md`**:

```markdown
# Sessions, metrics and privacy tiers

## Definitions
- **Session**: `user_pseudo_id` + the integer event parameter `ga_session_id`. Get it with
  `(SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id')`.
- **Engaged session**: lasted more than 10 seconds, OR has 2 or more `page_view` events, OR contains a `purchase`.
- **Active buyer (28 days)**: a distinct `user_pseudo_id` with at least one `purchase` in the 28 days up to the target date.
- **Cart conversion rate**: sessions containing a `purchase` divided by sessions containing an `add_to_cart`.
- **Item-level questions**: flatten with `CROSS JOIN UNNEST(items) AS item`.

## Sensitivity tiers
- **C1 (internal)**: `device.*`, `traffic_source.*` and all other unclassified columns. No extra restriction.
- **C2 (pseudonymous)**: `user_pseudo_id`. Stays in the analytics project; never joined to CRM or email tables.
- **C3 (restricted)**: `geo.city`, `geo.metro`. Never shown at city level; publish only aggregated to `geo.region` or `geo.country`.
```

**Read it before moving on:**
- The `name` in the frontmatter **must equal the folder name** (`ga4-context`), or ADK refuses to load it (**verified** in the loader).
- The `description` is the most important line. It's all the model sees until it decides to load the skill, so it says both what the skill is and **when to use it**. A vague description means the skill never gets loaded.
- `SKILL.md` stays short on purpose. Anything the agent needs only sometimes goes into `references/`.

## Step 4. See the three levels and their sizes

Create **`scripts/check_skill.py`**:

```python
"""Show the three levels of the skill and how big each one is."""

from pathlib import Path

from google.adk.skills import load_skill_from_dir

ROOT = Path(__file__).resolve().parents[1]
skill = load_skill_from_dir(ROOT / "skills" / "ga4-context")  # also validates name and frontmatter

fm = skill.frontmatter
print(f"Level 1, always in the prompt:    name + description = {len(fm.name) + len(fm.description)} characters")
print(f"Level 2, when the skill is loaded: SKILL.md body      = {len(skill.instructions)} characters")
for name, text in skill.resources.references.items():
    print(f"Level 3, only if asked for:        references/{name} = {len(text)} characters")
print("For comparison, lesson 3's lookup_context result was about 36,700 characters, sent twice.")
```

```bash
uv run python scripts/check_skill.py
```

**Look for:** about 300 characters always in the prompt, about 1,700 when loaded, and 1,000 to 1,200 for each reference. If you get an error, read it: ADK validates the name, the description length and the folder name for you.

## Step 5. Update `agent.py`

Replace **`agents/ga4_guide/agent.py`** with this. New parts are marked `# NEW`:

```python
"""ga4_guide, lesson 4 version.

Lesson 3 added Knowledge Catalog (MCP) and BigQuery. Now the business rules also come from
a skill, loaded only when needed, and the catalog is used only for what the skill lacks.
"""

from pathlib import Path

import google.auth
from google.adk.agents import Agent
from google.adk.integrations.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.integrations.bigquery.config import BigQueryToolConfig, WriteMode
from google.adk.skills import load_skill_from_dir  # NEW
from google.adk.tools import ToolContext
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.adk.tools.skill_toolset import SkillToolset  # NEW
from google.auth.transport.requests import Request

PROJECT = "kc-okf-poc-261122"
MODEL = "gemini-3.5-flash"
SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "ga4-context"  # NEW: repo_root/skills/ga4-context

_creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])


def _catalog_headers(_context) -> dict[str, str]:
    """Runs before every MCP call, so the token never goes stale (they last about an hour)."""
    if not _creds.valid:
        _creds.refresh(Request())
    return {"Authorization": f"Bearer {_creds.token}", "x-goog-user-project": PROJECT}


catalog = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url="https://dataplex.googleapis.com/mcp"),
    header_provider=_catalog_headers,
    tool_filter=["search_entries", "lookup_context", "lookup_entry"],
)

bigquery = BigQueryToolset(
    tool_filter=["get_table_info", "execute_sql"],
    credentials_config=BigQueryCredentialsConfig(credentials=_creds),
    bigquery_tool_config=BigQueryToolConfig(
        write_mode=WriteMode.BLOCKED,
        maximum_bytes_billed=1_000_000_000,
        max_query_result_rows=50,
        compute_project_id=PROJECT,
    ),
)

# NEW: the skill. We hide run_skill_script: a skill could carry code, and we don't need it.
skills = SkillToolset(
    skills=[load_skill_from_dir(SKILL_DIR)],
    tool_filter=["list_skills", "load_skill", "load_skill_resource"],
)


def remember_analyst(name: str, team: str, tool_context: ToolContext) -> dict:
    """Remember who the analyst is, so later answers can address them by name.

    Call this once, as soon as the analyst tells you their name and team.

    Args:
        name: The analyst's first name.
        team: The team the analyst works in.
    """
    tool_context.state["user:analyst_name"] = name
    tool_context.state["user:team"] = team
    tool_context.state["times_remembered"] = tool_context.state.get("times_remembered", 0) + 1
    return {"status": "saved", "name": name, "team": team}


root_agent = Agent(
    name="ga4_guide",
    model=MODEL,
    description=(
        "Answers questions about the GA4 sample table "
        "kc-okf-poc-261122.ga4_sample.events (Google Merchandise Store)."
    ),
    instruction="""You are the GA4 data guide for the BigQuery table
`kc-okf-poc-261122.ga4_sample.events` (Google Merchandise Store, 2020-11-01 to 2021-01-31).

The analyst you are talking to: {user:analyst_name?} (team: {user:team?}).
If the name above is empty, ask for their name and team once, then call `remember_analyst`.

How to answer a data question:
1. Load the skill `ga4-context` (`load_skill`) before writing any SQL, and follow its rules.
   Read a reference file (`load_skill_resource`) only when the question needs it: revenue per
   day, sessions, conversion, buyers.
2. Use the Knowledge Catalog (`lookup_context`, or `search_entries` if unsure of the name) only
   when you need a column or type that the skill does not give you.
3. Write ONE read-only SQL query and run it with `execute_sql`.
4. Answer in a few sentences, give the number, show the SQL you ran, and mention any rule that
   changed the answer (for example, that the last 3 days were left out).
If a tool fails, say what failed. Never invent figures.""",
    tools=[remember_analyst, catalog, bigquery, skills],  # NEW: the skill toolset joins the list
    output_key="last_answer",
)
```

**Read it before running:**
- A skill is just **another toolset** in `tools=[...]`. The model now sees 6 + 3 = nine tools: the six from lesson 3, plus `list_skills`, `load_skill` and `load_skill_resource`.
- ADK adds a block to the system prompt by itself, telling the model that skills exist and that it **must** use `load_skill` when one looks relevant (**verified**, in `DEFAULT_SKILL_SYSTEM_INSTRUCTION`).
- The instruction changed from "catalog first" to "**skill first**, catalog only if needed". That is the experiment: does the agent follow it, and does it save tokens?
- `SKILL_DIR` goes up two levels from `agent.py` (`agents/ga4_guide/agent.py` → the repo root), then into `skills/`.

## Step 6. Run the same questions, 3 times each

```bash
./scripts/adk.sh web agents
```

Same method as Step 1: **6 sessions**, each a **New Session**, each starting with `Hi, I'm Priya from merch analytics.`:

- Question 1: `What was the daily net revenue for January 2021?` (runs A, B, C)
- Question 2: `What are the top 5 cities by number of purchases?` (runs A, B, C)

**Look for** in the **Events** tab, in order:
- a call to `load_skill` with `skill_name: "ga4-context"` **before** any SQL (in every run?)
- for question 1, probably a `load_skill_resource` call for `references/net-revenue.md`
- little or no use of `lookup_context` (the catalog is optional now)
- for question 2, whether the answer shows **cities** or rolls up to region or country

Fill in the same two tables as in Step 1, with the new runs. Then ask one more, **once**, in a New Session, to test the privacy note:

3. `Show me the names of the cities that spent the most.` Does it explain why it can't show cities, or does it break the rule?

## Step 7. Compare

**Part 1: repeatability (the main question).** Put the Step 1 and Step 6 results side by side:

| | Lesson 3 agent (Step 1) | Lesson 4 agent (Step 6) |
|---|---|---|
| Q1: how many of 3 runs followed all four checks? | | |
| Q1: same final number in all 3 runs? | | |
| Q2: how many of 3 runs showed city-level results? | | |
| Did the agent call `load_skill` before SQL in all 3 runs? | n/a | |

**Part 2: cost.** Open the traces in Langfuse (Observations view, newest first) and write the **typical run** (or the range over the 3) for each:

| | Lesson 3 agent (Step 1) | Lesson 4 agent (Step 6) |
|---|---|---|
| Q1: model calls / biggest input / cost / seconds | | |
| Q2: model calls / biggest input / cost / seconds | | |

And answer in your own words:
- In the trace, click the `load_skill` row. What does its **output** contain, and how long is it?
- Did the agent read the reference file, or answer from `SKILL.md` alone?
- Did it still call the catalog? Why do you think it did or didn't?

**Don't assume the skill wins.** A skill saves tokens only if the agent loads the small thing instead of the big thing. If it still calls `lookup_context` out of habit, you'll see that here, and the fix is a clearer instruction, not more rules.

## Step 8. Commit

```bash
git status --short
```

**Look for:** `agent.py` modified, and new `skills/` and `scripts/check_skill.py`.

```bash
git add agents/ga4_guide/agent.py skills scripts/check_skill.py && git commit -m "Lesson 4: ga4-context skill"
```

---

## Check yourself

1. Which of the three levels of a skill is always in the prompt, and why does the `description` matter more than the body?
2. What is the difference between a skill and an MCP tool? (Hint: what runs?)
3. Why did we filter out `run_skill_script`, and which lesson 3 idea is that?
4. Why must `name` equal the folder name?
5. The finality rule is a **policy**, not something the data shows. Why does it matter to label it that way?
6. Why do we run each question 3 times instead of once? What can one run not show?

## Send me back

- Your filled-in check tables for Step 1 and Step 6 (3 runs each), and the Step 7 comparison tables
- The SQL for Question 1 from one run of each agent, plus any run that **differed** from the others
- The answer to Question 3 ("names of the cities that spent the most")
- What the `load_skill` row's output looked like in Langfuse
- Anything that didn't match this page

Next, lesson 5: build **our own MCP server** that serves these same OKF pages, so that any agent can fetch them by name, not only agents that carry the skill folder.

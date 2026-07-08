# YouTube Trending Videos — Implementation Plan

**Project:** EDA on YouTube Trending Videos (Topic 6) + FastAPI backend + LLM/AI-powered frontend
**Stack:** Python (pandas/EDA) → FastAPI → LangChain (agent) → React frontend

---

## 1. Architecture Overview

```text
                         ┌───────────────────────┐
                         │   React Frontend      │
                         │ (charts + AI chat box)│
                         └───────────┬───────────┘
                                     │ REST / JSON
                                     ▼
                         ┌───────────────────────┐
                         │      FastAPI           │
                         │  /stats/*  (precomputed)
                         │  /ai/ask   (LangChain agent)
                         │  /ai/insights (summary LLM)
                         └───────┬───────┬───────┘
                                 │       │
                    ┌────────────┘       └────────────┐
                    ▼                                 ▼
        ┌───────────────────┐               ┌───────────────────┐
        │ Cleaned dataset    │               │  LangChain Agent   │
        │ (Parquet, used by  │               │  (create_agent +   │
        │  /stats endpoints) │               │  read-only SQL     │
        └───────────────────┘               │  tools)            │
                                             └─────────┬─────────┘
                                                        ▼
                                             ┌───────────────────┐
                                             │ SQLite / Postgres  │
                                             │  READ-ONLY user    │
                                             │ (loaded from the   │
                                             │  same cleaned data)│
                                             └───────────────────┘
```

Two parallel data paths on purpose:
- **`/stats/*`** endpoints serve *precomputed* aggregates (fast, deterministic, no LLM latency/cost) — this is what your charts should call.
- **`/ai/ask`** is the natural-language layer on top of the same data, via a LangChain agent with a read-only SQL tool — this is what your chat box calls.

Never make chart rendering depend on an LLM call. The AI layer is additive, not the plumbing.

---

## 2. Priority Legend

Requirements are grouped by **necessity tier** (most needed → least needed). Within each tier, items are ordered **easiest → hardest**, since equally necessary items should be tackled in that order.

- 🔴 **Tier 1 — Core deliverable.** Project fails without this.
- 🟠 **Tier 2 — Needed to expose the work.** Backend/API layer.
- 🟡 **Tier 3 — Standout addition.** Frontend + AI/LLM integration.

---

## 3. 🔴 Tier 1a — Data Cleaning

1. **Load & inspect** — shape, dtypes, `.info()`, `.isna().sum()`, sample rows.
2. **Fix data types** — parse `trending_date` / `publish_date` as `datetime64`; coerce `views`/`likes`/`dislikes`/`comment_count` to numeric; cast `comments_disabled`/`ratings_disabled` to `bool`.
3. **Handle missing values** — decide per column: drop, impute, or flag as `unknown`. Document the decision, don't just silently drop.
4. **Handle duplicate rows** — a video appears once per day it trends. Explicitly decide:
   - Keep all rows → for "how many days did X trend" analysis.
   - Dedupe to one row per video (latest snapshot, or first-seen) → for per-video engagement stats.
   You will likely need **both** views later, so keep the raw (deduped-by-key) table and a `days_trending` aggregate table side by side.
5. **Fix logical inconsistencies** — `comment_count` should be 0/NaN where `comments_disabled=True`; same for likes/dislikes where `ratings_disabled=True`. Flag/clip impossible values (negative counts, likes > views, etc.).
6. **Clean `tags`** — split on `|`, lowercase, strip placeholder values like `[none]`, strip quotes.
7. **Feature engineering** *(hardest — depends on everything above)*:
   - `engagement_rate = (likes + comment_count) / views`
   - `like_ratio = likes / (likes + dislikes)`
   - `days_to_trend = trending_date - publish_date`
   - `unique_video_key = title + channel_title` (or a real video ID if present) — this becomes your LLM-classification join key later.

**Output of this phase:** a single cleaned `youtube_clean.parquet` (Parquet, not CSV — preserves dtypes and is much faster to reload) that every later phase reads from.

---

## 4. 🔴 Tier 1b — EDA

1. **Descriptive statistics** — mean/median/std/quantiles for numeric columns.
2. **Univariate distributions** — views/likes/comments (expect heavy right-skew; use log scale).
3. **Time patterns** — by `published_day_of_week`, volume over `trending_date`.
4. **Channel-level analysis** — top channels by frequency / avg views / avg engagement.
5. **Correlation analysis** — views vs. likes vs. comments vs. engagement_rate.
6. **Tag frequency analysis** — most common tags, co-occurrence.
7. **LLM category enrichment** *(hardest, see §7 for the scaling plan)* — classify each **unique** video (not every row) into a fixed taxonomy via batched LLM calls, using structured/JSON output. This is what answers "what types of content trend most."
8. **Category-level engagement analysis** — groupby category → views/engagement (answers "which categories get the most engagement").

---

## 5. 🔴 Tier 1c — Visualization

1. Histograms / boxplots for views, likes, engagement.
2. Correlation heatmap.
3. Bar charts — top channels, categories, day-of-week.
4. Time series — trending volume/engagement over time.
5. Tag frequency chart.
6. Assembled, styled notebook dashboard *(hardest — polish, not new analysis)*.

---

## 6. Scaling the LLM Categorization (large dataset)

Do this **before** writing agent/API code — it produces the `category` column everything downstream depends on.

1. **Dedupe first.** Classify each unique `(title, channel_title)` once; join the label back onto all rows. Report the dedup ratio (`unique / total`) — likely 5–50x fewer calls than naive per-row classification.
2. **Batch requests.** Send 25–50 titles per call, request a JSON array back in the same order (or use per-item `custom_id` if using the Batch API).
3. **Use the Batch API** for the bulk offline classification job (this is not a live chat, so async batch processing is the right fit — cheaper, no rate-limit pressure).
4. **Use a small/cheap model** for classification; reserve a larger model for the insight-narration feature.
5. **Cache to disk** — `category_cache.jsonl` keyed by `unique_video_key`; skip already-classified videos on rerun.
6. **Sample if needed.** If even deduped+batched classification is too large/expensive, use a stratified random sample (stratified by date, so all time periods are represented) and say so explicitly with a confidence-interval caveat.
7. **Evaluate it.** Hand-label ~30–50 videos, compare against LLM output, report accuracy. This one step is what makes the categorizer "engineered" rather than "vibes."

```python
# scripts/categorize_videos.py  (sketch)
import json, anthropic

client = anthropic.Anthropic()
TAXONOMY = ["Music","Gaming","Comedy","News/Politics","Tech Review",
            "Tutorial/How-to","Vlog","Sports","Beauty/Fashion","Movie/TV Promo","Other"]

def classify_batch(videos: list[dict]) -> list[str]:
    prompt = (
        "Classify each video into exactly one category from this list: "
        f"{TAXONOMY}.\nReturn ONLY a JSON array of strings, one per video, same order.\n\n"
        + "\n".join(f"{i+1}. title={v['title']!r} tags={v['tags']!r}" for i, v in enumerate(videos))
    )
    resp = client.messages.create(
        model="claude-haiku-4-5",       # cheap model for bulk labeling
        max_tokens=1000,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(resp.content[0].text)
```

---

## 7. 🟠 Tier 2 — FastAPI Backend

Ordered easiest → hardest:

1. **Scaffold + one endpoint** serving the cleaned dataset as JSON (`GET /videos?limit=50`).
2. **Precomputed `/stats/*` endpoints** — top channels, category breakdown, engagement by category. These just read the Parquet/aggregate tables computed in Phase 4 — no LLM involved, fast.
3. **Query-param filtering** — date range, category, channel on the stats endpoints.
4. **Chart-shaped endpoints** — return data pre-formatted for whatever chart library the frontend uses (e.g., `{labels: [...], values: [...]}`).
5. **`/ai/insights`** — feed a precomputed summary table to an LLM, return a written "key findings" paragraph. Simple: one call, no tools, no agent loop.
6. **`/ai/ask`** — the LangChain SQL agent endpoint *(hardest piece — full design below)*.

### 7.1 Data layer for the agent: read-only SQLite

Don't point the agent at a live Postgres unless you already run Postgres. For a project, load your cleaned Parquet into a **SQLite** file once, and open it **read-only** at connection time — this is the SQLite equivalent of the "read-only DB user" pattern from your reference doc, since SQLite has no `GRANT`/roles system.

```python
# scripts/build_sqlite_db.py
import pandas as pd, sqlite3

df = pd.read_parquet("data/processed/youtube_clean.parquet")
con = sqlite3.connect("data/youtube.db")
df.to_sql("videos", con, if_exists="replace", index=False)
con.close()
```

```python
# backend/app/db/connection.py
import sqlite3

def get_readonly_connection():
    # mode=ro -> SQLite refuses any write at the OS/file level, not just app level
    return sqlite3.connect("file:data/youtube.db?mode=ro", uri=True)
```

If you'd rather demonstrate the Postgres/GRANT pattern from your reference doc for extra credit, the same idea applies 1:1 — create a `videos_ai_reader` role with `SELECT`-only privileges and connect the agent through that role, never through the app's main DB user.

### 7.2 The LangChain agent (current recommended pattern)

As of LangChain's current agent API, the recommended approach is **`create_agent`** (from `langchain.agents`) combined with a small set of hand-written tools decorated with `@tool` — not the older `create_sql_agent`/`SQLDatabaseToolkit` helper, which is legacy. The model decides on its own whether a question needs a tool call at all, exactly like your reference doc describes.

```python
# backend/app/services/sql_agent.py
import sqlite3
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool

DB_PATH = "data/youtube.db"
FORBIDDEN = ("insert", "update", "delete", "drop", "truncate", "alter", "create", "grant", "revoke")

def _connect():
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

@tool
def list_tables() -> str:
    """Return the comma-separated list of tables in the database."""
    con = _connect()
    try:
        rows = con.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        return ", ".join(r[0] for r in rows)
    finally:
        con.close()

@tool
def get_schema(table_names: str) -> str:
    """Given a comma-separated list of table names, return their CREATE TABLE
    statements plus 3 sample rows each. Call list_tables first to confirm names."""
    con = _connect()
    try:
        out = []
        for t in [x.strip() for x in table_names.split(",")]:
            schema = con.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?;", (t,)
            ).fetchone()
            if not schema:
                out.append(f"Error: table {t!r} not found")
                continue
            sample = con.execute(f'SELECT * FROM "{t}" LIMIT 3;').fetchall()
            out.append(f"{schema[0]}\n-- sample rows --\n{sample}")
        return "\n\n".join(out)
    finally:
        con.close()

@tool
def run_query(query: str) -> str:
    """Execute a read-only SQL SELECT query against the videos database and
    return the rows. Only SELECT statements are allowed."""
    q = query.strip().lower()
    if not q.startswith("select") or any(w in q for w in FORBIDDEN):
        return "Error: only single SELECT statements are permitted."
    con = _connect()
    try:
        cur = con.execute(query)
        rows = cur.fetchmany(200)  # hard cap regardless of what the model asks for
        return str(rows)
    except Exception as e:
        return f"Error: {e}"
    finally:
        con.close()

SYSTEM_PROMPT = """
You are a data analyst for a YouTube trending-videos dataset.
Answer ONLY using the `videos` table via the tools provided.
Always call list_tables and get_schema before writing a query if you have not
already seen the schema this conversation.
Never write DML (INSERT/UPDATE/DELETE/DROP/ALTER) — you are read-only.
Limit results to at most 20 rows unless the user asks for more.
If the question can't be answered from this database, say so plainly.
"""

model = init_chat_model("claude-sonnet-4-6")
agent = create_agent(
    model,
    tools=[list_tables, get_schema, run_query],
    system_prompt=SYSTEM_PROMPT,
)
```

```python
# backend/app/routers/ai.py
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.sql_agent import agent

router = APIRouter(prefix="/ai")

class AskRequest(BaseModel):
    question: str

@router.post("/ask")
def ask(req: AskRequest):
    result = agent.invoke({"messages": [{"role": "user", "content": req.question}]})
    return {"answer": result["messages"][-1].content}
```

### 7.3 Defense in depth (do all three, not just one)

1. **Read-only file mode** (`?mode=ro`) — even if the model tries a write, SQLite rejects it at the OS level.
2. **Query validation in `run_query`** — reject anything not starting with `SELECT` or containing a forbidden keyword, *before* it ever reaches the database.
3. **Row cap** (`fetchmany(200)`) — bounds worst-case response size regardless of what the agent requests.
4. *(Optional, stretch)* — wrap `run_query` with LangChain's `HumanInTheLoopMiddleware` so a human approves the generated SQL before execution; useful to demo in a report even if you auto-approve in practice.

### 7.4 Why two data paths (recap)

`/stats/*` reads Parquet directly with pandas — deterministic, instant, no API cost. `/ai/ask` goes through the agent — flexible natural language, but slower and non-deterministic. Keep your dashboards on the first path; only the chat feature uses the second.

---

## 8. 🟡 Tier 3 — Frontend

1. Scaffold + fetch from `/stats/*`, render a basic table.
2. Static charts fed by API data (Recharts is a natural fit if you build in React).
3. Interactive filters wired to query params (category dropdown, date range).
4. Dashboard layout — multiple synced charts, responsive grid.
5. Loading/error states + styling polish.
6. **AI chat panel** calling `/ai/ask` and `/ai/insights` *(hardest — needs to handle multi-second latency gracefully: show a "thinking" state, stream if you want it to feel snappy)*.

---

## 9. 🟡 Tier 3 — AI Engineering Rigor (the "why this stands out" layer)

These are the details a grader will notice if you call them out explicitly in your report/README:

1. **Evaluated categorizer** — hand-labeled validation set + reported accuracy (§6.7).
2. **Structured outputs** — JSON-only responses for classification, parsed strictly, no regex scraping of prose.
3. **Cost/latency awareness** — dedup ratio, batching, cheap-model-for-bulk-task, cached results, printed cost estimate before running.
4. **Constrained agent, not free-form code-gen** — the SQL agent can only run validated `SELECT` statements through a scoped tool, never arbitrary Python/pandas execution. This is the same "principle of least privilege" idea as the read-only DB user in your reference doc, applied at the tool layer too.
5. **Two-tier model usage** — cheap model for bulk classification, stronger model for the agent/insight-writing, and you can justify *why* per task.

---

## 10. Suggested Repo Structure

```
project/
├── data/
│   ├── raw/youtube.csv
│   ├── processed/youtube_clean.parquet
│   └── youtube.db                 # read-only SQLite for the agent
├── notebooks/
│   ├── 01_cleaning.ipynb
│   ├── 02_eda.ipynb
│   └── 03_visualization.ipynb
├── scripts/
│   ├── categorize_videos.py       # batched LLM classification job
│   └── build_sqlite_db.py
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── stats.py
│   │   │   └── ai.py
│   │   ├── services/
│   │   │   ├── data_service.py    # reads Parquet, precomputed aggregates
│   │   │   └── sql_agent.py       # LangChain create_agent + tools
│   │   └── db/connection.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── api/
│   └── package.json
└── README.md
```

---

## 11. Build Order Summary

1. Data cleaning notebook (§3)
2. EDA notebook, including batched LLM categorization job run once and cached (§4, §6)
3. Visualization notebook (§5)
4. Build `youtube.db` from the cleaned Parquet (§7.1)
5. FastAPI `/stats/*` endpoints reading Parquet directly (§7, steps 1–4)
6. FastAPI `/ai/insights` (simple single-call LLM endpoint) (§7, step 5)
7. LangChain agent + `/ai/ask` (§7.2–7.3)
8. Frontend dashboard against `/stats/*` (§8, steps 1–5)
9. Frontend AI chat panel against `/ai/ask` + `/ai/insights` (§8, step 6)
10. Write up the AI-engineering rigor section for your report (§9)


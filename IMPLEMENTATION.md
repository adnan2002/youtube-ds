# YouTube Trending Videos - Combined Implementation Plan

**Project:** Project 2 Exploratory Data Analysis on YouTube Trending Videos with FastAPI, React visualizations, and LLM-assisted analysis features  
**Primary deliverable:** A polished GitHub technical report with notebook-based EDA, README, data files, presentation PDF, and an interactive React/JavaScript dashboard backed by FastAPI.  
**Priority rule:** Official requirements in `project-req/` define the report, EDA, README, and presentation expectations. The original FastAPI, React, LangChain, and LLM requirements remain part of the main implementation plan, not optional stretch work.

---

## 1. Requirement Priority

### Core Official Deliverables

These are grading-critical and must be completed:

1. **README.md** that replaces the starter README and introduces the project.
2. **Jupyter notebook(s)** with EDA, visualizations, statistical analysis, markdown explanation, and final recommendations.
3. **Data files** included in a clear `data/` structure, or documented with source links if too large.
4. **Presentation slideshow rendered as PDF** for a non-technical audience.
5. **Clear problem statement** and measurable objectives.
6. **Clean project organization** with appropriate file names, relative paths, no unnecessary files, and reproducible notebooks.

### Core Application Deliverables

These are part of this project's intended implementation and should not be demoted:

1. **FastAPI backend** that serves cleaned data, chart-ready statistics, and AI endpoints.
2. **React/Vite frontend** that renders interactive JavaScript visualizations.
3. **LangChain SQL agent** for natural-language questions over the cleaned dataset.
4. **LLM-powered insights** for short written summaries based on precomputed statistics.
5. **Read-only SQLite database** for the LangChain agent.

### Academic Integrity Constraint

The official requirements state that generative AI tools must not be used to create or copy-paste submitted code or presentations. If AI is used, keep it strictly aligned with instructor permissions and make sure submitted code, notebook analysis, README, and slides are student-authored and understood.

For this project, LLM features should be framed as part of the app's functionality, not as a replacement for the student's own analysis, code understanding, README, or presentation.

---

## 2. Architecture Overview

```text
React frontend
  |-- interactive charts and dashboard UI
  |-- filters for date, category, channel, and top-N
  |-- AI chat and AI insights panel
  |
  `-- REST/JSON calls
      |
      v
FastAPI backend
  |-- /videos
  |-- /stats/*
  |-- /ai/insights
  |-- /ai/ask
      |
      |-- pandas / Parquet for deterministic chart stats
      |
      `-- LangChain SQL agent
          `-- read-only SQLite database built from cleaned data
```

Use two data paths intentionally:

1. **Chart path:** React charts call deterministic `/stats/*` endpoints. These endpoints read precomputed aggregates or the cleaned Parquet/CSV file and should not depend on an LLM.
2. **AI path:** AI chat calls `/ai/ask`, which uses a constrained LangChain SQL agent against read-only SQLite.

This keeps the dashboard fast and reproducible while still supporting natural-language exploration.

---

## 3. Recommended Project Structure

Use a structure that supports both the official report deliverables and the full-stack app:

```text
youtube-ds/
|-- README.md
|-- IMPLEMENTATION.md
|-- requirements.txt
|-- data/
|   |-- raw/
|   |   `-- youtube_trending_raw.csv
|   |-- processed/
|   |   |-- youtube_clean.csv
|   |   `-- youtube_clean.parquet
|   |-- youtube.db
|   `-- data_dictionary.md
|-- notebooks/
|   `-- 01_youtube_trending_eda.ipynb
|-- scripts/
|   |-- build_sqlite_db.py
|   `-- prepare_data.py
|-- backend/
|   |-- requirements.txt
|   `-- app/
|       |-- main.py
|       |-- routers/
|       |   |-- stats.py
|       |   `-- ai.py
|       |-- services/
|       |   |-- data_service.py
|       |   `-- sql_agent.py
|       `-- db/
|           `-- connection.py
|-- frontend/
|   |-- package.json
|   `-- src/
|       |-- App.tsx
|       |-- api/
|       |-- components/
|       |-- pages/
|       `-- styles.css
|-- presentation/
|   `-- youtube_trending_presentation.pdf
|-- images/
|   `-- selected_visualizations.png
`-- scratch/
    `-- optional_experiments/
```

Notes:

1. Do not commit `.venv/`, `node_modules/`, `dist/`, `__pycache__/`, or temporary notebook checkpoint files.
2. Use relative paths in notebooks, scripts, and app code.
3. Keep incomplete or unused work in `scratch/` or remove it before submission.

---

## 4. Problem Statement and Objectives

The project must start with a specific, concise problem statement and measurable objectives.

### Draft Problem Statement

Content creators and marketing teams need to understand which YouTube video characteristics are associated with trending performance. This project analyzes YouTube trending video data across the available time period to identify which channels, publishing patterns, tags, categories, and engagement signals are most associated with high views and sustained trending activity.

Refine this after inspecting the dataset. If the dataset has a clear country, region, or time range, include it in the final problem statement.

### Draft Objectives

1. Identify the top channels and categories by trending frequency, views, and engagement.
2. Measure how engagement metrics such as likes, comments, and like ratio relate to view counts.
3. Analyze whether publishing timing or trending date patterns are associated with better performance.
4. Identify common tags or content themes among high-performing trending videos.
5. Produce clear, data-driven recommendations for creators or marketing teams.
6. Provide an interactive dashboard so users can explore the findings dynamically.
7. Provide an AI question-answering layer for natural-language exploration of the cleaned dataset.

Each objective should be answered directly in the notebook and reflected in the README, presentation, and application.

---

## 5. Core Notebook Requirements

Use the official `project-req/EDA_template.ipynb` structure as the baseline. Do not remove requested sections.

The final notebook should include:

1. Project title.
2. Introduction to the topic.
3. Problem statement.
4. Objectives.
5. Data info and descriptive statistics.
6. Data cleaning and handling.
7. Analysis that answers each objective.
8. Visualizations with labels, readable scales, and interpretation.
9. Bullet-point summary.
10. Bullet-point recommendations and conclusion.

Before submission:

1. Restart the kernel and run all cells.
2. Remove unused imports.
3. Remove broken, exploratory, or duplicate cells.
4. Confirm all paths are relative.
5. Confirm all charts render correctly.
6. Confirm markdown explains what each section contributes to the problem statement.

---

## 6. Data Cleaning Plan

1. **Load and inspect**
   - Check shape, columns, dtypes, `.info()`, `.describe()`, missing values, and sample rows.

2. **Fix data types**
   - Parse date columns such as `trending_date` and `publish_date`.
   - Convert `views`, `likes`, `dislikes`, and `comment_count` to numeric.
   - Convert flags such as `comments_disabled`, `ratings_disabled`, and `video_error_or_removed` to boolean if present.

3. **Handle missing values**
   - Decide column by column whether to drop, impute, or label as `unknown`.
   - Document every important decision in markdown.

4. **Handle duplicate rows**
   - YouTube trending datasets often include the same video on multiple trending days.
   - Keep a row-level trending dataset for time-based analysis.
   - Create a per-video view for video-level analysis, using the first or latest trending snapshot.
   - Create `days_trending` if repeated daily rows are available.

5. **Fix logical inconsistencies**
   - Check for negative counts.
   - Check impossible relationships such as likes greater than views.
   - Handle disabled comments or ratings consistently.

6. **Clean text columns**
   - Strip whitespace.
   - Normalize tags by splitting on `|`.
   - Lowercase tags for frequency analysis.
   - Remove placeholders such as `[none]`.

7. **Engineer features**
   - `engagement_rate = (likes + comment_count) / views`
   - `like_ratio = likes / (likes + dislikes)`
   - `days_to_trend = trending_date - publish_date`
   - `published_day_of_week`
   - `published_hour`
   - `tag_count`
   - `days_trending`
   - `unique_video_key`

8. **Save cleaned data**
   - Save to `data/processed/youtube_clean.csv`.
   - Save to `data/processed/youtube_clean.parquet` if `pyarrow` is installed.
   - Build `data/youtube.db` from the cleaned data for the SQL agent.

---

## 7. EDA Requirements

The official rubric evaluates data cleaning, EDA, statistical analysis, visualizations, and clarity of message. The analysis should be organized around the objectives, not around random charts.

Required analysis:

1. **Descriptive statistics**
   - Mean, median, standard deviation, min, max, and quantiles for numeric fields.
   - Explain skewed metrics such as views and likes.

2. **Univariate distributions**
   - Views, likes, comments, engagement rate, days to trend.
   - Use log scale where needed because video metrics are usually right-skewed.

3. **Time patterns**
   - Trending volume by date.
   - Publishing day of week.
   - Publishing hour if available.
   - Days from publish date to trending date.

4. **Channel-level analysis**
   - Top channels by trending frequency.
   - Top channels by average or median views.
   - Top channels by engagement rate.

5. **Category-level analysis**
   - If category IDs and category names are available, map IDs to readable labels.
   - Compare categories by views, engagement, and trending frequency.
   - If category labels are not available, document the limitation.

6. **Correlation analysis**
   - Views vs likes.
   - Views vs comments.
   - Likes vs comments.
   - Engagement rate vs views.
   - Use correlation heatmap and interpret carefully.

7. **Tag analysis**
   - Most frequent tags.
   - Tag count distribution.
   - Tags associated with high views or high engagement.

8. **Outlier analysis**
   - Identify extreme videos by views, engagement, and trending duration.
   - Explain whether outliers are valid observations or data quality issues.

9. **Recommendations**
   - Every recommendation must directly follow from the analysis.
   - Avoid unsupported claims or speculation.

---

## 8. Visualization Requirements

Use visuals that directly support the narrative and final recommendations.

Recommended notebook visuals:

1. Histogram or boxplot of views using log scale.
2. Histogram or boxplot of engagement rate.
3. Bar chart of top channels by trending frequency.
4. Bar chart of top categories by median views or engagement.
5. Line chart of trending volume over time.
6. Bar chart by publishing day of week.
7. Correlation heatmap.
8. Tag frequency chart.
9. Scatterplot of views vs likes or views vs comments.

React dashboard visuals:

1. KPI cards for total rows, unique videos, unique channels, date range, and median views.
2. Interactive line chart for trending volume over time.
3. Top channels bar chart with top-N control.
4. Category performance chart if category labels are available.
5. Engagement distribution chart.
6. Views vs likes/comments scatterplot.
7. Tag frequency visualization.
8. Filter controls for date range, category, channel, and top-N.

Chart quality requirements from the official presentation standards:

1. Use readable labels and appropriate chart types.
2. Format large numbers with K, M, or B.
3. Use percentages where appropriate.
4. Use consistent colors.
5. Avoid clutter.
6. Make charts interpretable to a non-technical audience.

---

## 9. FastAPI Backend Requirements

Build the backend after cleaned data exists.

Required endpoints:

1. `GET /`
   - Health check and project metadata.

2. `GET /videos?limit=50`
   - Returns a limited sample of cleaned videos.

3. `GET /stats/summary`
   - Returns high-level dashboard metrics.

4. `GET /stats/top-channels`
   - Query params: `limit`, `start_date`, `end_date`, `category`.

5. `GET /stats/categories`
   - Returns category-level counts, views, and engagement.

6. `GET /stats/trending-over-time`
   - Returns chart-ready time series data.

7. `GET /stats/engagement`
   - Returns engagement distributions and summary metrics.

8. `GET /stats/tags`
   - Returns most frequent tags and optional performance metrics.

9. `POST /ai/insights`
   - Feeds a compact precomputed summary into an LLM and returns written key findings.

10. `POST /ai/ask`
   - Uses a LangChain SQL agent to answer natural-language questions from the cleaned dataset.

Backend rules:

1. Chart endpoints should be deterministic and should not call an LLM.
2. Return chart-shaped JSON where practical, such as `{ "labels": [], "values": [] }`.
3. Add query-param filtering for date range, category, and channel.
4. Keep LLM latency isolated to `/ai/*`.
5. Validate user inputs and cap returned rows.

---

## 10. LangChain and LLM Requirements

The AI layer should be useful but constrained.

### Read-Only SQLite

Build `data/youtube.db` from `data/processed/youtube_clean.parquet` or `.csv`.

```python
import sqlite3
import pandas as pd

df = pd.read_parquet("data/processed/youtube_clean.parquet")
con = sqlite3.connect("data/youtube.db")
df.to_sql("videos", con, if_exists="replace", index=False)
con.close()
```

Open the database in read-only mode for the agent:

```python
sqlite3.connect("file:data/youtube.db?mode=ro", uri=True)
```

### Agent Safety

Implement defense in depth:

1. Use SQLite read-only mode.
2. Only allow `SELECT` statements in the query tool.
3. Reject write keywords such as `insert`, `update`, `delete`, `drop`, `truncate`, `alter`, `create`, `grant`, and `revoke`.
4. Cap query result rows.
5. Tell the agent to answer only from the dataset and to say when the data cannot answer a question.

### LLM Feature Scope

1. `/ai/insights` should summarize precomputed statistics, not raw full data.
2. `/ai/ask` should use the SQL agent and constrained tools.
3. Optional category enrichment can be done only if permitted by the instructor and documented clearly.
4. AI-generated text should not replace the student's own final recommendations in the notebook, README, or slides.

---

## 11. React and JavaScript Dashboard Requirements

Core frontend requirements:

1. React/Vite application under `frontend/`.
2. API client module for FastAPI calls.
3. Dashboard page with multiple chart sections.
4. Interactive filters wired to backend query params.
5. Loading, empty, and error states.
6. Responsive layout for desktop and mobile.
7. AI insights panel calling `/ai/insights`.
8. AI question box calling `/ai/ask`.

Recommended chart library:

1. Recharts for fast implementation.
2. Plotly.js if richer interactivity is needed.
3. D3 only if custom visualization is required.

Suggested frontend flow:

1. Load `/stats/summary` for KPI cards.
2. Load chart endpoints in parallel.
3. Update charts when filters change.
4. Keep AI calls manually triggered, not automatic on every filter change.

---

## 12. README Requirements

The final `README.md` should be written as an executive summary of the project, not as setup notes only.

Include:

1. Project title.
2. Problem statement.
3. Executive summary of process, findings, and recommendations.
4. File directory / table of contents.
5. Data source and data dictionary.
6. Description of cleaned data and engineered features.
7. Key visualizations.
8. Conclusions and recommendations.
9. Areas for further research.
10. Sources.
11. Instructions to run the notebook.
12. Instructions to run the FastAPI backend.
13. Instructions to run the React dashboard.
14. Notes explaining the LangChain/LLM features and their constraints.

The starter README from `project-req/README.md` must not remain as the final project README.

---

## 13. Presentation Requirements

The presentation is for a non-technical audience and should be about 5 minutes, with an allowed range of 5-7 minutes.

Required content:

1. Cover page with project title, name, and cohort.
2. Concise problem statement.
3. Key metrics, time coverage, and location/region if applicable.
4. High-level methodology with no code.
5. Primary findings supported by charts.
6. Data-driven recommendations.
7. Dashboard demo or screenshots if time allows.
8. Next steps or further research.

Presentation standards:

1. A chart slide should mostly contain the chart.
2. Avoid text boxes on chart slides.
3. Use one line of title text at the top.
4. Format values clearly.
5. Use readable font sizes.
6. Keep colors consistent and high contrast.
7. Do not speculate beyond the data.
8. Export final slides to PDF and place them under `presentation/`.

---

## 14. Build Order

Follow this order to avoid building UI before the data is stable:

1. Choose final dataset and place it under `data/raw/`.
2. Create or rename the main notebook to `notebooks/01_youtube_trending_eda.ipynb`.
3. Define the final problem statement and objectives.
4. Load, inspect, clean, and document the data.
5. Save cleaned data to `data/processed/`.
6. Perform EDA aligned to each objective.
7. Create polished notebook visualizations and written interpretations.
8. Write conclusions and data-driven recommendations.
9. Build `data/youtube.db` from the cleaned data.
10. Build FastAPI `/stats/*` endpoints.
11. Build the React dashboard visualizations against `/stats/*`.
12. Build `/ai/insights`.
13. Build the LangChain SQL agent and `/ai/ask`.
14. Add the React AI insights and chat UI.
15. Write the final `README.md`.
16. Create the presentation slideshow and export it as PDF.
17. Clean the repo before submission.
18. Restart and rerun the notebook from top to bottom.
19. Run the backend and frontend locally to confirm the app works.

---

## 15. Submission Checklist

Before submitting the GitHub repository, confirm:

1. `README.md` is the final project README, not the starter instructions.
2. Notebook runs without errors from a fresh kernel.
3. Notebook includes markdown explanations, visualizations, summary, and recommendations.
4. Data files or data source links are included and documented.
5. FastAPI backend runs locally.
6. React dashboard runs locally.
7. React charts use backend data, not hardcoded final results.
8. AI endpoints are isolated under `/ai/*` and do not control chart rendering.
9. LangChain SQL access is read-only and query-limited.
10. Presentation PDF exists.
11. Repo has no unnecessary generated files.
12. File and folder names are clear and consistent.
13. All paths are relative.
14. Recommendations are supported by analysis.
15. Presentation is non-technical and timed to 5-7 minutes.
16. Any AI-assisted learning or AI functionality complies with instructor policy.

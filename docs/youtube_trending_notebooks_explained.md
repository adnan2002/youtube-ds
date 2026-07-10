# YouTube Trending Notebook Walkthrough

This document explains the two notebooks in `notebooks/` as one pipeline:

1. `01_youtube_trending_eda.ipynb` prepares and cleans the raw dataset.
2. `02_youtube_trending_eda_analysis.ipynb` reads the cleaned dataset and performs the exploratory analysis.

The goal is not just to describe what each cell does, but also why it exists, how the code works, and what the notebook outputs mean.

## How The Two Notebooks Fit Together

- Notebook 1 is the data-preparation notebook.
- Notebook 2 is the analysis notebook.
- Notebook 2 depends on the cleaned dataset produced by the first notebook or by an equivalent export step.
- The notebooks are intentionally separated so the cleaning logic stays visible and reusable instead of being buried inside the analysis code.

One important operational note: the first notebook says the cleaned data stays in memory and does not write an export file, while the second notebook loads `data/processed/youtube_clean.csv`. That means the analysis notebook assumes that a cleaned CSV already exists somewhere in the project workflow.

## Notebook 1: `01_youtube_trending_eda.ipynb`

### Purpose

This notebook loads the raw YouTube trending dataset, inspects its structure, normalizes messy text and date values, creates engineered features, and prepares two useful views:

- `clean_df`: the row-level cleaned dataset
- `video_level_df`: one row per unique video-country pair, useful for per-video summaries

### Cell-by-Cell Explanation

#### Title and introduction cells

The opening markdown cells define the problem and objectives:

- understand which YouTube video characteristics are associated with trending performance
- inspect raw data quality
- clean types and text fields
- preserve row-level history for time-based analysis
- create derived features for downstream EDA

These cells do not execute code, but they frame the notebook as a reproducible cleaning pipeline rather than a one-off scratchpad.

#### Cell 5: imports and raw file discovery

```python
from pathlib import Path
import re

import numpy as np
import pandas as pd
```

What this means:

- `Path` is used for portable file handling.
- `re` provides regular expressions for parsing the `time_frame` text field.
- `numpy` and `pandas` are the data wrangling libraries used throughout the notebook.

```python
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 140)
```

These options make DataFrame previews easier to read by preventing pandas from truncating the table horizontally.

```python
RAW_CANDIDATES = [
    Path("data/raw/youtube_trending_raw.csv"),
    Path("../data/raw/youtube_trending_raw.csv"),
]
```

This list lets the notebook work whether it is launched from the project root or from inside the `notebooks/` directory.

```python
for candidate in RAW_CANDIDATES:
    if candidate.exists():
        RAW_PATH = candidate
        break
else:
    raise FileNotFoundError("Could not find data/raw/youtube_trending_raw.csv")
```

This is a safe path-search pattern:

- check each possible location
- stop at the first file that exists
- fail loudly if none of them exist

```python
raw_df = pd.read_csv(RAW_PATH)
raw_df.head()
```

This loads the raw CSV into memory and previews the first five rows.

#### Raw dataset result

The raw dataset loaded successfully with:

- `161,470` rows
- `18` columns

The preview shows the core fields:

- `video_id`
- `trending_date`
- `title`
- `channel_title`
- `category_id`
- `publish_date`
- `time_frame`
- `published_day_of_week`
- `publish_country`
- `tags`
- `views`
- `likes`
- `dislikes`
- `comment_count`
- three boolean flags about comments, ratings, and removal

#### Cell 6: structure and summary inspection

This cell prints:

- dataset shape
- column names
- data types
- `info()`
- `describe(include="all").T`

Why this matters:

- `shape` confirms the dataset size.
- `columns` shows the schema.
- `dtypes` tells you which fields are numeric, text, date-like, or boolean.
- `info()` reveals null counts and memory usage.
- `describe(include="all")` gives both numeric and categorical summaries.

#### Cell 7: missing values and sample rows

```python
missing_counts = raw_df.isna().sum().sort_values(ascending=False)
```

This counts missing values per column.

```python
display(missing_counts[missing_counts > 0].to_frame('missing_count'))
```

This shows only columns with missing values, if any exist.

```python
display(raw_df.sample(5, random_state=42))
```

This prints random rows to spot obvious formatting issues.

#### Raw data quality result

The raw dataset had:

- no true `NaN` values in any column
- many placeholder strings that needed normalization
- obvious text irregularities in `tags`

That means the main issue was not missingness in the pandas sense, but inconsistent placeholder values and type formats.

### Cell 9: cleaning helpers and feature engineering logic

This is the most important cell in the notebook. It defines the rules that transform the raw dataset into analysis-ready form.

#### Placeholder handling

```python
TEXT_PLACEHOLDERS = {'#name?', '[none]', 'none', 'null', 'nan', ''}
```

These values are treated as placeholders instead of real content.

Why:

- `#NAME?` often appears when spreadsheet exports or formula errors leak into text columns.
- `[none]`, `none`, `null`, and `nan` are common stand-ins for absent text.
- Empty strings also need to be handled consistently.

#### Column groups

```python
BOOLEAN_COLUMNS = ['comments_disabled', 'ratings_disabled', 'video_error_or_removed']
NUMERIC_COLUMNS = ['category_id', 'views', 'likes', 'dislikes', 'comment_count']
```

These lists keep the coercion logic centralized and easy to maintain.

#### Category label mapping

`CATEGORY_LABELS` maps numeric category IDs to readable names such as:

- `24 -> Entertainment`
- `10 -> Music`
- `25 -> News & Politics`
- `22 -> People & Blogs`

This is necessary because category IDs alone are not meaningful for analysis.

#### `normalize_text_columns(df)`

This function standardizes text fields.

Key lines:

```python
series = df[column].astype('string').str.strip()
```

This converts the column to pandas’ string dtype and removes surrounding whitespace.

```python
df[column] = series.mask(series.str.lower().isin(TEXT_PLACEHOLDERS), 'unknown')
```

This replaces placeholder text with `unknown` for identifier-like fields such as `video_id`, `title`, and `channel_title`.

For `tags`, the logic is different:

```python
df[column] = series.fillna('')
```

Tags are left as an empty string when missing so they can be processed later into a cleaned tag list.

Country and day fields are also normalized:

- `publish_country` is uppercased
- `published_day_of_week` is title-cased

That makes grouping and display consistent.

#### `coerce_numeric_columns(df)`

This function turns string-like numeric data into real numeric types.

```python
df[column] = pd.to_numeric(df[column], errors='coerce')
```

This is important because malformed values become `NaN` instead of silently producing bad data.

```python
df['category_id'] = df['category_id'].astype('Int64')
```

`Int64` is pandas’ nullable integer type. It supports missing values while still behaving like an integer column.

```python
df.loc[df[column] < 0, column] = pd.NA
```

Negative engagement metrics do not make sense here, so they are converted to missing values rather than clipped or forced to zero.

#### `coerce_boolean_columns(df)`

This function standardizes booleans.

```python
truthy = {'true', '1', 'yes', 'y', 't'}
falsy = {'false', '0', 'no', 'n', 'f'}
```

These sets define acceptable boolean text values.

```python
mapped = series.map(lambda value: True if value in truthy else False if value in falsy else pd.NA)
```

This converts common text representations into real booleans and leaves unknown values as missing.

#### `parse_dates(df)`

```python
df['trending_date'] = pd.to_datetime(df['trending_date'].astype('string'), format='%y.%d.%m', errors='coerce')
df['publish_date'] = pd.to_datetime(df['publish_date'].astype('string'), format='%d/%m/%Y', errors='coerce')
```

The explicit formats matter:

- `trending_date` is stored as `yy.dd.mm`
- `publish_date` is stored as `dd/mm/YYYY`

Using exact formats is safer than relying on inference and avoids ambiguous parsing.

#### `parse_time_frame_start_hour(value)`

This extracts the starting hour from strings like `17:00 to 17:59`.

```python
match = re.search(r'(\d{1,2}):\d{2}\s*to\s*(\d{1,2}):\d{2}', str(value))
```

The regex captures the hour at the start of the time window.

If the pattern does not match, the function returns `pd.NA`.

#### `clean_tags(value)`

This cleans the `tags` field into a consistent pipe-delimited format.

What it does:

- splits on `|`
- strips outer quotes
- lowercases each tag
- collapses multiple spaces into one
- removes placeholder-like tags
- deduplicates tags while preserving the original order

Example effect:

- raw tags may look messy and inconsistent
- cleaned tags become a standardized string such as `last week tonight trump presidency|last week tonight|john oliver`

That makes frequency analysis meaningful.

#### `add_engineered_features(df)`

This function creates the analytical features used later in both notebooks.

##### `published_hour`

```python
df['published_hour'] = df['time_frame'].map(parse_time_frame_start_hour).astype('Int64')
```

This converts a time range into a single hour bucket.

##### `days_to_trend`

```python
df['days_to_trend'] = (df['trending_date'] - df['publish_date']).dt.days.astype('Int64')
```

This measures how many days elapsed between publishing and trending.

Why it matters:

- small values mean the video trended quickly
- large values mean the video took longer to trend

##### `engagement_rate`

```python
views_safe = views.where(views > 0)
df['engagement_rate'] = (likes + comments) / views_safe
```

This measures engagement relative to reach.

The `views.where(views > 0)` part prevents division by zero.

##### `like_ratio`

```python
like_total = likes + dislikes
df['like_ratio'] = likes / like_total.where(like_total > 0)
```

This measures the fraction of reactions that are likes.

##### `unique_video_key`

```python
df['unique_video_key'] = df['publish_country'].fillna('unknown').astype('string') + '::' + df['video_id'].fillna('unknown').astype('string')
```

This is a crucial design choice.

Why:

- the same `video_id` can appear in multiple countries
- pairing it with `publish_country` avoids collisions
- this key is used to build the per-video view

##### `tags_clean` and `tag_count`

```python
df['tags_clean'] = df['tags'].map(clean_tags)
df['tag_count'] = df['tags_clean'].map(lambda value: 0 if not value else len(value.split('|'))).astype('Int64')
```

This stores the cleaned tags and counts how many tags each row has.

##### `category_label`

```python
df['category_label'] = df['category_id'].map(CATEGORY_LABELS).fillna('Unknown')
```

This translates numeric category IDs into readable labels.

##### `metric_issue_flag`

This flag is set when metrics look suspicious:

- any of `views`, `likes`, `dislikes`, or `comment_count` is missing
- `likes > views`
- `comment_count > views`

The notebook uses this as a lightweight data-quality guardrail.

##### `days_trending`

```python
df['days_trending'] = df.groupby('unique_video_key')['trending_date'].transform('count').astype('Int64')
```

This counts how many trending rows exist for each unique video-country pair.

Important nuance:

- it does not compute a calendar span
- it counts how many days the video appears in the dataset

That is the right interpretation for repeated daily trending snapshots.

### Cell 10: applying the helpers

```python
clean_df = normalize_text_columns(clean_df)
clean_df = coerce_numeric_columns(clean_df)
clean_df = coerce_boolean_columns(clean_df)
clean_df = parse_dates(clean_df)
```

The order is deliberate:

1. normalize text first
2. coerce numeric values
3. standardize booleans
4. parse dates

Then the notebook previews the cleaned rows and dtypes.

#### Cleaning result after coercion

The cleaned dataset now has:

- `trending_date` and `publish_date` as datetimes
- `category_id`, `views`, `likes`, `dislikes`, and `comment_count` as nullable integers
- the boolean flags as nullable booleans
- text fields normalized and stripped

#### Cell 11: validation checks

This cell verifies that the cleaning behaved as expected.

Results:

- missing values after coercion: `0` in every column
- duplicate full rows: `0`
- duplicate `video_id` + `trending_date` rows: `19,341`

The duplicate video/date count is not a problem by itself. It is a sign that the same video can appear in multiple countries on the same date, which is why `unique_video_key` includes the country.

#### Cell 12: engineered features

The notebook shows the first few engineered columns:

- `published_hour`
- `days_to_trend`
- `engagement_rate`
- `like_ratio`
- `tag_count`
- `days_trending`
- `unique_video_key`

It also shows before/after tag cleanup.

Observed examples:

- `SHANtell martin` becomes `shantell martin`
- quoted tags are split and normalized into lower-case pipe-delimited strings

This confirms that the tag cleaning logic is working.

#### Cell 13: metric sanity checks

This cell checks for impossible or suspicious metric combinations.

Results:

- negative counts for `views`, `likes`, `dislikes`, and `comment_count`: all `0`
- `likes > views`: `0`
- `comments > views`: `0`
- `metric_issue_flag`: `0`

So the cleaned data did not contain rows that violated the notebook’s metric rules.

#### Cell 14: per-video view

```python
sorted_df = clean_df.sort_values(['unique_video_key', 'trending_date', 'publish_date'], ascending=[True, False, False], kind='mergesort')
video_level_df = sorted_df.drop_duplicates(subset=['unique_video_key'], keep='first').copy()
```

This keeps the latest row for each unique video-country pair.

Why:

- trend analysis often needs a row per video instead of every daily snapshot
- sorting descending by date ensures the latest snapshot is kept
- `mergesort` is a stable sort, which helps preserve ordering consistency

```python
trend_bounds = clean_df.groupby('unique_video_key', as_index=False).agg(
    first_trending_date=('trending_date', 'min'),
    last_trending_date=('trending_date', 'max'),
)
```

This computes the date range for each video-country pair.

The notebook then merges those bounds back into `video_level_df`.

#### Per-video results

- row-level shape: `161,470 x 28`
- video-level shape: `63,805 x 30`
- row-level trending date range: `2017-11-14` to `2018-06-14`

That means the per-video view collapses the daily observations into a smaller summary table.

#### Cell 16: descriptive statistics after cleaning

The notebook prints a detailed summary of the cleaned data.

Notable results:

- average views: `2,419,854`
- median views: `384,739.5`
- average likes: `65,661.9`
- average dislikes: `3,490.2`
- average comment count: `7,035.5`
- mean `engagement_rate`: `0.0416`
- mean `like_ratio`: `0.9315`
- mean `days_to_trend`: `14.71`
- mean `tag_count`: `17.85`
- mean `days_trending`: `12.99`

Interpretation:

- the distributions are heavily skewed
- a few videos have extremely large values
- median values are more representative than means for many metrics

#### Cells 17 and 18: summary and recommendations

The notebook’s conclusion is:

- the raw dataset was loaded and cleaned in memory
- text, numeric, boolean, and date fields were normalized
- placeholder values were handled explicitly
- both row-level and per-video views were created
- engineered features are available in `clean_df`

The practical recommendations are:

- use `clean_df` for time-based questions
- use `video_level_df` for per-video snapshots
- treat `engagement_rate` and `like_ratio` as derived metrics with zero-denominator protection
- inspect `metric_issue_flag` before trusting questionable rows

## Notebook 2: `02_youtube_trending_eda_analysis.ipynb`

### Purpose

This notebook performs the actual EDA on the cleaned dataset.

It focuses on:

- distributions
- time patterns
- channel performance
- category performance
- correlations
- tags
- outliers

### Cell-by-Cell Explanation

#### Cell 5: imports and cleaned file loading

```python
from pathlib import Path
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
```

The analysis notebook adds plotting libraries because its job is to visualize patterns, not just clean data.

```python
CLEAN_PATHS = [
    Path("data/processed/youtube_clean.csv"),
    Path("../data/processed/youtube_clean.csv"),
    Path("../../data/processed/youtube_clean.csv"),
]
```

This is the same path-fallback idea used in notebook 1.

```python
df = pd.read_csv(CLEAN_PATH)
```

The analysis starts from the cleaned CSV, not the raw file.

Then it re-parses important columns:

- `trending_date` and `publish_date` become datetimes
- numeric columns are converted with `pd.to_numeric`
- boolean columns are mapped from text to real booleans

This is a defensive step. Even if the CSV was saved cleanly, the notebook ensures the columns are in the expected types.

### Result of loading the cleaned dataset

The dataset contains:

- `161,470` rows
- `28` columns

That confirms the analysis notebook is working with the enriched, cleaned version of the dataset.

### Cells 6 and 7: schema and summary

These cells print:

- shape
- columns
- dtypes
- `info()`
- numeric quantiles and descriptive statistics
- missing value counts
- sample rows

Why:

- they confirm the cleaned dataset is usable
- they provide a baseline before analysis
- they reveal skewness, outliers, and data spread

### Cell 9: distribution plots

This cell creates histograms and boxplots.

#### Why `log1p` is used

```python
np.log1p(series)
```

`log1p(x)` means `log(1 + x)`.

Why it is better here:

- views, likes, and comments are extremely right-skewed
- the log transform compresses the very large values
- it makes the bulk of the data visible

The notebook uses log-scale histograms for:

- views
- likes
- comment_count

and normal histograms for:

- engagement_rate
- days_to_trend
- tag_count

It also shows boxplots for the log-transformed main engagement metrics.

### Interpreting the distribution results

The raw metrics are dominated by a long tail:

- many videos have modest engagement
- a small number have very large counts
- log scaling gives a more informative view than raw counts

### Cell 11: time pattern analysis

This block answers questions like:

- When do videos trend?
- Which weekdays are used most often for publishing?
- Which hours are most common?
- How long does it usually take a video to trend?

Key code:

```python
daily_trending = df.groupby(df["trending_date"].dt.date).size().reset_index(name="count")
```

This counts how many trending rows appear on each date.

```python
day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Unknown"]
```

This forces weekday bars into a human-readable order.

```python
hour_counts = df["published_hour"].dropna().value_counts().sort_index().reset_index()
```

This counts publishing frequency by hour.

```python
sns.histplot(df["days_to_trend"].dropna(), bins=40, ...)
```

This shows how long it takes videos to go from publish date to trending date.

#### What this section means

- `trending_date` line plot shows how trending volume changes over time
- weekday bar chart shows publishing preferences
- hour bar chart shows publication timing patterns
- `days_to_trend` histogram shows the lag between publish and trend

### Cell 13: channel-level analysis

This section groups by `channel_title` and computes:

- `trending_frequency`
- average and median views
- average and median engagement rate

The `>= 10` threshold filters out tiny channels so the comparison is less noisy.

#### Why this matters

Some channels appear only once or twice. Those values are not stable enough for comparison, so the notebook keeps only channels with at least 10 rows.

#### Main results

Top channels by trending frequency include:

- `The Late Show with Stephen Colbert` - `653`
- `Late Night with Seth Meyers` - `594`
- `TheEllenShow` - `586`
- `The Tonight Show Starring Jimmy Fallon` - `569`
- `Jimmy Kimmel Live` - `560`

Other notable channels in the top group:

- `WWE`
- `CNN`
- `The Late Late Show with James Corden`
- `Netflix`
- `ESPN`
- `Saturday Night Live`
- `FBE`
- `Breakfast Club Power 105.1 FM`
- `Screen Junkies`
- `Warner Bros. Pictures`

Interpretation:

- late-night shows and large media brands dominate frequency
- channels with high median views are not always the same as the most frequent channels
- median engagement rate can highlight channels with strong audience response even when views are not the highest

### Cell 15: category-level analysis

This section groups by `category_label` and compares categories by:

- frequency
- average views
- median views
- average engagement rate
- median engagement rate

#### Main results

Top categories by trending frequency:

- `Entertainment` - `42,358`
- `Music` - `27,903`
- `People & Blogs` - `15,960`
- `Comedy` - `13,401`
- `News & Politics` - `11,623`
- `Sports` - `11,210`
- `Howto & Style` - `10,442`

Other categories in the top set include:

- `Film & Animation`
- `Gaming`
- `Science & Technology`
- `Education`
- `Pets & Animals`

Interpretation:

- Entertainment is the most common category by far
- Music has very high median views
- Comedy and Howto & Style show especially strong engagement rates
- category choice influences both reach and audience response

### Cell 17: correlation analysis

This section builds a correlation matrix for:

- `views`
- `likes`
- `dislikes`
- `comment_count`
- `engagement_rate`
- `like_ratio`
- `days_to_trend`
- `tag_count`
- `days_trending`

It then shows:

- a heatmap for the full correlation matrix
- scatter plots for:
  - views vs likes
  - views vs comments
  - likes vs comments
  - views vs engagement rate

#### Why the sampling and log scales matter

```python
df.sample(min(len(df), 5000), random_state=42)
```

The notebook samples at most 5,000 points because full scatter plots would overplot badly.

```python
axes[1].set_xscale("log")
axes[1].set_yscale("log")
```

Log axes make the large spread in counts easier to read.

#### Interpretation

- views, likes, and comment count are related
- the relationships are not linear on the raw scale because the data is heavily skewed
- engagement rate is useful because it normalizes raw activity by view count

### Cell 19: tag analysis

This section expands the cleaned `tags_clean` field into one row per tag.

#### Why `explode()` is used

```python
tag_frame["tag"] = tag_frame["tags_clean"].str.split("|")
tag_frame = tag_frame.explode("tag")
```

This converts a single row with multiple tags into multiple rows, one per tag.

That makes frequency and performance analysis possible at the tag level.

#### Most frequent tags

The top tag counts include:

- `funny` - `11,631`
- `comedy` - `10,041`
- `music` - `6,157`
- `2018` - `5,301`
- `pop` - `4,707`
- `news` - `4,540`
- `video` - `4,138`
- `trailer` - `4,077`
- `rap` - `3,949`
- `interview` - `3,746`

This indicates that broad theme words and genre labels appear frequently.

#### Tag performance

The tag metrics table filters to tags with at least 10 mentions and sorts by median engagement rate.

High median engagement examples include niche tags such as:

- `apiculture`
- `hakone`
- `#vegetarien`
- `#vegetal`
- `my parents do my makeup`

Interpretation:

- rare tags can show high engagement, but they are often noisy because the sample size is tiny
- tag frequency is more reliable than tag performance when a tag appears only a few times

### Cell 21: outlier analysis

This section surfaces the extreme values directly.

#### Highest view counts

The top rows are dominated by the viral music video:

- `Nicky Jam x J. Balvin - X (EQUIS)` with views above `424 million`

Other rows in that same video’s time series also appear near the top because the same video trended across multiple days.

#### Highest engagement rates

The highest engagement-rate rows include smaller-view videos with a very active audience.

This is why the notebook warns against using views alone as a proxy for success.

#### Longest trending durations

Some rows show `days_trending = 530`.

That means the same video-country pair appears in the dataset across a very long span of trending snapshots.

#### Metric issue result

```python
print("rows flagged for possible metric issues:", int(df["metric_issue_flag"].sum()))
```

Result:

- `0` rows flagged

So the outliers are not being rejected as bad data by the notebook’s checks. They are simply extreme observations that need interpretation.

### Notebook 2 summary

The notebook’s written conclusion is:

- views, likes, and comments are strongly right-skewed
- time-based patterns can be analyzed by date, weekday, and hour
- a few channels and categories dominate the trending data
- tags provide theme-level context
- outliers must be reviewed before drawing conclusions

The final recommendations are:

- focus on repeatedly strong channels and categories
- use engagement rate alongside views
- consider publishing timing
- treat low-frequency tags cautiously
- inspect outliers before using them in decisions

## Key Findings Across Both Notebooks

- The raw dataset was large and clean enough to load directly, but it still needed normalization.
- Placeholder strings were a bigger issue than missing values.
- `tags` required substantial cleanup before it could support analysis.
- `days_to_trend` and `days_trending` capture different but complementary time concepts.
- Entertainment and Music dominate the dataset by frequency, while Comedy and Howto & Style stand out on engagement.
- The data is highly skewed, so medians and log-scaled visuals are more informative than raw means alone.
- The strongest observed outliers are valid viral observations, not obvious data corruption.

## Practical Reading Guide

If you want to understand the notebooks in the fastest possible order:

1. Read Notebook 1 for cleaning logic and engineered features.
2. Read Notebook 2 for the actual EDA results.
3. Pay special attention to `unique_video_key`, `days_to_trend`, `engagement_rate`, `like_ratio`, `tags_clean`, and `metric_issue_flag`.

Those are the columns that turn the raw trending dump into something analytically useful.

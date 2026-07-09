-- Schema for the cleaned YouTube trending dataset stored in SQLite.
-- This file documents the table shape expected from the CSV-to-SQLite converter.

CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT,
    trending_date TEXT,
    title TEXT,
    channel_title TEXT,
    category_id INTEGER,
    category_label TEXT,
    publish_date TEXT,
    time_frame TEXT,
    published_hour INTEGER,
    published_day_of_week TEXT,
    publish_country TEXT,
    tags TEXT,
    tags_clean TEXT,
    tag_count INTEGER,
    views INTEGER,
    likes INTEGER,
    dislikes INTEGER,
    comment_count INTEGER,
    engagement_rate REAL,
    like_ratio REAL,
    days_to_trend INTEGER,
    days_trending INTEGER,
    unique_video_key TEXT,
    comments_disabled INTEGER,
    ratings_disabled INTEGER,
    video_error_or_removed INTEGER,
    metric_issue_flag INTEGER
);

CREATE INDEX IF NOT EXISTS idx_videos_video_id ON videos(video_id);
CREATE INDEX IF NOT EXISTS idx_videos_publish_country ON videos(publish_country);
CREATE INDEX IF NOT EXISTS idx_videos_category_id ON videos(category_id);
CREATE INDEX IF NOT EXISTS idx_videos_trending_date ON videos(trending_date);

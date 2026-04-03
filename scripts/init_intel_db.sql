-- ============================================
-- ARK95X NEUROLINK - Intel Database Schema
-- Twitter/X Social Intelligence Pipeline
-- ============================================
-- Database: C:\ARK95X\data\ark95x_intel.db
-- ============================================

CREATE TABLE IF NOT EXISTS intel_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author TEXT NOT NULL,
    original_text TEXT,
    original_link TEXT UNIQUE,
    original_date TEXT,
    summary TEXT,
    topics TEXT,            -- JSON array as string
    sentiment TEXT CHECK(sentiment IN ('positive','negative','neutral')),
    relevance_score REAL DEFAULT 0.0,
    key_entities TEXT,      -- JSON array as string
    action_items TEXT,      -- JSON array as string
    threat_level TEXT CHECK(threat_level IN ('none','low','medium','high')),
    category TEXT CHECK(category IN ('model_release','funding','research','policy','product','opinion','hiring')),
    extracted_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS monitored_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    handle TEXT UNIQUE NOT NULL,
    display_name TEXT,
    rss_url TEXT,
    category TEXT,
    priority INTEGER DEFAULT 5,
    active INTEGER DEFAULT 1,
    added_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS extraction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    account_handle TEXT,
    posts_fetched INTEGER DEFAULT 0,
    posts_extracted INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    duration_ms INTEGER,
    started_at TEXT,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS intel_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER REFERENCES intel_posts(id),
    alert_type TEXT CHECK(alert_type IN ('high_relevance','high_threat','trending_topic','new_model','funding_event')),
    acknowledged INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_posts_author ON intel_posts(author);
CREATE INDEX IF NOT EXISTS idx_posts_category ON intel_posts(category);
CREATE INDEX IF NOT EXISTS idx_posts_relevance ON intel_posts(relevance_score);
CREATE INDEX IF NOT EXISTS idx_posts_threat ON intel_posts(threat_level);
CREATE INDEX IF NOT EXISTS idx_posts_date ON intel_posts(extracted_at);
CREATE INDEX IF NOT EXISTS idx_alerts_type ON intel_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_ack ON intel_alerts(acknowledged);

-- Seed monitored accounts
INSERT OR IGNORE INTO monitored_accounts (handle, display_name, category, priority) VALUES
    ('@karpathy', 'Andrej Karpathy', 'researcher', 1),
    ('@sama', 'Sam Altman', 'executive', 1),
    ('@AndrewYNg', 'Andrew Ng', 'researcher', 1),
    ('@ylecun', 'Yann LeCun', 'researcher', 1),
    ('@demishassabis', 'Demis Hassabis', 'executive', 1),
    ('@lexfridman', 'Lex Fridman', 'media', 2),
    ('@kaifulee', 'Kai-Fu Lee', 'executive', 2),
    ('@gdb', 'Greg Brockman', 'executive', 2),
    ('@drfeifei', 'Fei-Fei Li', 'researcher', 2),
    ('@ESYudkowsky', 'Eliezer Yudkowsky', 'safety', 2),
    ('@rasbt', 'Sebastian Raschka', 'researcher', 3),
    ('@alliekmiller', 'Allie K. Miller', 'executive', 3),
    ('@mattshumer_', 'Matt Shumer', 'builder', 3),
    ('@OfficialLoganK', 'Logan Kilpatrick', 'developer_rel', 3),
    ('@dair_ai', 'DAIR.AI', 'research_org', 3),
    ('@ID_AA_Carmack', 'John Carmack', 'engineer', 4),
    ('@abhi1thakur', 'Abhishek Thakur', 'ml_engineer', 4),
    ('@wellingmax', 'Max Welling', 'researcher', 4),
    ('@timnitgebru', 'Timnit Gebru', 'ethics', 4),
    ('@gaborcselle', 'Gabor Cselle', 'builder', 4);

-- Views for quick intel queries
CREATE VIEW IF NOT EXISTS v_high_priority_intel AS
SELECT p.*, a.display_name, a.priority
FROM intel_posts p
JOIN monitored_accounts a ON p.author = a.handle
WHERE p.relevance_score >= 0.7
ORDER BY p.extracted_at DESC;

CREATE VIEW IF NOT EXISTS v_threat_board AS
SELECT p.author, p.summary, p.threat_level, p.category, p.original_link, p.extracted_at
FROM intel_posts p
WHERE p.threat_level IN ('medium', 'high')
ORDER BY p.extracted_at DESC;

CREATE VIEW IF NOT EXISTS v_daily_digest AS
SELECT 
    date(p.extracted_at) as intel_date,
    COUNT(*) as total_posts,
    AVG(p.relevance_score) as avg_relevance,
    SUM(CASE WHEN p.threat_level IN ('medium','high') THEN 1 ELSE 0 END) as threat_count,
    GROUP_CONCAT(DISTINCT p.category) as categories
FROM intel_posts p
GROUP BY date(p.extracted_at)
ORDER BY intel_date DESC;

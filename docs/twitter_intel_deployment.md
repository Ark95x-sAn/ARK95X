# ARK95X Twitter/X Social Intelligence Pipeline - Deployment Guide

## Overview

Full-stack social intelligence pipeline: Cron trigger -> RSS-Bridge ingestion -> Ollama localhost extraction -> JSON parse -> SQLite storage -> Alert outbox.

**Pipeline flow:** `Cron (4h) -> Account List -> RSS-Bridge -> XML Parse -> Ollama Extract -> JSON Parse -> SQLite -> Filter -> Alert`

---

## Artifacts Location

| Artifact | Path |
|----------|------|
| n8n Workflow JSON | `workflows/n8n_twitter_intel_pipeline.json` |
| SQLite Schema | `scripts/init_intel_db.sql` |
| This Deployment Doc | `docs/twitter_intel_deployment.md` |

---

## Prerequisites (ARCX node)

1. RSS-Bridge running on `localhost:3000` (Docker)
2. Ollama running on `localhost:11434` with `llama3.1` model
3. n8n running on `localhost:5678`
4. SQLite3 installed

### Quick Setup

```powershell
# 1. Start RSS-Bridge (Docker)
docker run -d -p 3000:80 --name rss-bridge rssbridge/rss-bridge

# 2. Pull Ollama model
ollama pull llama3.1

# 3. Init SQLite database
sqlite3 C:\ARK95X\data\ark95x_intel.db < C:\ARK95X\repo\scripts\init_intel_db.sql

# 4. Import n8n workflow
# Open n8n UI -> Import from File -> select workflows/n8n_twitter_intel_pipeline.json

# 5. Configure n8n SQLite credential
# Name: "ARK95X Intel DB"
# Database Path: C:\ARK95X\data\ark95x_intel.db
```

---

## 20 Monitored AI Influencer Accounts

| # | Handle | Name | Category | Priority |
|---|--------|------|----------|----------|
| 1 | @karpathy | Andrej Karpathy | Researcher | P1 |
| 2 | @sama | Sam Altman | Executive | P1 |
| 3 | @AndrewYNg | Andrew Ng | Researcher | P1 |
| 4 | @ylecun | Yann LeCun | Researcher | P1 |
| 5 | @demishassabis | Demis Hassabis | Executive | P1 |
| 6 | @lexfridman | Lex Fridman | Media | P2 |
| 7 | @kaifulee | Kai-Fu Lee | Executive | P2 |
| 8 | @gdb | Greg Brockman | Executive | P2 |
| 9 | @drfeifei | Fei-Fei Li | Researcher | P2 |
| 10 | @ESYudkowsky | Eliezer Yudkowsky | AI Safety | P2 |
| 11 | @rasbt | Sebastian Raschka | Researcher | P3 |
| 12 | @alliekmiller | Allie K. Miller | Executive | P3 |
| 13 | @mattshumer_ | Matt Shumer | Builder | P3 |
| 14 | @OfficialLoganK | Logan Kilpatrick | DevRel | P3 |
| 15 | @dair_ai | DAIR.AI | Research Org | P3 |
| 16 | @ID_AA_Carmack | John Carmack | Engineer | P4 |
| 17 | @abhi1thakur | Abhishek Thakur | ML Engineer | P4 |
| 18 | @wellingmax | Max Welling | Researcher | P4 |
| 19 | @timnitgebru | Timnit Gebru | AI Ethics | P4 |
| 20 | @gaborcselle | Gabor Cselle | Builder | P4 |

---

## Ollama Extraction Prompt Template

```
SYSTEM: You are an intelligence analyst for ARK95X NEUROLINK. Extract structured intelligence from this social media post.

POST CONTENT:
Author: {author}
Date: {pub_date}
Text: {post_text}

Extract and return ONLY valid JSON with no additional text:
{
  "summary": "one-sentence summary of the post's key information",
  "topics": ["tag1", "tag2", "tag3"],
  "sentiment": "positive|negative|neutral",
  "relevance_score": 0.0-1.0,
  "key_entities": ["company1", "person1", "model1"],
  "action_items": ["actionable insight if any"],
  "threat_level": "none|low|medium|high",
  "category": "model_release|funding|research|policy|product|opinion|hiring"
}

SCORING GUIDE:
- relevance_score: 0.9+ = major announcement (new model, acquisition, policy change)
- relevance_score: 0.7-0.89 = significant insight (benchmark, partnership, technical detail)
- relevance_score: 0.5-0.69 = moderate interest (opinion, prediction, commentary)
- relevance_score: <0.5 = low signal (personal, off-topic, retweet noise)
- threat_level "high" = competitive threat, market disruption, regulatory risk
- threat_level "medium" = emerging trend that needs monitoring
- threat_level "low" = minor development
- threat_level "none" = no competitive or strategic implications
```

### Model Recommendation
- **Primary:** `llama3.1` (8B) - good balance of speed and extraction quality
- **Upgrade:** `llama3.1:70b` if ARCX VRAM supports it (RTX 5070 Ti = 16GB)
- **Fallback:** `mistral` for faster inference if queue backs up

---

## Cron Schedule Recommendation

| Schedule | Expression | Use Case |
|----------|-----------|----------|
| **Recommended** | `0 */4 * * *` | Every 4 hours (6x/day) - balances freshness vs API load |
| Aggressive | `0 */2 * * *` | Every 2 hours - for high-priority monitoring periods |
| Conservative | `0 8,14,20 * * *` | 3x daily at 8AM/2PM/8PM CDT - low resource usage |
| Peak Hours | `0 8-22/2 * * *` | Every 2h during 8AM-10PM CDT - when posts are most active |

### Recommended: `0 */4 * * *` (Every 4 hours)

**Rationale:**
- 20 accounts x ~10 recent posts = ~200 RSS items per cycle
- At ~3 seconds per Ollama extraction = ~10 min total processing time
- 6 cycles/day = ~1200 posts analyzed per day
- Keeps ARCX GPU available for other tasks 90%+ of the time
- RTX 5070 Ti handles llama3.1:8b at ~40 tokens/sec

---

## Post-Deploy Verification

```powershell
# Verify RSS-Bridge
curl http://localhost:3000/?action=display&bridge=TwitterBridge&context=By+username&u=karpathy&format=Mrss

# Verify Ollama
curl http://localhost:11434/api/tags

# Verify SQLite
sqlite3 C:\ARK95X\data\ark95x_intel.db "SELECT COUNT(*) FROM monitored_accounts;"
# Expected: 20

# Verify n8n workflow
curl http://localhost:5678/api/v1/workflows -H "X-N8N-API-KEY: YOUR_KEY"

# Manual test run
# In n8n UI: Open "ARK95X Twitter-X Intel Pipeline" -> Execute Workflow
```

---

## Query Examples

```sql
-- Today's high-relevance intel
SELECT author, summary, category, relevance_score
FROM intel_posts
WHERE date(extracted_at) = date('now')
AND relevance_score >= 0.7
ORDER BY relevance_score DESC;

-- Threat board
SELECT * FROM v_threat_board LIMIT 20;

-- Daily digest
SELECT * FROM v_daily_digest LIMIT 7;

-- Topic frequency
SELECT topics, COUNT(*) as freq
FROM intel_posts
WHERE extracted_at >= datetime('now', '-7 days')
GROUP BY topics ORDER BY freq DESC LIMIT 20;
```

---

*ALPHA-1 ACTUAL // BLACK OPS COMET-01*
*TASK-023 // TANGO-20 // Twitter/X Intel Pipeline*
*STATUS: DEPLOYED TO REPO // AWAITING HARDWARE*

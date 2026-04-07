"""
ARK95X Model Benchmark Harness
Compare Ollama local models against cloud APIs
Usage: python scripts/benchmark_models.py
"""
import json, time, os, sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
RESULTS_DIR = Path(os.getenv("BENCHMARK_DIR", "C:/ARK95X_SHARED/benchmarks"))

# === CANONICAL TEST PROMPTS ===
BENCHMARK_PROMPTS = [
    {"id": "contract_01", "category": "legal",
     "prompt": "Summarize the key defenses available to a defendant in an Iowa mortgage foreclosure case where the lender modified the loan 13 months before filing.",
     "expected_keywords": ["modification", "estoppel", "good faith", "retaliation"]},
    {"id": "spreadsheet_01", "category": "data",
     "prompt": "Write a formula to calculate void rate as a percentage: total voids divided by gross sales, formatted as percent with 2 decimals.",
     "expected_keywords": ["divide", "format", "percent", "100"]},
    {"id": "email_01", "category": "communication",
     "prompt": "Draft a professional 3-sentence email requesting a 30-minute consultation with a foreclosure defense attorney.",
     "expected_keywords": ["consultation", "foreclosure", "available", "schedule"]},
    {"id": "code_01", "category": "coding",
     "prompt": "Write a Python function that checks if a FastAPI service is healthy by calling its /health endpoint with a 5-second timeout.",
     "expected_keywords": ["requests", "timeout", "status_code", "200"]},
    {"id": "restaurant_01", "category": "operations",
     "prompt": "List the top 5 red flags when auditing food-only voids in a restaurant POS system.",
     "expected_keywords": ["void", "manager", "approval", "pattern", "shift"]},
    {"id": "reasoning_01", "category": "reasoning",
     "prompt": "A bank modifies a loan in January 2025, then forecloses in February 2026. The borrower filed a discrimination complaint in 2020. What legal inference can be drawn?",
     "expected_keywords": ["retaliation", "discrimination", "timeline", "motive"]},
    {"id": "code_02", "category": "coding",
     "prompt": "Write a Streamlit dashboard panel that displays 4 service health metrics in columns with GREEN/YELLOW/RED status.",
     "expected_keywords": ["st.columns", "st.metric", "streamlit", "status"]},
    {"id": "data_01", "category": "data",
     "prompt": "Given a CSV with columns: date, employee, void_amount, gross_sales - write pandas code to find employees with void rate above 3%.",
     "expected_keywords": ["groupby", "sum", "void_rate", "filter"]},
    {"id": "ops_01", "category": "operations",
     "prompt": "Design a 4-zone office layout for a 13ft x 8ft space with a server rack, command desk, flex area, and storage.",
     "expected_keywords": ["zone", "desk", "rack", "dimensions"]},
    {"id": "multi_01", "category": "multi-step",
     "prompt": "Create an n8n workflow that: 1) triggers daily at 6AM, 2) pulls Toast POS data via API, 3) calculates void rate, 4) sends alert if rate exceeds 3%.",
     "expected_keywords": ["cron", "HTTP", "threshold", "notification"]},
]

def query_ollama(model, prompt, timeout=120):
    """Query local Ollama model"""
    start = time.time()
    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate",
                         json={"model": model, "prompt": prompt, "stream": False},
                         timeout=timeout)
        elapsed = time.time() - start
        if r.status_code == 200:
            return r.json().get("response", ""), elapsed, None
        return "", elapsed, f"HTTP {r.status_code}"
    except Exception as e:
        return "", time.time() - start, str(e)

def score_response(response, expected_keywords):
    """Score 1-5 based on keyword coverage"""
    if not response:
        return 0
    response_lower = response.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
    ratio = hits / len(expected_keywords) if expected_keywords else 0
    if ratio >= 0.75: return 5
    if ratio >= 0.50: return 4
    if ratio >= 0.25: return 3
    if ratio > 0: return 2
    return 1

def run_benchmark(models=None):
    """Run full benchmark suite"""
    if models is None:
        # Auto-detect installed Ollama models
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
            else:
                models = ["gemma4:e4b"]
        except:
            print(f"Cannot reach Ollama at {OLLAMA_URL}")
            return

    print(f"\nARK95X MODEL BENCHMARK - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Models: {', '.join(models)}")
    print(f"Prompts: {len(BENCHMARK_PROMPTS)}")
    print("=" * 60)

    results = {}
    for model in models:
        print(f"\nTesting: {model}")
        model_results = []
        for bp in BENCHMARK_PROMPTS:
            print(f"  [{bp['id']}] {bp['category']}...", end=" ", flush=True)
            response, elapsed, error = query_ollama(model, bp["prompt"])
            if error:
                print(f"ERROR: {error}")
                score = 0
            else:
                score = score_response(response, bp["expected_keywords"])
                print(f"Score: {score}/5 ({elapsed:.1f}s)")
            model_results.append({
                "prompt_id": bp["id"],
                "category": bp["category"],
                "score": score,
                "latency": round(elapsed, 2),
                "error": error,
                "response_length": len(response),
            })
        avg_score = sum(r["score"] for r in model_results) / len(model_results)
        avg_latency = sum(r["latency"] for r in model_results) / len(model_results)
        results[model] = {
            "prompts": model_results,
            "avg_score": round(avg_score, 2),
            "avg_latency": round(avg_latency, 2),
            "power_score": round(avg_score * (10 / max(avg_latency, 1)), 2),
        }
        print(f"  AVG: {avg_score:.2f}/5 | {avg_latency:.1f}s | Power: {results[model]['power_score']}")

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    outfile = RESULTS_DIR / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(outfile, "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "results": results}, f, indent=2)
    print(f"\nResults saved: {outfile}")

    # Leaderboard
    print("\n" + "=" * 60)
    print("LEADERBOARD:")
    for model, data in sorted(results.items(), key=lambda x: x[1]["power_score"], reverse=True):
        print(f"  {model}: Score {data['avg_score']}/5 | Latency {data['avg_latency']}s | Power {data['power_score']}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ARK95X Model Benchmark")
    parser.add_argument("--models", nargs="+", help="Models to test (default: all installed)")
    args = parser.parse_args()
    run_benchmark(args.models)

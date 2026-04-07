"""
ARK95X Toast POS Audit Engine
Food-only sales vs voids and comps analysis
Usage: python services/toast_audit.py --csv sales.csv voids.csv comps.csv
       python services/toast_audit.py --api  (uses Toast API)
"""
import json, os, sys, csv
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

try:
    import pandas as pd
except ImportError:
    pd = None
    print("Warning: pandas not installed. CSV mode limited.")

# === CONFIG ===
TOAST_API_HOST = os.getenv("TOAST_API_HOST", "https://ws-api.toasttab.com")
TOAST_CLIENT_ID = os.getenv("TOAST_CLIENT_ID", "")
TOAST_CLIENT_SECRET = os.getenv("TOAST_CLIENT_SECRET", "")
TOAST_RESTAURANT_GUID = os.getenv("TOAST_RESTAURANT_GUID", "")
OUTPUT_DIR = Path(os.getenv("AUDIT_OUTPUT", "C:/ARK95X_SHARED/audits"))
WEBHOOK_LOG = Path(os.getenv("TOAST_LOG", "C:/ARK95X_SHARED/logs/toast_webhook.json"))

# Thresholds
VOID_RATE_THRESHOLD = 0.03   # 3%
COMP_RATE_THRESHOLD = 0.02   # 2%
VOID_COMP_RATIO_ALERT = 3.0  # voids/comps > 3:1
EMPLOYEE_OUTLIER_MULT = 2.0  # employee rate > 2x average

class ToastAudit:
    def __init__(self):
        self.sales = []
        self.voids = []
        self.comps = []
        self.results = {}

    def load_csv(self, sales_path, voids_path=None, comps_path=None):
        """Load from Toast CSV exports"""
        if pd is None:
            print("pandas required for CSV mode")
            return False
        try:
            self.sales = pd.read_csv(sales_path)
            if voids_path:
                self.voids = pd.read_csv(voids_path)
            if comps_path:
                self.comps = pd.read_csv(comps_path)
            print(f"Loaded: {len(self.sales)} sales, {len(self.voids)} voids, {len(self.comps)} comps")
            return True
        except Exception as e:
            print(f"CSV load error: {e}")
            return False

    def analyze(self):
        """Run full audit analysis"""
        if pd is None or not isinstance(self.sales, pd.DataFrame):
            print("No data loaded")
            return

        gross = self.sales["Gross Sales"].sum() if "Gross Sales" in self.sales.columns else 0
        void_total = self.voids["Void Amount"].sum() if isinstance(self.voids, pd.DataFrame) and "Void Amount" in self.voids.columns else 0
        comp_total = self.comps["Comp Amount"].sum() if isinstance(self.comps, pd.DataFrame) and "Comp Amount" in self.comps.columns else 0

        void_rate = void_total / gross if gross > 0 else 0
        comp_rate = comp_total / gross if gross > 0 else 0
        net_sales = gross - void_total - comp_total
        vc_ratio = void_total / comp_total if comp_total > 0 else 0

        self.results = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "gross_food_sales": round(gross, 2),
            "total_voids_food": round(void_total, 2),
            "void_rate": round(void_rate, 4),
            "total_comps_food": round(comp_total, 2),
            "comp_rate": round(comp_rate, 4),
            "net_food_sales": round(net_sales, 2),
            "void_comp_ratio": round(vc_ratio, 2),
            "alerts": [],
        }

        # Check thresholds
        if void_rate > VOID_RATE_THRESHOLD:
            self.results["alerts"].append(f"VOID RATE ALERT: {void_rate:.1%} exceeds {VOID_RATE_THRESHOLD:.0%}")
        if comp_rate > COMP_RATE_THRESHOLD:
            self.results["alerts"].append(f"COMP RATE ALERT: {comp_rate:.1%} exceeds {COMP_RATE_THRESHOLD:.0%}")
        if vc_ratio > VOID_COMP_RATIO_ALERT:
            self.results["alerts"].append(f"VOID/COMP RATIO ALERT: {vc_ratio:.1f}:1 exceeds {VOID_COMP_RATIO_ALERT:.0f}:1")

        # Employee analysis
        if isinstance(self.voids, pd.DataFrame) and "Voided By" in self.voids.columns:
            emp_voids = self.voids.groupby("Voided By")["Void Amount"].sum()
            avg_void = emp_voids.mean()
            outliers = emp_voids[emp_voids > avg_void * EMPLOYEE_OUTLIER_MULT]
            for emp, amt in outliers.items():
                self.results["alerts"].append(f"EMPLOYEE VOID OUTLIER: {emp} = ${amt:.2f} ({amt/avg_void:.1f}x avg)")

        # Void reason analysis
        if isinstance(self.voids, pd.DataFrame) and "Void Reason" in self.voids.columns:
            reasons = self.voids["Void Reason"].value_counts(normalize=True)
            if "Other" in reasons.index and reasons["Other"] > 0.20:
                self.results["alerts"].append(f"VOID REASON ALERT: 'Other' = {reasons['Other']:.0%} (>20%)")
            self.results["top_void_reason"] = reasons.index[0] if len(reasons) > 0 else "N/A"

        self.results["alert"] = len(self.results["alerts"]) > 0
        return self.results

    def save_results(self):
        """Save audit results and update webhook log"""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        outfile = OUTPUT_DIR / f"audit_{datetime.now().strftime('%Y%m%d')}.json"
        with open(outfile, "w") as f:
            json.dump(self.results, f, indent=2)
        # Update webhook log for dashboard
        WEBHOOK_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(WEBHOOK_LOG, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved: {outfile}")
        print(f"Webhook log updated: {WEBHOOK_LOG}")

    def print_report(self):
        """Print formatted audit report"""
        r = self.results
        print(f"\n{'='*50}")
        print(f"TOAST POS AUDIT REPORT - {r.get('date', 'N/A')}")
        print(f"{'='*50}")
        print(f"Gross Food Sales:  ${r.get('gross_food_sales', 0):>10,.2f}")
        print(f"Total Voids:       ${r.get('total_voids_food', 0):>10,.2f}  ({r.get('void_rate', 0):.1%})")
        print(f"Total Comps:       ${r.get('total_comps_food', 0):>10,.2f}  ({r.get('comp_rate', 0):.1%})")
        print(f"Net Food Sales:    ${r.get('net_food_sales', 0):>10,.2f}")
        print(f"Void/Comp Ratio:   {r.get('void_comp_ratio', 0):.1f}:1")
        if r.get("alerts"):
            print(f"\nALERTS ({len(r['alerts'])}):'")
            for a in r["alerts"]:
                print(f"  ** {a}")
        else:
            print("\nNo alerts - all metrics within thresholds.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ARK95X Toast POS Audit")
    parser.add_argument("--csv", nargs=3, metavar=("SALES", "VOIDS", "COMPS"),
                       help="CSV files: sales voids comps")
    args = parser.parse_args()

    audit = ToastAudit()
    if args.csv:
        if audit.load_csv(args.csv[0], args.csv[1], args.csv[2]):
            audit.analyze()
            audit.print_report()
            audit.save_results()
    else:
        print("Usage: python toast_audit.py --csv sales.csv voids.csv comps.csv")
        print("Export CSVs from Toast Back Office > Reporting")

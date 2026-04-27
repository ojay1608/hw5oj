#!/usr/bin/env python3
import csv, json, sys, argparse
from datetime import date, datetime
from collections import defaultdict

SUPPORTED_DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y"]
AGING_BUCKETS = [
    ("0-30 days",  0,   30),
    ("31-60 days", 31,  60),
    ("61-90 days", 61,  90),
    ("90+ days",   91,  None),
]
REQUIRED_COLUMNS = {"claim_id", "payer", "submission_date", "amount", "status"}
VALID_STATUSES   = {"pending", "denied", "paid"}

def parse_date(raw):
    for fmt in SUPPORTED_DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None

def normalize_headers(row):
    return {
        k.strip().lower(): (v.strip() if v is not None else "")
        for k, v in row.items()
        if k is not None
    }

def get_bucket(days):
    for label, low, high in AGING_BUCKETS:
        if high is None and days >= low:
            return label
        if high is not None and low <= days <= high:
            return label
    return "unknown"

def safe_float(val):
    try:
        return float(val.replace(",", "").replace("$", "").strip())
    except (ValueError, AttributeError):
        return None

def analyze(filepath, threshold_days, threshold_amount):
    today = date.today()
    warnings = []
    rows = []
    try:
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            raw_headers = {h.strip().lower() for h in (reader.fieldnames or [])}
            missing = REQUIRED_COLUMNS - raw_headers
            if missing:
                sys.exit(json.dumps({"error": f"CSV missing required columns: {', '.join(sorted(missing))}"}))
            for i, row in enumerate(reader, start=2):
                row = normalize_headers(row)
                sub_date = parse_date(row.get("submission_date", ""))
                if sub_date is None:
                    warnings.append(f"Row {i}: unparseable submission_date '{row.get('submission_date', '')}' — skipped.")
                    continue
                if sub_date > today:
                    warnings.append(f"Row {i}: submission_date {sub_date} is in the future — skipped.")
                    continue
                amount = safe_float(row.get("amount", ""))
                if amount is None:
                    warnings.append(f"Row {i}: invalid amount '{row.get('amount', '')}' — treated as 0.")
                    amount = 0.0
                status = row.get("status", "").lower().strip()
                if status not in VALID_STATUSES:
                    warnings.append(f"Row {i}: unrecognised status '{status}' — treated as 'pending'.")
                    status = "pending"
                days_outstanding = (today - sub_date).days
                rows.append({
                    "claim_id": row.get("claim_id", f"row-{i}"),
                    "payer": row.get("payer", "Unknown"),
                    "submission_date": str(sub_date),
                    "amount": amount,
                    "status": status,
                    "denial_code": row.get("denial_code", ""),
                    "days_outstanding": days_outstanding,
                    "bucket": get_bucket(days_outstanding),
                })
    except FileNotFoundError:
        sys.exit(json.dumps({"error": f"File not found: {filepath}"}))
    except Exception as e:
        sys.exit(json.dumps({"error": str(e)}))

    if not rows:
        sys.exit(json.dumps({"error": "No valid rows found after parsing."}))

    total_claims = len(rows)
    total_billed = sum(r["amount"] for r in rows)
    denied_claims = [r for r in rows if r["status"] == "denied"]
    overall_denial_rate = round(len(denied_claims) / total_claims * 100, 1)

    bucket_data = {label: {"claims": 0, "billed": 0.0} for label, _, _ in AGING_BUCKETS}
    for r in rows:
        b = r["bucket"]
        if b in bucket_data:
            bucket_data[b]["claims"] += 1
            bucket_data[b]["billed"] += r["amount"]

    aging_buckets_out = []
    for label, _, _ in AGING_BUCKETS:
        d = bucket_data[label]
        aging_buckets_out.append({
            "bucket": label,
            "claims": d["claims"],
            "billed": round(d["billed"], 2),
            "pct_of_total": round(d["claims"] / total_claims * 100, 1) if total_claims else 0,
        })

    payer_stats = defaultdict(lambda: {"claims": 0, "denied": 0, "billed": 0.0, "days_sum": 0})
    for r in rows:
        p = r["payer"]
        payer_stats[p]["claims"] += 1
        payer_stats[p]["billed"] += r["amount"]
        payer_stats[p]["days_sum"] += r["days_outstanding"]
        if r["status"] == "denied":
            payer_stats[p]["denied"] += 1

    payer_breakdown = []
    for payer, s in payer_stats.items():
        payer_breakdown.append({
            "payer": payer,
            "claims": s["claims"],
            "denial_rate_pct": round(s["denied"] / s["claims"] * 100, 1),
            "avg_days_outstanding": round(s["days_sum"] / s["claims"], 1),
            "total_billed": round(s["billed"], 2),
        })
    payer_breakdown.sort(key=lambda x: x["denial_rate_pct"], reverse=True)

    high_risk = [
        {"claim_id": r["claim_id"], "payer": r["payer"], "days_outstanding": r["days_outstanding"],
         "amount": r["amount"], "status": r["status"], "denial_code": r["denial_code"]}
        for r in rows
        if r["days_outstanding"] >= threshold_days and r["amount"] >= threshold_amount
    ]
    high_risk.sort(key=lambda x: x["days_outstanding"], reverse=True)

    if total_claims < 10:
        warnings.append(f"Dataset has only {total_claims} valid claims. Denial rates may not be statistically meaningful.")

    return {
        "generated_date": str(today),
        "source_file": filepath,
        "summary": {
            "total_claims": total_claims,
            "total_billed": round(total_billed, 2),
            "overall_denial_rate": overall_denial_rate,
            "high_risk_count": len(high_risk),
        },
        "aging_buckets": aging_buckets_out,
        "payer_breakdown": payer_breakdown,
        "high_risk_claims": high_risk,
        "warnings": warnings,
        "thresholds": {"days": threshold_days, "amount": threshold_amount},
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--threshold-days", type=int, default=90)
    parser.add_argument("--threshold-amount", type=float, default=500)
    args = parser.parse_args()
    print(json.dumps(analyze(args.csv_path, args.threshold_days, args.threshold_amount), indent=2))

if __name__ == "__main__":
    main()

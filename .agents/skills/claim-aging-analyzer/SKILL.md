---
name: claim-aging-analyzer
description: >
  Parses a CSV of insurance claims, computes days outstanding using real date
  arithmetic, classifies each claim into aging buckets (0-30, 31-60, 61-90,
  90+ days), calculates denial rates by payer, flags high-risk claims, and
  produces a structured denial risk report. Use this skill whenever the user
  asks to audit, analyze, age, or summarize a claims dataset, especially when
  the words "aging," "denial rate," "days outstanding," "payer performance," or
  "revenue cycle" appear in the request.
---

## When to use this skill
- The user supplies a CSV file containing insurance claim records
- The user asks for aging analysis, denial rates, or payer-level performance
- The user wants to identify high-risk or stale claims (90+ days unpaid)
- The user is working in healthcare revenue cycle management (RCM) contexts

## When NOT to use this skill
- The user has not provided a CSV or valid file path
- The dataset has no date columns
- The user wants clinical or medical coding advice (out of scope)
- The user wants to generate denial appeal letters (separate skill)

## Expected inputs
| Column           | Description                               |
|------------------|-------------------------------------------|
| claim_id         | Unique identifier for each claim          |
| payer            | Insurance payer name or code              |
| submission_date  | Date submitted (YYYY-MM-DD or MM/DD/YYYY) |
| amount           | Billed amount in USD                      |
| status           | pending, denied, or paid                  |

## Step-by-step instructions
1. Confirm the file path with the user
2. Run: python scripts/analyze_claims.py <path_to_csv>
3. Parse the JSON output
4. Render a Markdown report with aging buckets, payer breakdown, and high-risk claims

## Why the script is load-bearing
Date arithmetic, statistical aggregation, and CSV parsing require deterministic
code. A language model cannot reliably compute days outstanding or denial rates
across hundreds of rows reproducibly.

## Limitations
- Does not validate CPT or ICD codes
- Does not connect to live payer systems
- Supports YYYY-MM-DD and MM/DD/YYYY date formats only

# hw5-oj: claim-aging-analyzer

> **Video walkthrough:** [ADD YOUR ZOOM/YOUTUBE LINK HERE]

---

## What the skill does

`claim-aging-analyzer` is a reusable AI skill that accepts a CSV of insurance
claims, runs a deterministic Python analysis, and produces a structured denial
risk report. It computes:

- **Days outstanding** per claim using real date arithmetic (today minus submission date)
- **Aging buckets**: 0–30, 31–60, 61–90, and 90+ days
- **Payer-level denial rates** and average days outstanding, sorted by denial rate
- **High-risk claim flags** (default: 90+ days AND $500+ billed)
- **Data quality warnings** for bad dates, unknown statuses, future dates, or missing amounts

The agent orchestrates the workflow; the Python script does every part that
requires deterministic computation.

---

## Why I chose it

Revenue cycle management (RCM) is the backbone of healthcare finance, and
denial management is one of its most costly failure points. Payers deny claims
for reasons ranging from missing prior authorizations to timely-filing
violations, and the longer a claim sits unworked, the lower the probability of
recovery.

This skill maps directly to work I am doing at AutoMed AI, my healthcare AI
venture focused on RCM automation. A claims aging report is one of the first
artifacts an RCM team needs, and it is precisely the type of task where a
language model alone fails — date arithmetic, statistical aggregation across
potentially thousands of rows, and reproducible output all require code.
Bolting a trivial script onto a prompt would have been intellectually
dishonest; here, the script *is* the core of the skill.

---

## Folder structure

```
hw5-oj/
├── .agents/
│   └── skills/
│       └── claim-aging-analyzer/
│           ├── SKILL.md              ← skill metadata + agent instructions
│           └── scripts/
│               └── analyze_claims.py ← deterministic analysis script
├── sample_data/
│   ├── claims_normal.csv             ← 20-claim realistic dataset
│   ├── claims_edge.csv               ← messy data (bad dates, unknown statuses)
│   └── claims_tiny.csv               ← 3-claim set (triggers caution warning)
└── README.md
```

---

## How to use it

### Prerequisites

Python 3.10+ (uses `date | None` union type hint). No external packages required
— the script uses only the standard library.

### Basic usage

```bash
python .agents/skills/claim-aging-analyzer/scripts/analyze_claims.py path/to/claims.csv
```

### With custom thresholds

```bash
python .agents/skills/claim-aging-analyzer/scripts/analyze_claims.py path/to/claims.csv \
  --threshold-days 60 \
  --threshold-amount 1000
```

### CSV format

The script expects these columns (case-insensitive, flexible order):

| Column            | Required | Description                                  |
|-------------------|----------|----------------------------------------------|
| `claim_id`        | Yes      | Unique claim identifier                      |
| `payer`           | Yes      | Insurance payer name                         |
| `submission_date` | Yes      | Date submitted (YYYY-MM-DD or MM/DD/YYYY)    |
| `amount`          | Yes      | Billed amount (USD)                          |
| `status`          | Yes      | `pending`, `denied`, or `paid`               |
| `denial_code`     | No       | CMS reason code (e.g., CO-4, PR-96)          |

### In a coding agent (Claude Code / Codex / VS Code Copilot Agent)

The agent reads `SKILL.md` and matches on keywords like *aging*, *denial rate*,
*days outstanding*, *payer performance*, or *revenue cycle*. It then:

1. Confirms the CSV path with the user
2. Runs `analyze_claims.py` with that path
3. Parses the JSON output
4. Renders a Markdown denial risk report

#### Demo prompts

| Type       | Prompt |
|------------|--------|
| Normal     | `Analyze my claims file at sample_data/claims_normal.csv and give me a denial risk report.` |
| Edge case  | `Run the aging analyzer on sample_data/claims_edge.csv — some rows might have bad data.` |
| Caution    | `Can you tell me the denial rate from sample_data/claims_tiny.csv?` |

---

## What the script does

`analyze_claims.py` is responsible for every computation the model cannot do
reliably on its own:

1. **CSV parsing** — uses `csv.DictReader` with case-insensitive, stripped
   header normalization; handles extra columns and None keys from malformed rows
2. **Date parsing** — tries four common date formats; skips rows with
   unparseable or future dates and logs warnings
3. **Days outstanding** — computed as `today - submission_date` using Python's
   `datetime.date` arithmetic; not estimated or inferred
4. **Aging bucketing** — deterministic classification into four buckets based
   on exact day counts
5. **Statistical aggregation** — denial rates, average days outstanding, and
   total billed per payer, computed across all valid rows
6. **High-risk flagging** — configurable thresholds via CLI flags
7. **Output** — clean JSON to stdout; warnings and errors to stderr / `sys.exit`

The agent receives JSON and converts it to a polished Markdown report. Neither
step could do the other's job.

---

## What worked well

- The separation of concerns is clean: the script produces structured data,
  the model produces narrative. Neither bleeds into the other's domain.
- The warning system makes the skill robust to real-world messy data — a common
  problem in RCM workflows where export formats vary by system.
- The CLI flags (`--threshold-days`, `--threshold-amount`) make the script
  genuinely reusable without touching the code.
- The SKILL.md description is specific enough that an agent could reliably
  activate it from natural language requests without ambiguity.

## Limitations

- Does not validate CPT, ICD-10, or HCPCS codes — only processes what is in
  the CSV
- Does not connect to live claim adjudication systems or payer portals
- Date parsing supports four formats only; ISO 8601 with time components
  (e.g., `2026-04-27T14:00:00`) is not supported
- Denial rate statistics are flagged as unreliable below 10 claims but not
  suppressed; the user should interpret with caution
- The `--threshold-amount` flag is in USD and not adjusted for currency

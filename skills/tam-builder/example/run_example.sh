#!/usr/bin/env bash
# Rebuild every file in output/ from input/ and the three model versions. Standard library Python 3.8+ only.
set -euo pipefail
cd "$(dirname "$0")"
S=../scripts
AS_OF=2026-01-15                        # the example's "today", so recency multipliers never drift
mkdir -p output
cp input/accounts.csv output/accounts.csv
rm -f output/evidence.csv
python3 $S/score.py --check

# 0. Evidence: what the page readers extracted (input/extractions.csv) is checked against the saved pages (input/pages/,
#    as fetch_pages.py writes them). Lines whose quote is not on the page, whose value is off the list or whose number is
#    not in the quote are rejected; a value that disagrees with the list is a conflict for a person. See the report.
python3 $S/apply_evidence.py --model model_v3.json --extractions input/extractions.csv --pages input/pages \
  --accounts output/accounts.csv --evidence-out output/evidence.csv --report output/evidence_check.csv

# 1. Tune on the test set: the rows with a test_group (strong, decent, bad), one S<n>- column set per model version.
python3 - <<'PY'
import csv
rows = [r for r in csv.DictReader(open("input/accounts.csv", newline="")) if r["test_group"]]
w = csv.DictWriter(open("output/test_set.csv", "w", newline=""), fieldnames=list(rows[0]), lineterminator="\n")
w.writeheader(); w.writerows(rows)
PY
python3 $S/score.py --model model_v1.json --file output/test_set.csv --as-of $AS_OF --write
python3 $S/score.py --model model_v2.json --file output/test_set.csv --as-of $AS_OF --write --next
python3 $S/score.py --model model_v3.json --file output/test_set.csv --as-of $AS_OF --write --next
python3 $S/score.py --model model_v3.json --file output/test_set.csv --groups

# 2. Roll the accepted model out to the full list.
python3 $S/score.py --model model_v3.json --file output/accounts.csv --as-of $AS_OF --write

# 3. Fact packs for hot and warm rows, briefs checked against them, then applied.
python3 $S/brief_facts.py --model model_v3.json --file output/accounts.csv --evidence output/evidence.csv --out output/facts.jsonl
python3 $S/check_briefs.py --model model_v3.json --facts output/facts.jsonl --briefs briefs.csv --apply output/accounts.csv
rm -f output/accounts.csv.bak

# 4. The ranked page, in the client's own look. theme.json comes from the client's homepage: theme_probe.js reads it
#    in a browser, brand_theme.py turns that into colors for a light and a dark page. Relaydesk's homepage is invented,
#    so its probe is a saved file here.
python3 $S/brand_theme.py --probe input/homepage_probe.json --client "Relaydesk" --out output/theme.json
python3 $S/render_page.py --model model_v3.json --file output/accounts.csv --evidence output/evidence.csv --out output/ranked.html --title "Relaydesk target accounts (invented example)" --theme output/theme.json --as-of $AS_OF

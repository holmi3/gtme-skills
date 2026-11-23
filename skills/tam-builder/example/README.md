# Worked example: Relaydesk (invented)

Everything here is made up. Relaydesk is a fictional company that sells a shared inbox and ticket routing tool to B2B support teams of about 15 to 300 agents. The 28 accounts use `.example` domains, invented numbers and invented evidence URLs.

## Run it
```
bash run_example.sh
```
Python 3.8 or newer, standard library only. It rebuilds everything in `output/` from `input/` and the three model files, with "today" fixed at 2026-01-15 so the numbers never drift.

## What it shows
| Step | Files | What to look at |
|---|---|---|
| Universe | `input/accounts.csv` | one row per domain, a `test_group` on 15 rows, three rows that must be disqualified (under 20 staff, a competitor, the seller itself) |
| Context and look | `input/homepage_probe.json`, `output/theme.json` | what `theme_probe.js` would read on Relaydesk's (invented) homepage, and the light and dark theme `brand_theme.py` builds from it, 20 of 20 contrast checks passing |
| Pages and evidence | `input/pages/`, `input/extractions.csv`, `output/evidence_check.csv`, `output/evidence.csv` | saved page text as `fetch_pages.py` writes it, 13 extracted facts, and the check: 9 kept, 4 rejected (a number not in its quote, a quote not on the page, a value off the list, a page never saved) and 1 conflict left for a person |
| Tune | `model_v1.json` to `model_v3.json`, `output/test_set.csv`, `iterations.md` | S1 fails because big consumer contact centers score like strong fits; S2 adds the product's ceiling; S3 raises the consumer penalty and passes the stop rule |
| Score | `output/accounts.csv` | the accepted model on all 28 rows: hot 6, warm 8, cold 8, research 3, out 3 |
| Briefs | `output/facts.jsonl`, `briefs.csv` | 14 fact packs for hot and warm rows, and the 14 briefs written from them; `check_briefs.py` holds every number to its pack |
| Page | `output/ranked.html` | open from disk, in Relaydesk's colors and font; click a band tile to filter, a row for the brief, owner, receipts and sources; the button top right switches light and dark; "Try other weights" above the tiles re-sorts the list as you move the sliders |

## Try breaking it
- Change one word inside a quote in `input/extractions.csv` and rerun: that line is rejected and its fact never reaches the list.
- Change `"page_bg"` in `input/homepage_probe.json` to a dark color and rerun: the page opens dark and the light mode is derived.
- Change a number in one brief in `briefs.csv` and rerun: the checker fails on that row and the page is not rebuilt.
- Set `"b2c": -6` back in `model_v3.json` and run `python3 ../scripts/score.py --model model_v3.json --file output/test_set.csv --write --next --as-of 2026-01-15`, then `--groups`: separation fails again.

---
name: tam-builder
description: Build a scored, ranked TAM (total addressable market) account list for a client company from public signals, end to end - learn the client from their website into a context layer, define the ICP and exclusions, build the account universe, read public pages and keep only quotes that check out, score with a deterministic formula, tune it on a known test set, write a brief and likely owner per top account, and render a ranked page in the client's own colors and fonts. Use when asked to build a TAM, a target account list, an ICP-scored account list, account tiers for sales, or "which accounts should we go after first and why".
---

# TAM builder

A TAM is not a list of logos. It is a ranked list where every account says why it ranks, who likely owns the decision, and what is still unknown, built so a rep trusts it and a RevOps lead can change a weight and rerun it in seconds.

This skill runs the whole flow, from a client's homepage to a ranked page in the client's look, in nine stages with a human checkpoint after stages 1, 4, 7 and 8. It builds a context layer from `context-layer-template/`, reuses the scoring approach of `skills/scored-lead-model/` and the tuning loop of `skills/score-tuning/`, and ships the scripts to run it (`scripts/`, Python 3 standard library only; the theme probe is page JavaScript). A complete worked example on invented data is in `example/` (`bash example/run_example.sh`).

```
client website --> 0 context layer + theme --> 1 ICP and model --> 2 universe --> 3 pages, extraction, quote check
  --> 4 score and tune --> 5 briefs and owner --> 6 ranked page in the client's look --> 7 hand check --> 8 export
```

## Ground rules (every stage)
- **Public sources only**, unless the owner names an approved internal source. Read politely: robots.txt, a pause between requests, a few pages per company, never behind a login. Every fact gets `[source: <url>, read YYYY-MM-DD]` in an evidence file. Passive reads: no logins, no probing, no form submissions.
- **Accounts before contacts.** This skill builds and scores companies. People's names, emails and profile URLs never go into the list, the repo or the page; a later, separate step finds contacts in a CRM or a private sheet.
- **Never invent.** A missing value is `unknown`. "Not found after reading <page>" is a finding; "not checked" is not, and never appears in a brief.
- **A model reads, a script counts.** LLMs turn pages into closed-list values with a quote and a confidence. `scripts/score.py` turns values into points from a JSON model. Nobody types a score.
- **Spend is approved.** Before any paid enrichment or model run at scale: run 10 rows, show the cost and the output, then ask. Test "missing data" on value columns, never on URL or ID columns.
- **Nothing sends, nothing syncs** to a CRM without the owner's explicit go.

## Stage 0: learn the client from their website
Follow `references/context-from-website.md`:
1. `python scripts/fetch_pages.py --domain <client-domain> --preset client --out <client>-context/research/pages` saves the client's homepage, pricing, customers, product, integrations, trust, about and careers pages as text (robots.txt obeyed, a pause between requests, nothing behind a login). Pages a script cannot read are read with a browser tool and registered with `--import-text`.
2. Run `scripts/theme_probe.js` on the homepage in a browser tool, save the JSON, and `python scripts/brand_theme.py --probe homepage_probe.json --client "<Client>" --out theme.json` (details in `references/client-theme.md`).
3. Draft the context layer files (company, positioning, personas, ICP, signals, competitors, suppression) from the saved pages, every line tagged with its source page or `[assumption]`, and every assumption a `QUESTIONS.md` line.
4. Show the client the draft on one screen, then run the template's bootstrap interview, each question opening with the drafted answer and its source.

## Stage 1: ICP, offer and exclusions (checkpoint)
Start from the stage 0 context layer (`context/icp.md`, `positioning.md`, `personas.md`, `signals.md`, `suppression.md`) and interview the owner one question at a time on what the pages could not say. Settle:
- the offer and point of difference, before any list
- segments, with the one public signal that defines each, and which segment goes first
- size tiers (primary, confirm-floor, above-ceiling, under-floor) and territory
- anti-ICP and suppression: the company itself, customers (by motion), partners, competitors and builders, under the size floor, regions out of scope
- closed lists for every column an agent will fill (industry, work mode, tool in use)
- the four score parts and their maxima (default fit 40, prize 25, awareness 15, timing 20) and the band cut-offs, set from the team's weekly capacity

Write `scoring_model.md` (spec in words) and `model.json` (the same thing as data, format in `references/model-format.md`). **Stop for approval.**

## Stage 2: universe
Build one file, `accounts.csv`, one row per root domain (lower case, no `www`). Sources, cheapest first: job-post and technology searches per segment, company search by firmographics, lookalikes of the best known accounts (round two, not round one), public customer and partner pages. Details in `references/universe.md`.
- Keep a `list_source` column (which search or list each row came from) and `segments_all` (every segment it appeared in).
- Dedupe by domain; fold subsidiaries and product domains into the parent only when the product is sold by the parent.
- Move competitors and builders into `competitors.csv` and out-of-territory rows into their own file. Disqualify, never delete, everything else: a disqualified row keeps `exclusion_reason` so nobody researches it again.
- Record the count per source and per segment in `research/YYYY-MM-DD-universe.md`.

## Stage 3: pages, extraction and the quote check
Fill the columns the model reads. Prefer a column a data source already returns over a page read, and a page read over a model guess. For page reads:
1. **Read.** `python scripts/fetch_pages.py --domains accounts.csv --preset account --out pages --limit 10` first; look at `pages/index.csv` and a few saved files, then run the rest (hot and warm candidates first if the list is large). It obeys robots.txt, waits between requests, saves text only, and follows each homepage's own link to careers. Blocked or JavaScript-drawn pages: read them with a browser tool and register them with `--import-text`.
2. **Extract.** Writers (people, or model subagents in shards of about 50 domains) use `references/page-extraction-prompt.md`: one line per fact with a closed-list value, a word-for-word quote, the page URL and a confidence. Nothing else.
3. **Check and apply.** `python scripts/apply_evidence.py --model model.json --extractions extractions.jsonl --pages pages --accounts accounts.csv --evidence-out evidence.csv --report evidence_check.csv` keeps a line only if its quote is on the saved page, its value is on the closed list and its number is in its quote. It fills blank cells, reports conflicts with values already on the list for a person to settle, writes the kept lines to `evidence.csv`, and sets the model's read column (`page_read`) on every domain with a saved page; confidence depends on it. Run with `--dry-run` first.
4. **Coverage.** Report filled share per column: a signal empty on most rows is tracked, not scored, until coverage improves. "Not found after reading <page>" (`none_found` with a `[checked]` note) is a finding; a page never read is not.

## Stage 4: score and tune (checkpoint)
1. Pick a test set before scoring: 5 strong (real customers or obvious fits), 5 decent, 5 bad, as `test_group` on copies of those rows in `test_set.csv`.
2. `python scripts/score.py --model model.json --file test_set.csv --write` (baseline set S1), then `--groups`.
3. Follow `skills/score-tuning/SKILL.md`: judge every row against the rubric with a fact, name the cause (weight, input or test group), change one thing, rerun with `--next`, log it. Stop when strong > decent > bad with a gap of at least 5, or after three changes with the blocker written down.
4. Roll out: `python scripts/score.py --model model.json --file accounts.csv --write`. The main file carries one set only, the accepted model.

Show the owner the iteration log, the band counts and the top 25. **Stop for approval.**

## Stage 5: briefs and likely owner
For hot and warm rows only:
1. `python scripts/brief_facts.py --model model.json --file accounts.csv --evidence evidence.csv --out facts.jsonl` builds one fact pack per row: what the company is, the reasons it ranks (strongest first, points removed), signals, the likely owner from the model's first-match `owner_rules`, and what is unknown.
2. Writers (people, or model subagents in shards of about 150 rows) write one paragraph per pack from the pack alone, using `references/brief-writer-prompt.md`.
3. `python scripts/check_briefs.py --model model.json --facts facts.jsonl --briefs briefs.csv` fails any brief with a number not in its pack, score language, internal wording, a dash, a link, a missing owner title, the wrong length, or a duplicate. Fix and rerun until it passes, then add `--apply accounts.csv`.

The owner is a title, never a person, and every owner basis that rests on judgment ends `[assumption]`.

## Stage 6: ranked page in the client's look
`python scripts/render_page.py --model model.json --file accounts.csv --evidence evidence.csv --out ranked.html --title "..." --theme theme.json --as-of <the date score.py used>`. One self-contained file: band tiles that filter, search, the ranked table, and per account the brief, the owner, a receipt for every point and the sources. It also carries a closed "Try other weights" panel: a slider per rule that adds points (starting at the model's weights) and the hot and warm cut-offs, which re-score and re-sort the list in the browser, for talking through weights with the owner. Nothing on disk changes. The panel lists the model.json edits that reproduce a what-if ranking; ones the owner wants go into the model file and back through stage 4. The script only adds the panel when the model reproduces every part, total, band and confidence on the file, so pass the same `--as-of` as the scoring run; otherwise it leaves the panel out and says why (`--no-weights` leaves it out on purpose). With the stage 0 theme it uses the client's colors, font and corners, says "Prepared for <Client>", opens in the site's own mode, and has a Light / Dark switch; every color pair has passed a contrast check. Open it next to the client's homepage and compare before anyone else sees it (`references/client-theme.md`). Readability for sales matters more than completeness: bands with plain definitions, a legend, the brief first, numbers second.

The theme is for a page made for that client. Do not publish a page that imitates a company to anyone else, and leave the logo out unless the client provides it.

## Stage 7: hand check (checkpoint)
Follow `references/hand-check.md`: a fixed-seed sample of 25 hot accounts, one claim and its link per account, checked by a person. Record good, stale (a closed job post), wrong. Fix the input or the rule behind each wrong row, rerun stages 4 to 6, and note the result in the research log. **Stop for the owner's sign-off.** Do not quote an accuracy number before a hand check.

## Stage 8: export and handoff (checkpoint)
- `accounts.csv` sorted by band then total, with a short data dictionary (`README.md` next to it) and the page.
- A one-paragraph summary: universe size, band counts, what the score rests on, what it does not know, the date it was built and when it goes stale.
- Ask the owner before anything leaves the folder: emailing it, sharing a link, or a CRM import. Contacts are a separate, later step.

## Refreshing
Rerunning is cheap by design: change a weight and rerun stage 4 onward. Re-pull the fluid signals (timing) on a schedule; fit and prize change rarely. Any change to the model goes through the iteration log, never a hand edit to a score column.

## Files
| Path | What |
|---|---|
| `scripts/fetch_pages.py` | polite public-page reader: presets for the client and for accounts, robots.txt, saved text plus an index, `--import-text` for browser reads |
| `scripts/apply_evidence.py` | checks every extracted fact against its saved page and the closed lists, fills the list, reports conflicts |
| `scripts/theme_probe.js` | page JavaScript that reads a homepage's computed colors, fonts and main button |
| `scripts/brand_theme.py` | probe in, `theme.json` out: light and dark tokens, contrast checked and fixed, review notes |
| `scripts/score.py` | the scorer: JSON model in, S<n>- column sets out, `--next`, `--groups`, `--test`, `--check` |
| `scripts/brief_facts.py` | fact packs and likely owner for hot and warm rows |
| `scripts/check_briefs.py` | holds every brief to its pack; `--apply` writes briefs onto the list |
| `scripts/render_page.py` | the ranked page, with `--theme` for the client's look and a what-if weights panel |
| `references/context-from-website.md` | stage 0: the context layer and theme from the client's website |
| `references/page-extraction-prompt.md` | the prompt that turns saved pages into checked facts |
| `references/client-theme.md` | reading the client's look and checking the page against it |
| `references/model-format.md` | the model JSON: parts, rule types, disqualify, confidence, bands, owner rules, brief settings |
| `references/universe.md` | building and cleaning the universe |
| `references/brief-writer-prompt.md` | the prompt for brief writers |
| `references/hand-check.md` | the hand check procedure |
| `example/` | the whole flow on invented data |

## Credits
The TAM method (breadth list first, formula scoring, readable bands for sales, hand check before any accuracy number) was learned in Jared Waxman's GTM Engineer School.

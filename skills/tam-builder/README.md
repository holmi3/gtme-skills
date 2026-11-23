# TAM builder

Give it a client's website and it builds them a ranked list of accounts to go after. Every account shows why it ranks. The top ones also get a likely owner and a note on what's still unknown, and the whole list comes out as one page in the client's own colors and fonts.

Everything it needs is in this folder, so you can copy it into your agent's skills directory on its own.

- `SKILL.md` runs the whole flow in nine stages, and a person signs off after stages 1, 4, 7 and 8.
- `scripts/` does the fetching, checking, scoring and rendering (Python standard library only, plus one browser script that reads the client's look).
- `references/` has the prompts and notes the stages use.
- `skills/scored-lead-model/` and `skills/score-tuning/` are the scoring approach and the tuning loop it uses.
- `context-layer-template/` is the blank context layer that stage 0 copies and fills in for each client.
- `example/` is a worked run on Relaydesk, a made up company with 28 made up accounts.

## Try it

```
cd example
bash run_example.sh        # Python 3.8+, standard library only
open output/ranked.html
```

That rescores the 28 accounts, checks the 14 briefs and rebuilds the page.

The page has a "Try other weights" panel. There's one slider per scoring rule plus the hot and warm cut-offs, and the list re-sorts as you drag. So when sales says "what if timing mattered more", you can show them in the meeting instead of promising a rerun. It starts at the model's own weights and changes nothing on disk. If a set of weights wins, put it in the model file and rescore.

## How it stays honest

A model (or a person) reads each page and pulls out a value with a word for word quote. A script checks that the quote is on the saved page before it counts, and another script does the scoring, so changing a weight is a one line edit and a rerun. It reads public pages politely (robots.txt, a pause between requests, nothing behind a login) and never puts people's names in the list.

## Author
Built by Aaron Holmblad ([github.com/holmi3](https://github.com/holmi3)). MIT licensed, see [LICENSE](LICENSE).

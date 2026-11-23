# GTM engineering skills

These are skills I built and ran for go-to-market work, cleaned up so anyone can use them. There's no real data in these copies (the examples use made up companies on `.example` domains).

- [TAM builder](skills/tam-builder/) starts from a client's website and ends with a ranked account list, a short brief for each top account, and a page in the client's own colors. The page has sliders for the weights, so you can try "what if timing mattered more" with the client and watch the list re-sort. Start here. Everything it needs is in that folder, so you can copy it on its own, and it has its own README. Inside it are the [scored lead model](skills/tam-builder/skills/scored-lead-model/), which does the scoring, and [score tuning](skills/tam-builder/skills/score-tuning/), which adjusts it one change at a time. The [context layer template](skills/tam-builder/context-layer-template/) is the plain file "company brain" it fills in for each client.
- [Copy review](skills/copy-review/) is a second reader for every draft. It scores how AI the draft sounds and says PASS or REVISE.
- [Outreach learning loop](skills/outreach-learning-loop/) turns what got replies into rule changes a person approves.

```
skills/
  tam-builder/
    skills/
      scored-lead-model/
      score-tuning/
    context-layer-template/
    scripts/  references/  example/
  copy-review/
  outreach-learning-loop/
```

Wherever there's a score, the model reads and a script does the math, so you can check every number. And nothing sends or merges until a person says yes.

## Try it

```
cd skills/tam-builder/example
bash run_example.sh        # Python 3.8+, standard library only
open output/ranked.html
```

To install a skill, copy its folder into your agent's skills directory. Each skill has a `SKILL.md`, the format Claude Code reads.

## Author
Built by Aaron Holmblad ([github.com/holmi3](https://github.com/holmi3)), GTM engineer. The methods were learned in Jared Waxman's GTM Engineer School and generalized from systems I built and ran during it.

## Credits
- The context layer template is inspired in part by the brainstarter skill from Jared Waxman's GTM Engineer School. The refresh loop, suppression rules and learning from outreach results are my additions.

## License
MIT. See [LICENSE](LICENSE).

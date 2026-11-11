# Suggested pilot cases from six Buffy episodes

These **normalized line numbers** were derived from the exact six `.htm` examples supplied in this ScriptLab development session. They are not original HTML source line numbers. Always reopen the JSON to recheck ranges if you replace the source files.

| Episode (original file) | Normalized range | Known challenge | Source clue |
|---|---:|---|---|
| S02E03 *School Hard* (`2x03.htm`) | 15–70 | Ordinary centered dialogue baseline | Early episode exchanges |
| S03E15 *Consequences* (`3x15.htm`) | 525–570 | Provisional scenes at normalized 545 and 560 | HTML source lines ~794 and 816 |
| S04E22 *Restless* (`4x22.htm`) | 975–1005 | `VOICE:` cue | HTML source line ~1605 |
| S04E22 *Restless* | 1290–1310 | Second `VOICE:` cue | HTML source line ~2088 |
| S04E22 *Restless* | 1496–1505 | Website link after `END OF SHOW` | HTML source line ~2420 |
| S05E11 *Triangle* (`5x11.htm`) | 880–902 | Double-`<BR>` followed by Willow | Normalized cue ~891 |
| S06E03 *After Life* (`6x03.htm`) | 248–265 | Continued `DAWN (cont'd.)` | Normalized cue ~258 |
| S06E03 *After Life* | 360–380 | Misspelled `XAN'DER` | Normalized cue ~371 |
| S06E03 *After Life* | 1265–1290 | `DEMON (V.0.)` | Normalized cue ~1274 |
| S06E07 *Once More, With Feeling* (`6x07.htm`) | 115–145 | Simultaneous/parallel dialogue table | Parallel metadata first appears ~125 |

Example command for *Restless*:

```powershell
python -m scriptlab compare --parsed output/buffy/S04E22.json --model qwen3:8b --line-start 975 --line-end 1005 --chunk-size 16 --out output/verification/S04E22_voice
```

For the first pilot, favor *Consequences* because it includes **known structural mistakes in the raw script**. After that, try *Triangle* and *Restless* before evaluating a whole episode.

# Held-out parser reviews

Holdout reviews are kept separate from `tests/fixtures/gold_cases/`, which is
used to develop and test parser rules. Do not treat agreement on these small,
challenge-oriented samples as a representative corpus accuracy estimate.

## Round 1

The local, untracked `output/holdout_review/20261111_round01.json` records
seven user-reviewed passages from seven episodes that had no approved gold
case at sampling time. All 56 classifications were confirmed, with no
reported disagreements. A local validation test reparsed the original source
files and checked recorded hashes, exact text, source and normalized line
numbers, classifications, nullable speakers, and order. The source excerpts
and validation artifacts are not distributed or promoted to the
rule-development gold fixture set.

## Round 2

The local, untracked round 2 contains seven new source-only passages, one per
season. Episodes used in round 1 and episodes with approved gold cases were
excluded. The sample was selected with seed `20261112`; it contains 60
classifications. Parser predictions were snapshotted before review and
unsealed after adjudication. The source-only review artifact remains free of
parser labels.

The comparison recorded 59/60 type matches and 18/18 explicitly adjudicated
speaker matches. The one type disagreement was a stage direction the user
classified as action while the parser classified it as a parenthetical. The
blind review was not used to tune parser rules. Source excerpts, prediction
snapshots, comparison artifacts, and the local validation test are not
included in this repository because they depend on the original episodes.

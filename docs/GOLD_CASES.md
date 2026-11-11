# Human-reviewed reference cases

Gold cases are evidence-backed regression references, not Ollama output. For
local development, store a JSON record and its small original HTML fixture
under `tests/fixtures/gold_cases/`. Episode-derived case files are gitignored
and must not be committed; shared repository tests should use synthetic
fixtures. Keep local source fragments short and never copy an entire
copyrighted episode into this package.

Each approved JSON record must include:

- `case_id`, `review_status: "human_reviewed"`, and reviewer identity.
- `source_fragment_file` and `reference_location`.
- `expected_elements`, including original cue spelling, type, and speaker where
  relevant.
- `notes` for ambiguities and how dialogue boundaries were decided.

Use `musical_direction` when a script note describes musical timing, sound,
or performance rather than character action or spoken/sung dialogue. The
parser recognizes explicit descriptions connecting notes or chords with
dissonance (for example, a "discordant note"). More ambiguous musical
directions still require human review.

Prefer grouping reviewed material into one scene-level case rather than
creating a separate fixture for every obvious line or action. Prioritize
documented parser disagreements and ambiguous boundaries or attribution;
already-correct classifications can remain in the grouped case for context.

When the parser intentionally emits a provisional classification for a
human-confirmed element, `parser_element_type` may record that current parser
output separately from the human-reviewed `element_type`.
`parser_speaker` may similarly record the parser's speaker value when it
differs from the human-reviewed speaker.
Use `parser_element_type: "missing"` to document a reviewed element that the
current parser omits.

The `pending_review.json` record is an invented example only. It is
intentionally rejected by `validate_gold_case`; it must not be used as evidence
of parser accuracy or silently promoted to gold. Once a person has checked a
case against its original HTML, set the status and reviewer, then add a
regression assertion in `tests/test_gold_cases.py`. A model response alone is
never sufficient to approve a case.

## Approved cases

The local, untracked `s02e04_reviewed.json` records reven's explicit approval
on November 10, 2026:
the compound VOICE cue, its dialogue, and two camera directions. The small
HTML fixture retains only those blocks; source locations and the original
file's SHA-256 are recorded in the JSON. The regression harness maps verifier
`shot_direction` to parser `shot_heading` without changing the saved labels.
This is a four-element reference case, not evidence of whole-episode accuracy.

The local, untracked `s02e04_act_boundary.json` records reven's second approval:
seven elements
covering action, a character cue, a parenthetical attached to Xander, a
transition, two act markers, and the next scene heading. The fixture retains
dialogue and preceding scene context without treating them as additional
reviewed elements. There are now two approved cases with eleven reviewed
element classifications, not a representative accuracy benchmark.

`s02e04_interruption.json` records the third review: Buffy's wrapped
parenthetical, the action describing Xander's interruption, two dialogue
segments attributed to Xander, and Ampata's parenthetical addressing Xander.
There are now three approved cases covering sixteen element classifications.

`s05e11_shared_center.json` records reven's fourth review: Anya's dialogue,
Willow's new cue after consecutive BR tags, and Willow's dialogue inside the
same centered block. The set now covers four cases and twenty-one element
classifications across two episodes.

`s06e03_xander_typo.json` records reven's fifth review: the original
`XAN'DER` cue identifies Xander, the intervening prose is unspoken action,
and `XANDER (cont'd)` continues the same speaker. The typo is preserved as
source evidence, not used as the speaker identity. The set now covers five
cases and twenty-four element classifications across three episodes.

`s02e04_ampata_offscreen.json` records reven's sixth review: `AMPATA (O.S.)`
identifies Ampata as the speaker of the off-screen line, followed by Buffy's
reply. The set now covers six cases and twenty-eight element classifications
across four episodes. This remains a small regression set, not a representative
accuracy benchmark.

`s03e15_malformed_scene_heading.json` records reven's seventh review: the
original `!NT.` line is a scene heading with a typo, not a different kind of
element. The malformed source text is preserved without correction. The set
now covers seven cases and twenty-nine element classifications across five
episodes; it is still not a representative accuracy benchmark.

`s06e07_simultaneous_singing.json` records reven's eighth review: Willow and
Giles sing at the same time in separate table columns. Their cues and lines
remain separate speaker-attributed turns, with simultaneity noted rather than
flattened into a sequential exchange. The set now covers eight cases and
thirty-seven element classifications across six episodes; it is not a
representative accuracy benchmark.

`s04e22_recorded_target_voice.json` records reven's ninth review: the `VOICE`
cue and line are the prerecorded voice of the toy target dummy Giles made, not
Giles speaking live. The parser attributes the dialogue to `VOICE` but omits
the cue, which the regression records explicitly. The set now covers nine
cases and thirty-nine element classifications across seven episodes; it is
not a representative accuracy benchmark.

The five `s03e*_*.json` cases record reven's review of mixed-case speaker
cues and OCR-corrupted modifiers in Season 3: Oz and Buffy cues, the
Secretary's off-screen cue, numbered CORDETTE background speakers, an
off-camera GIRL, and a STUDENT ON FLOOR. Source spellings are preserved while
speaker names and common OCR variants are normalized for attribution. The
approved fixture corpus now contains sixty cases and two hundred forty-two
element classifications across nineteen episodes; it is not a representative
accuracy benchmark.

`s03e06_latin_chanting.json` records reven's request to label the ritual
passage as Latin chanting rather than interpret or translate it. The original
words remain intact as dialogue by the ROBED FIGURES, with `(in Latin)` kept
as their parenthetical direction.

`s04e22_intercom_warning.json` records reven's tenth review: the `VOICE`
announcement warns Buffy over a loudspeaker. Reven clarified that it is spoken
by someone in the bunker whose identity is not given; the loudspeaker is the
delivery channel, not the speaker identity. The two source-separated dialogue
lines retain the generic `VOICE` attribution. As with the preceding `VOICE`
example, the parser captures the dialogue but omits the cue. The set now
covers ten cases and forty-two element classifications across seven episodes;
it is not a representative accuracy benchmark.

`s06e07_tara_singing_cue.json` records reven's eleventh review: Tara's
`(sings)` parenthetical and lyric are attributed to Tara as part of the same
turn. Only a short lyric fragment is retained in the fixture. The set now
covers eleven cases and forty-five element classifications across seven
episodes; it is not a representative accuracy benchmark.

`s06e07_xander_anya_living_room_song.json` records reven's review of the
living-room song: alternating Xander/Anya lines are sung dialogue, and lines
under their shared cue are simultaneous. The fixture samples rather than
reproduces the full song. The set now covers thirty-four cases and one hundred
seventeen element classifications across seven episodes; it is not a
representative accuracy benchmark.

`s06e07_xander_anya_verse_interruption_dance.json` groups Xander's interrupted
verse, Anya's response, and their dance directions. The set now covers
thirty-five cases and one hundred thirty-two element classifications across
seven episodes; it is not a representative accuracy benchmark.

`s06e07_xander_anya_charm_duet.json` records the sung exchange beginning with
the simultaneous "YOU KNOW," followed by alternating solo lyrics and dance
directions. The set now covers thirty-six cases and one hundred forty-six
element classifications across seven episodes; it is not a representative
accuracy benchmark.

`s06e07_xander_anya_verses_get_closer.json` groups the alternating sung
verses and the stage direction of the couple getting closer. The set now
covers thirty-seven cases and one hundred sixty-one element classifications
across seven episodes; it is not a representative accuracy benchmark.

`s06e07_xander_anya_fears_love_song.json` records the parenthetical
`(waving the camera away)` under Xander's cue; the source wraps it across a
BR, so the two parser-produced fragments are tested separately. It also
records the post-song collapse as action and `SMASH CUT TO:` as direction
(transition). The set now covers thirty-eight cases and one hundred sixty-five
element classifications across seven episodes; it is not a representative
accuracy benchmark.

`s04e22_end_show_draft_link.json` records reven's twelfth review:
`END OF SHOW` is the script ending, and the following invitation with an
embedded writer's-draft URL is supplementary material, not part of the
script. The set now covers twelve cases and forty-seven element
classifications across seven episodes; it is not a representative accuracy
benchmark.

`s06e07_tara_lyric_action.json` records reven's thirteenth review: the walk
into the sunlight is action, and lyrics after the continued Tara cue are still
Tara's. The set now covers thirteen cases and fifty-two element
classifications across seven episodes; it is not a representative accuracy
benchmark.

`s06e07_tara_turning_direction.json` records reven's fourteenth review:
`(turning to Willow)` is action, specifically a stage direction, between
Tara's lyrics. The parser currently labels it as a parenthetical. The set now
covers fourteen cases and fifty-three element classifications across seven
episodes; it is not a representative accuracy benchmark.

`s06e07_street_overlapping_comments.json` records the street exchange as
spoken dialogue, with Xander and Anya's two-column comments overlapping as
they talk over each other. The fixture samples the exchange. The set now
covers thirty-nine cases and one hundred eighty element classifications
across seven episodes; it is not a representative accuracy benchmark.

`s06e08_buffy_hurt_cue.json` records reven's confirmation that `BUFFY` is
the cue, `(hurt)` is a parenthetical direction, and the following question is
Buffy's dialogue. The cue and direction share one source line, which is
retained and attributed to Buffy. This case also exercises recognition of a
known HTML speaker followed by a descriptive parenthetical. The set now
covers forty cases and one hundred eighty-two element classifications across
eight episodes; it is not a representative accuracy benchmark.

`s06e08_vamp_cue_run_together.json` records reven's confirmation that the
`VAMP #2` cue and spoken line are run together in the source. The original
line is preserved as dialogue attributed to VAMP #2; the cue is not split into
a separate source element. The set now covers forty-one cases and one hundred
eighty-three element classifications across eight episodes; it is not a
representative accuracy benchmark.

`s06e08_buffy_run_together_garbled.json` records reven's confirmation that
Buffy speaks the line following her run-together cue. Malformed HTML is
preserved and reported as a reader warning; the extracted line is attributed
to Buffy as dialogue, with a separate warning to review the source line break.
The set now covers forty-two cases and one hundred eighty-four element
classifications across eight episodes; it is not a representative accuracy
benchmark.

The approved table cases also serve as parser regressions for narrow
two-column tables inside CENTER markup. Their row and column metadata is
preserved on reconstructed dialogue turns so overlapping or simultaneous
speakers are not flattened into sequential dialogue. The parser distinguishes
the explicit discordant-note direction as `musical_direction`; this remains a
conservative rule and does not classify every paragraph mentioning music as a
musical direction.

`s06e07_tara_handholding_action.json` records reven's fifteenth review: the
sentence describing Tara and Willow walking and dancing together is action
between Tara's lyrics. The set now covers fifteen cases and fifty-four element
classifications across seven episodes; it is not a representative accuracy
benchmark.

`s06e07_tara_fairy_dust_action.json` records reven's sixteenth review: Tara's
hand-tracing and fairy-dust description is action between her lyrics. The set
now covers sixteen cases and fifty-five element classifications across seven
episodes; it is not a representative accuracy benchmark.

`s06e07_willow_light_trail_action.json` records reven's seventeenth review:
Willow's matching gesture and more spectacular light trail are action between
Tara's lyrics. The set now covers seventeen cases and fifty-six element
classifications across seven episodes; it is not a representative accuracy
benchmark.

`s06e07_willow_spin_scene_transition.json` records reven's eighteenth review:
the sentence about Willow spinning Tara and the transition into the bedroom is
action leading into a new scene. The destination scene heading is contextual,
not an additional approved classification. The set now covers eighteen cases
and fifty-seven element classifications across seven episodes; it is not a
representative accuracy benchmark.

`s06e07_bedroom_spinning_action.json` records reven's nineteenth review: the
description of Willow and Tara spinning, settling onto the bed, and moving
close is action. The set now covers nineteen cases and fifty-eight element
classifications across seven episodes; it is not a representative accuracy
benchmark.

`s06e07_tara_pillow_action.json` records reven's twentieth review: the
description of Tara falling onto pillows and the camera staying close as Willow
moves over her is action. The set now covers twenty cases and fifty-nine
element classifications across seven episodes; it is not a representative
accuracy benchmark.

`s06e07_tara_floating_action.json` records reven's twenty-first review: the
description of Tara rising from the bed and floating is action between her
lyrics. The set now covers twenty-one cases and sixty element classifications
across seven episodes; it is not a representative accuracy benchmark.

`s06e07_smash_cut_transition.json` records reven's twenty-second review:
`SMASH CUT TO:` is a transition before the Magic Box scene. The set now covers
twenty-two cases and sixty-one element classifications across seven episodes;
it is not a representative accuracy benchmark.

`s06e07_music_cut_xander_action.json` records reven's twenty-third review:
the sentence about the music cutting off and Xander speaking is action
introducing Xander's dialogue. The set now covers twenty-three cases and
sixty-two element classifications across seven episodes; it is not a
representative accuracy benchmark.

`s06e07_xander_censors_himself.json` records reven's twenty-fourth review:
Xander's `(seeing Dawn)` parenthetical interrupts his sentence as he censors
himself, and both dialogue fragments remain his. The source's line break
splits the second fragment into two parser elements. The set now covers
twenty-four cases and sixty-six element classifications across seven episodes;
it is not a representative accuracy benchmark.

`s06e07_xander_buffy_simultaneous.json` records reven's twenty-fifth review:
the shared `XANDER/BUFFY` cue and line are spoken by both characters at the
same time. The shared cue spelling is preserved alongside the two reviewed
speaker identities. The set now covers twenty-five cases and sixty-eight
element classifications across seven episodes; it is not a representative
accuracy benchmark.

`s06e07_alley_dancer_action.json` records reven's twenty-sixth review: the
description of the frantically dancing man in the alley is action. The set now
covers twenty-six cases and sixty-nine element classifications across seven
episodes; it is not a representative accuracy benchmark.

`s06e07_alley_dancer_smoking_action.json` records reven's twenty-seventh
review: the dancer continuing and beginning to smoke is action. The set now
covers twenty-seven cases and seventy element classifications across seven
episodes; it is not a representative accuracy benchmark.

`s06e07_alley_dancer_ignites_action.json` records reven's twenty-eighth
review: the dancer igniting and burning down to ash and bone is action. The
set now covers twenty-eight cases and seventy-one element classifications
across seven episodes; it is not a representative accuracy benchmark.

`s06e07_alley_corpse_and_figure_action.json` records reven's twenty-ninth
review: the burning corpse falling and the new figure's visual introduction
are action. The set now covers twenty-nine cases and seventy-two element
classifications across seven episodes; it is not a representative accuracy
benchmark.

`s06e07_sweet_introduction_action.json` records reven's thirtieth review: the
line identifying Sweet and describing his look at the corpse and smile is
action. The set now covers thirty cases and seventy-three element
classifications across seven episodes; it is not a representative accuracy
benchmark.

`s06e07_sweet_first_line.json` records reven's thirty-first review: SWEET is
the cue and speaker for the spoken dialogue "That's entertainment..." The set
now covers thirty-one cases and seventy-five element classifications across
seven episodes; it is not a representative accuracy benchmark.

`s06e07_act_boundary.json` records reven's thirty-second review: BLACK OUT is
camera action, followed by the non-spoken act-ending and next-act markers. The
parser currently labels BLACK OUT as a transition. The set now covers
thirty-two cases and seventy-eight element classifications across seven
episodes; it is not a representative accuracy benchmark.

`s06e07_xander_anya_bedroom_scene.json` consolidates twelve previously
approved micro-cases into one scene-level fixture, preserving their reviewed
classifications. It includes the opening action, breakfast exchange, waffles
discussion, kiss, omelette exchange, and short song/direction excerpts.
`(catches himself)` is a parenthetical direction, not spoken dialogue; the
parser's parenthetical classification agrees. The reviewed embrace and Anya
wriggling free are action. The subsequent Xander lyrics are sung dialogue,
and his shared line with Anya is recorded as simultaneous. The discordant
note and movement cue is musical direction, not action or dialogue; the
parser now recognizes its explicit discordant-note wording. The living-room
movement is stage direction. The set now covers thirty-three cases and one
hundred ten element classifications across seven episodes; it is not a
representative accuracy benchmark.

`s06e02_buffy_voiceover_and_reveal.json` records reven's approval of Buffy's
spaced, OCR-corrupted V.O. cue and the subsequent dialogue, followed by a
camera direction, whispered cue, and two spoken lines separated by
`(then)`. The set now covers thirty-four cases and one hundred eighteen
element classifications across eight episodes; it is not a representative
accuracy benchmark.

`s06e05_buffy_paragraph_cue.json` records reven's approval that a standalone
BUFFY paragraph cues the dialogue in the immediately following paragraph.
The set now covers thirty-five cases and one hundred twenty element
classifications across nine episodes; it is not a representative accuracy
benchmark.

`s06e10_buffy_malformed_cue.json` records reven's approval that the malformed
`BUFFY,br>` cue is a typo and BUFFY speaks the following dialogue. The source
is preserved as written.

`s06e16_creature_actor_direction.json` records reven's clarification that
`(taken aback}` is an actor direction, not dialogue. The mismatched brace is
preserved as source text.

`s03e05_camera_direction.json` records reven's classification of the long-lens
slug as a camera direction. `s03e15_malformed_scene_heading.json` records
reven's confirmation that `!NT.` is a typo in a scene heading and that the
following unprefixed Buffy's house slug is also a scene heading.

The approved fixture corpus now contains seventy-seven cases and three hundred
twenty-nine reviewed element classifications; it is not a representative
accuracy benchmark.

`s06e11_womans_voice_on_tv.json` records reven's approval that
`WOMAN'S VOICE (ON TV)` cues the following spoken television dialogue.

The six `s06e*_confirmed_scene_heading*.json` cases record reven's approval
that all nine previously flagged Season 6 location slugs are scene headings,
including irregular INT./EXT. punctuation, the missing space in `INT.CONDEMNED`,
the apparent source spelling `TREET`, and A36/B36 scene-number prefixes. Their
source text is preserved verbatim. The approved fixture corpus now contains
fifty-two cases and two hundred seven element classifications across eleven
episodes; it is not a representative accuracy benchmark.

`s02e04_centered_action_and_directions.json` records reven's approval that
standalone centered narrative prose is action and explicit camera cues such as
`CLOSE UP` and `ANGLE` are shot directions. The parser applies this distinction
to the matching one-line centered blocks while retaining ambiguous multi-line
blocks for review. The approved fixture corpus now contains fifty-three cases
and two hundred eleven element classifications across twelve episodes; it is
not a representative accuracy benchmark.

`s02e07_ford_repeats_jack_palance.json` records reven's clarification that
Ford repeats the television character's dialogue and both intone the lines.
The source's backslash-separated cue is retained verbatim while the normalized
speaker is `FORD/JACK PALANCE`.

`s02e19_fifties_girls.json` records reven's clarification that the numbered
50'S GIRL cues identify day players/extras speaking in the scene. The
approved fixture corpus now contains fifty-five cases and two hundred
twenty-three element classifications across fourteen episodes; it is not a
representative accuracy benchmark.

`s01e01_front_matter_and_annotated_cues.json` records reven's November 11,
2026 review: the opening title/date/byline are metadata; the centered
description is action; the attack description is action followed by
`BLACKOUT.` as a transition; `BUFFY’S MOM (O.S.)` is Joyce; and the handwritten
`- AURA` note belongs to what Girl #3 sees, not the speaker identity. The
chanting-fills-the-room line is action rather than spoken dialogue. This
fixture covers fourteen classifications in one episode and is not a
representative accuracy benchmark.

`s01e06_reporter_on_tv.json` records reven's confirmation that
`REPORTER (T.V.)` cues spoken television-news dialogue, attributed to REPORTER.
`s01e11_buffy_photo_dialogue.json` records that “person. This person.” continues
Buffy's line about Marcie's photo; the photo-showing direction and following
question also remain part of Buffy's turn.

The additional Season 1 cases record reven's review of centered action in
episodes 2 and 5, Xander's statement after a wrapped parenthetical in episode
3, Darla's dialogue in episode 7 despite a malformed tag, and three
descriptively prefixed location headings confirmed as scene headings. The bad
HTML warning is treated as non-blocking; original source text remains
unchanged.

The Season 4 cases record Tara's spoken Latin in episode 17 separately from
the parenthetical translation label and reader-only English rendering, plus
three centered dialogue blocks attributed to Colonel McNamara in episodes 19
and 21.

The Season 5 episode 13 case records two remembered lines as dialogue spoken
by the Lunatic and Nightwatchman, with the episode references directing the
production to use the same actors from those earlier episodes. The references
are not part of the character speaker names.

The Season 5 episode 16 case records the 911 Operator's off-screen phone
statements. The operator's real identity is unknown; the role cue is retained
as the speaker label, and `(O.S.)` remains a delivery modifier.

The Season 5 episode 20 case records `BUFF'Y` as a typographical cue variant
for Buffy; the source spelling is preserved while the dialogue is attributed
to BUFFY.

The Season 7 case records two user-confirmed location headings, including
their original unusual wording. Both are recognized as scene headings without
silently correcting the source text.

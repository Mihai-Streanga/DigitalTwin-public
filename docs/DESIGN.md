# Design notes — the ear and the voice

Why speech input and output work the way they do. Each choice below was measured on the
development machine (Windows 11, Intel integrated GPU), in August 2026; the alternatives
that lost are listed too, because they are the obvious first thing to try.

The code is in `server/transcriere.py` (the ear), `server/voce.py` (the voice) and
`server/web/pagina.js` (the sentence pipeline in the page).

---

## The ear: speech to text

**Engine.** Whisper `large-v3-turbo`, int8, through OpenVINO GenAI on the integrated GPU.
A 2–6 s utterance transcribes in **0.26–0.43 s**; a 40 s clip in 1.12 s. Romanian comes out
with diacritics.

### Whisper cannot say "I heard nothing"

Given noise and no speech, Whisper produces text with the same confidence it gives a real
transcript. Measured through the server: "Să vă mulțumim pentru vizionare!" ("Thanks for
watching!") on room noise at RMS 0.002 and 0.008, "Amplified." at 0.020 and 0.040. In real
use, silence once came out as **"Hún er hann."** — Icelandic — and went on to the language
model, which costs money.

An energy threshold cannot separate these cases: room noise passes any threshold set low
enough to let a whisper through. The engine does not help either: `scores` is 1.000 on
speech, noise and coughs alike, and the reported language is always Romanian because it is
forced.

So every utterance passes through **five nets**, in this order:

| # | net | where | what it catches |
|---|---|---|---|
| 1 | digital silence | RMS < 0.001 | a muted or dead microphone; nothing else runs |
| 2 | voice activity | Silero VAD, `PRAG_VORBIRE` = 0.20 s of speech | noise without a voice; runs **before** the engine |
| 3 | subtitle tail | `COZI_DE_SUBTITRARE`, `MAXIM_COADA` = 8 words | a closing formula glued to a real utterance |
| 4 | letters | characters Romanian does not have (ð, þ, á, í, ø, ñ) | the engine drifting into another language |
| 5 | rhythm | `PRAG_RITM` = 6 words per second of speech | text too dense to have been spoken |

**Net 2, voice activity.** Silero VAD (shipped with `faster-whisper`, installed as a
separate package) separates cleanly: pure noise up to RMS 0.100 yields **0.00 s** of
speech, speech lowered to RMS 0.005 is caught whole, and a 0.38 s "Da." passes. It costs
**5–10 ms** and sits in front of the engine, so an utterance without speech never touches
the GPU.

**VAD does not catch everything.** A cough has vocal cords in it, so Silero calls it
speech. On the same day it produced "Cough.", and the next utterance "Svík, hvað er það?".
Nets 4 and 5 judge the **text**, and neither is a word list: Romanian has no ð or þ, and
6 words per second of detected speech is nearly double fast human speech (a measured
control gives 3.3; "Da." gives 1.8). Both cut the two real hallucinations, and both let
through old-style Romanian diacritics (`ş`, `ţ`) and English jargon.

**Net 3 cuts the tail, not the utterance.** The other nets judge the whole utterance, so
they cannot catch Whisper appending a subtitle outro to real speech: once, 28.8 s of clean
speech ended in "Să vă mulțumim pentru vizionare!". The model was trained on video
subtitles and fills the trailing silence with the closing line. The net looks **only at
the last sentence**, cuts it only if it is short (under 8 words) and only if some text
remains — an utterance that is *only* the outro is left to the other nets. It runs before
nets 4 and 5, because a glued outro would also distort the word count behind the rhythm.

**What still gets through is handled in the page.** While the twin is thinking or speaking,
the ear is **deaf**, not just paused: a cough once landed in the synthesis window, became a
new message and cut the answer in half. The accepted cost: you cannot interrupt it by
talking; you interrupt it with a click.

**Every utterance leaves a line on disk** (`date/ureche.log`): time, audio length, seconds
of speech found by VAD, the verdict and the text — or the refused text — plus a `taiat: …`
column when a tail was cut. Any complaint about the ear starts there.

### GPU first, CPU as the fallback

`DISPOZITIVE = ("GPU", "CPU")`: the first device that compiles wins. The fallback is **the
same OpenVINO model**, not another engine, so it writes exactly the same words, with the
same diacritics and the same mistakes. On the same three clips (1.8 / 7.1 / 13.7 s):

| device | time |
|---|---|
| integrated GPU | 0.25 / 0.36 / 0.55 s |
| CPU | 2.28 / 2.44 / 2.87 s |

Six to nine times slower, plus about 5 s once when falling back (1.2 s compile, 3.8 s
warm-up). That is noticeable, so **it is shown**: a line in the conversation at startup and
a permanent "ear on CPU" in the status bar. A slow ear with no explanation looks exactly
like a broken microphone.

The GPU can also fail **after** the engine started — a driver reset, memory taken by another
program. The device is then burned for the session and the next utterance goes to the CPU;
restarting the server retries the GPU. If nothing is left underneath, the face turns red and
the error is written below it.

Two OpenVINO pipelines on the same integrated GPU were feared to conflict. They did not: with
the server already holding one, a second compiled in 3.2 s and ran at the same speed.

**Alternatives that lost:**

- `faster-whisper` on CPU with `small`: faster (1.5 s) but mangles technical jargon.
- `faster-whisper` on CPU with `large-v3-turbo`: 5.0 s, twice as slow as the same weights
  through OpenVINO.
- The NPU (Intel AI Boost): 23 s to compile, then fails on `initial_prompt`.

---

## The voice: text to speech

**Engine.** Piper, voice `ro_RO-liana-high`, phonemised by espeak-ng.

### Sentence by sentence, not the whole answer

The text is split at punctuation; the first sentence is synthesised alone, and each next one
is synthesised while the previous one plays. On a 69-word answer, measured with `curl`:
**3.0–3.3 s** of silence when the whole answer was requested at once, **0.80 s** sentence by
sentence. One sentence takes ~0.8 s to synthesise and 2–5 s to play, so preparation fits
inside listening and no seam is audible.

### While the model is still writing

Sentences used to go to synthesis only once the stream closed, so the last word sat on screen
for the whole writing time plus the synthesis of the first sentence. Now the buffer in
`pagina.js` (`hraneste`) cuts each sentence that is **certainly finished** — punctuation
followed by a space, or a newline — and pushes it at once onto a queue (`laRostit`) drained
by a single loop.

Measured through the real page, with the model replaced by a fake stream writing 25 words per
second:

| event | time |
|---|---|
| model starts writing | 17.12 s |
| first sentence sent to synthesis | 17.76 s |
| first sound ready | 19.65 s |
| model finishes writing | 20.32 s |

The voice starts **0.7 s before** the text is complete, instead of ~2 s after it.

A period at the very end of the buffer is not enough to cut: it may be the middle of a number,
or just where the model has got to so far — hence the wait for the following space. A short
sentence left at the end of a chunk is held for the next one, because `fraze()` merges short
sentences into their left neighbour, and that neighbour has not been written yet.

### Speed

A 68-character sentence synthesises in **0.47–0.74 s** and yields ~4.2 s of speech: six to
seven times faster than real time. In-process, the `high` voice gives the same figure, and a
`medium` voice is thirteen times faster than real time, if speed ever matters more than
quality.

> **Do not measure through `localhost` on Windows.** `localhost` resolves to `::1` first,
> where uvicorn is not listening, and only then to `127.0.0.1` — **2.7 false seconds added to
> every request**. The same synthesis: 3.3 s via `localhost`, 0.58 s via `127.0.0.1`. The
> browser is not affected because it keeps the connection open; a measuring tool is. All
> figures here were taken via `127.0.0.1`, with the connection kept alive.

### Markdown is not read aloud

espeak reads `**` literally: at the phonemiser, "`**Halucinații**`" comes out as
`ˌasteɾˌiskasteɾˈisk hˌalutʃinˈatiɪ ˌasteɾˌiskasteɾˈisk` — "asterisk asterisk" twice per
bold word, eight times in a four-point answer. `pentru_rostire()` strips `*`, `` ` ``, `#`,
`[`, `]` and list dashes, and ends every line with a period so that list items become
separate sentences rather than one long one. **The page still shows the Markdown**; only what
goes to Piper is cleaned.

### Programming jargon is rewritten before synthesis

The voice's dictionary covers everyday loanwords, not `branch` or `docker`. The `JARGON`
dictionary in `server/voce.py` respells them; every entry was checked at the phonemiser, not
guessed. The page still shows the correct spelling — the rewrite only touches the text sent
to Piper.

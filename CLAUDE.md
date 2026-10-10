# Mih.AI — instructions for Claude Code

A small local web app where you talk, by keyboard or by voice, with a language model prompted
from one person's own writing: *with* the person, as a thinking partner, and *as* the person, to
others, always saying it is the twin. The persona in `persona/` is fictional ("Ana Ionescu").
Code comments, the interface and the persona are in Romanian; keep new ones in Romanian.

## Map

| file | what it holds |
|---|---|
| `server/app.py` | the server: one page, the HTTP routes, the Host and Origin checks |
| `server/prompt.py` | the system prompt: `persona/prompt/` plus the evidence file |
| `server/model.py` | the streaming call to the Anthropic API and the spend counter |
| `server/transcriere.py` | speech to text, local |
| `server/voce.py`, `server/espeak_ctypes.py` | text to speech, local |
| `server/jurnal.py` | conversations, as plain text in `date/conversatii/` |
| `server/web/` | the page |
| `persona/prompt/`, `persona/probe/` | the prompt layers and the evidence file |
| `persona/banc-orb/` | the blind test bank |
| `scripts/consum-api.py` | this month's spend, from the log |

## Commands

```bat
python -m pip install -r requirements.txt
python -m uvicorn server.app:aplicatie --port 8100
python tests/ruleaza.py
```

## Rules

- **The blind bank never reaches the prompt.** `persona/banc-orb/` holds questions the person
  answers alone, to test the twin. `prompt.py` has no parameter through which the bank could
  enter; do not add one.
- **The twin does not invent a life.** What the person lived, decided or believes enters only
  with a source in the evidence files. The style is written from real texts, not from rules
  about them.
- **Every paid call is logged** with the token usage the API itself reported, even when the
  reply is interrupted. The tests recompute the spend two independent ways.
- **Silence never costs money.** Noise, coughs and Whisper's invented closing lines are stopped
  before anything reaches the paid model.
- **Local by design.** Speech runs on the machine; only the model call goes out. The server
  answers only on `localhost` / `127.0.0.1` and refuses any other `Host` or `Origin`.
- **No test calls the paid API.** A test whose input is missing (the real spend logs, the
  Whisper model) is **skipped with its reason**, never failed; keep it that way.

The design decisions for the ear and the voice are in [docs/DESIGN.md](docs/DESIGN.md).

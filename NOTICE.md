# Ce nu acoperă licența MIT

Licența MIT (`LICENSE`) acoperă codul și documentele din acest depozit. **Nu acoperă ce se
descarcă la instalare.** Nimic din lista de mai jos nu e redistribuit aici: fiecare
componentă se ia din sursa ei și își păstrează licența.

| componentă | de unde vine | licența |
|---|---|---|
| vocea `ro_RO-liana-high` | HuggingFace, `eduardem/piper-liana-romanian`, prin `scripts/adu-vocea.py` | **CC-BY-NC-4.0 — necomercială** |
| `piper-tts` 1.8.0 | PyPI | GPL-3.0-or-later |
| espeak-ng (biblioteca și datele) | proiectul `espeak-ng/espeak-ng` | GPL-3.0 |
| `espeakng-loader` 0.2.4 | PyPI | MIT |
| `OpenVINO/whisper-large-v3-turbo-int8-ov` | HuggingFace | MIT |

**Consecința practică:** codul îl poți folosi cum vrei, dar **cu vocea Liana, ansamblul nu se
folosește comercial.** Dacă vrei folosire comercială, înlocuiești vocea din
`server/voce.py` cu una care permite asta.

*Licențele sunt verificate pe 4 octombrie 2026, din model card-urile HuggingFace, din
metadatele PyPI și din API-ul GitHub. Nu țin loc de consultanță juridică.*

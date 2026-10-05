"""Apelul catre API-ul Anthropic, cu streaming, si contorul de consum.

DE CE SE SCRIE `usage` CA ATARE, copiat din raspuns:

  Fiindca orice alta cifra e o estimare. Regula proiectului: modelul nu
  produce fapte, le formuleaza — iar o cifra pe care codul n-a primit-o de la
  API e inventata. Numaratul de octeti sau de cuvinte da o cifra plauzibila si
  gresita, care apoi ajunge intr-o decizie despre bani.

DE CE SE SCRIE IN `finally`:

  Un raspuns intrerupt la mijloc (pagina inchisa, retea cazuta) a fost deja
  platit. Daca scrierea sta pe drumul fericit, exact apelurile scumpe —
  cele lungi, care apuca sa fie intrerupte — lipsesc din contor.

DESPRE CACHE: prefixul e stabil intre replici — nimic variabil in fata, fara
data, fara ceas — iar marcajul se cere o data, la nivel de cerere, si prinde tot
ce e stabil, prompt SI istoric. Motivul si cifra sint la `CACHE_TTL`, mai jos.
La inceput promptul era sub pragul de 1024 de tokeni al lui Sonnet si cache-ul nu
se activa deloc; cu fisa de stil si dosarul inauntru, pragul e trecut de
la sine si prefixul se citeste la 0,10x.

CHEIA vine din mediu (`ANTHROPIC_API_KEY`, la nivel de utilizator). Nu se scrie
pe disc, nu se citeste din alt program, nu se logheaza nicaieri.
"""

import json
import os
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path

from anthropic import AsyncAnthropic

from . import tipografie

RADACINA = Path(__file__).resolve().parent.parent
REGISTRU = RADACINA / "date" / "consum"

# Intr-un singur loc. Se schimba pe masuratoare, nu pe impresie.
MODEL = "claude-sonnet-5"

# 2000 era prea putin, si s-a vazut in folosire, nu pe hirtie: pe 30 august o
# replica a trecut la 45 de tokeni de plafon, iar doua au lovit plafonul si au
# iesit fara nicio litera de text — vezi `raspunde()`. Ridicarea NU costa nimic
# prin ea insasi: iesirea se plateste pe tokenii chiar generati, nu pe plafon.
# Ce poate costa sint replici mai lungi, si asta se masoara pe conversatii
# adevarate, cu `scripts/consum-api.py`.
# Ridicat de la 4000 pe 5 septembrie: plafonul e comun cu gindirea, iar ea
# maninca partea leului. Cu 4000, replicii vizibile ii ramineau vreo 1240 —
# adica exact felul de strimtoare care a golit doua replici pe 30 august.
MAX_TOKENI = 6000

# GINDIREA SE CERE ACUM EXPRES, si asta e o schimbare de pret, nu de stil.
# Masurat pe 5 septembrie din `date/consum/`: in august 2 apeluri din 73 aveau
# bloc `thinking`; in septembrie, 23 din 30. Media de iesire pe apel sarise de
# la 417 la 1636 de tokeni. Modelul gindea nechemat, se platea la pret de
# iesire (10 $/milion), se scadea din `max_tokens` si nu se vedea nicaieri —
# vreo 0,34 $ din cei 0,74 $ ai lunii, aruncati la gunoi.
#
# CUM SE COMANDA, la Sonnet 5: nu cu buget de tokeni. `{"type": "enabled",
# "budget_tokens": N}` — mecanismul modelelor vechi — e refuzat cu 400:
# «"thinking.type.enabled" is not supported for this model. Use
# "thinking.type.adaptive" and "output_config.effort"». Verificat pe
# 5 septembrie 2026, si de-aia gindea nechemat: `adaptive` e purtarea din
# fabrica, nu ceva ce ceruse cineva aici.
#
# Deci doua butoane, nu unul:
#   GANDIRE["display"] — "summarized" o trimite in raspuns (si de acolo in
#     pagina, pliata), "omitted" o ascunde dar o plateste mai departe.
#   EFORT — cit de mult gindeste: low, medium, high, xhigh, max. Nespus,
#     modelul alege singur, si alegerea lui e cea masurata mai sus.
# `low` e ales pe 5 septembrie si se schimba pe folosire, nu pe masuratoare: urca la `medium` daca raspunsurile
# incep sa sune subtiri in conversatii adevarate. Ce se stie deja: `medium` a
# injumatatit iesirea fata de `adaptive` nechemat — 2.052 -> 1.095 de tokeni pe
# intrebare — fara ca replica vizibila sa se scurteze. Cit taie `low` peste
# asta nu e masurat.
GANDIRE = {"type": "adaptive", "display": "summarized"}
EFORT = "low"

# CACHE-UL SE CERE ACUM LA NIVEL DE CERERE, nu pe blocul de sistem, si asta e o
# schimbare de pret, nu de mecanism. Marcajul de sus se pune singur pe ULTIMUL
# bloc care se poate tine in cache — adica pe capatul firului, nu pe capatul
# promptului — si se muta inainte cu fiecare replica. Deci in cache intra si
# conversatia, nu numai prefixul.
#
# DE CE, masurat pe 5 septembrie 2026 din `date/consum/`, pe cele 85 de replici
# de pagina din august si septembrie: 0,9359 $ in total, din care **0,200 $ (21%)
# pe istoricul de conversatie trimis la pret plin de intrare, la fiecare replica**.
# Firul creste — 235, 491, 961, 1.610, 2.240, 2.893 de tokeni in opt schimburi,
# pe 2 septembrie — si tot ce s-a spus pana atunci se replatea intreg de fiecare
# data. Cu marcajul de sus, aceiasi tokeni se scriu O DATA la 1,25x si pe urma se
# citesc la 0,10x.
#
# CE COSTA IN PLUS: pe o ratare de cache se rescrie si istoricul, cu 25% peste
# cat ar fi costat trimis simplu. Pe cifrele reale — 78 de nimeriri la 7 ratari —
# marginea nu se vede. Daca vreodata se inverseaza, se vede tot in `consum-api.py`.
#
# TTL-ul sta AICI, intr-un singur loc, si pleaca si in registru. Regula dupa care
# se alege intre 5m si 1h: ora e mai ieftina numai daca evita peste 0,65 scrieri pe fereastra de o ora. Pe 3
# septembrie iesea 0,5 — sub prag; pe 5 septembrie, cu tot ce se strinsese,
# 0,75 — peste. Diferenta dintre cele doua verdicte e 0,024 $ in doua saptamini,
# adica sub zgomotul unei conversatii. Ramine `5m` pina cind ritmul o rupe clar.
CACHE_TTL = "5m"

_client: AsyncAnthropic | None = None


def client() -> AsyncAnthropic:
    global _client
    if _client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY lipseste din mediu. Serverul nu porneste "
                "apeluri fara ea."
            )
        _client = AsyncAnthropic()
    return _client


def scrie_consumul(usage, unde: str = "pagina", stop: str | None = None,
                   blocuri: list[str] | None = None) -> None:
    """Un rand in `date/consum/AAAA-LL.jsonl`, in forma ceruta de consum-api.py.

    `stop` si `blocuri` sint in plus fata de bani, si sint acolo fiindca fara ele
    un apel oprit la plafon arata pe disc exact ca unul care a mers bine. Vezi
    `raspunde()`. `consum-api.py` citeste cimpurile pe nume si nu se sinchiseste
    de cele in plus.
    """
    acum = datetime.now().astimezone()
    rand = {
        "ora": acum.isoformat(timespec="seconds"),
        "model": MODEL,
        "unde": unde,
        "input": getattr(usage, "input_tokens", 0) or 0,
        "cache_write": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "output": getattr(usage, "output_tokens", 0) or 0,
        "cache_ttl": CACHE_TTL,
        "stop": stop,
        "blocuri": blocuri or [],
    }
    REGISTRU.mkdir(parents=True, exist_ok=True)
    fisier = REGISTRU / f"{acum.strftime('%Y-%m')}.jsonl"
    with fisier.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rand, ensure_ascii=False) + "\n")


async def raspunde(fir: list[dict], prompt_sistem: str, unde: str = "pagina",
                   raport: dict | None = None) -> AsyncIterator[tuple[str, str]]:
    """Perechi `(fel, bucata)`, pe masura ce vin. Consumul se scrie la capat, orice ar fi.

    `fel` e `"text"` (replica) sau `"gand"` (gindirea ceruta prin `GANDIRE`).
    Cele doua ies pe acelasi fir fiindca asa vin de la API, intretesute; cine
    le primeste alege ce arata si ce pastreaza. In jurnal si in `fir` intra
    numai textul: gindirea e proba de moment, nu istoric de conversatie.

    `fir` e istoricul conversatiei in forma ceruta de API: role/content.

    `raport` e al DOILEA canal de iesire, si exista dintr-un motiv masurat pe
    30 august: `text_stream` din SDK lasa sa treaca numai `text_delta`. Orice alt
    bloc pe care-l scrie modelul e aruncat in tacere — dar se plateste si se
    scade din `max_tokens`. In seara aia doua replici au iesit cu output 2000,
    adica exact plafonul, si zero text: apelul platit, raspuns niciunul, iar
    pagina a aratat o bula goala. Nimic pe disc nu spunea de ce, fiindca
    `stop_reason` si tipurile blocurilor nu se scriau nicaieri.

    Apelantul da un dicton gol si-l gaseste completat dupa ce fluxul s-a
    terminat: `stop` (de ce s-a oprit modelul), `blocuri` (ce tipuri de continut
    a scris), `text` (cate bucati de text au iesit), `gand` (cate de gindire).
    Nu costa niciun apel in plus — cifrele vin din raspunsul deja primit.
    """
    # Fara `cache_control` pe blocul de sistem: marcajul vine de sus, din
    # `cache_control` al cererii, si se aseaza singur pe ultimul bloc care se
    # poate tine in cache. Pus si aici, ar fi al doilea punct de taiere, fixat
    # inaintea firului — adica exact ce inlocuim.
    sistem = [{"type": "text", "text": prompt_sistem}]

    usage = None
    flux = None
    bucati = 0
    ganduri = 0
    # Ghilimelele se indreapta AICI, pe drumul spre pagina, ca sa ajunga la fel
    # si in bula, si in jurnal, si in ce se trimite la rostire. Motivul pentru
    # care regula nu sta in fisa de stil e in `server/tipografie.py`.
    ghilimele = tipografie.Ghilimele()
    try:
        async with client().messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENI,
            system=sistem,
            messages=fir,
            thinking=GANDIRE,
            output_config={"effort": EFORT},
            cache_control={"type": "ephemeral", "ttl": CACHE_TTL},
        ) as f:
            flux = f
            # Evenimentele brute, nu `text_stream`: ala lasa sa treaca numai
            # `text_delta` si inghite gindirea in tacere — exact defectul
            # masurat pe 30 august. Aici cele doua feluri ies pe acelasi fir,
            # etichetate, si apelantul decide ce face cu fiecare.
            async for ev in flux:
                if getattr(ev, "type", None) != "content_block_delta":
                    continue
                delta = ev.delta
                fel = getattr(delta, "type", None)
                if fel == "text_delta":
                    bucati += 1
                    yield "text", ghilimele.treci(delta.text)
                elif fel == "thinking_delta":
                    ganduri += 1
                    # Ghilimelele NU se indreapta pe gindire: fisa de stil e
                    # pentru ce citeste un om ca replica, iar gindirea e proba,
                    # aratata asa cum a iesit.
                    yield "gand", delta.thinking
            usage = (await flux.get_final_message()).usage
    finally:
        # Chiar si intrerupt, apelul a fost platit: se ia ce s-a strans pana
        # atunci din snapshot. Daca nici atat nu exista, apelul n-a plecat.
        instantaneu = None
        if flux is not None:
            try:
                instantaneu = flux.current_message_snapshot
            except Exception:
                instantaneu = None
        if usage is None and instantaneu is not None:
            usage = instantaneu.usage
        stop = getattr(instantaneu, "stop_reason", None)
        blocuri = sorted({b.type for b in getattr(instantaneu, "content", [])})
        # Raportul se completeaza numai daca apelul a plecat. Altfel (fara cheie,
        # de exemplu) apelantul ar adauga la eroarea adevarata a doua, inselatoare:
        # „modelul nu a scris nimic — s-a oprit la None".
        if raport is not None and flux is not None:
            raport.update(stop=stop, blocuri=blocuri, text=bucati,
                          gand=ganduri)
        if usage is not None:
            scrie_consumul(usage, unde, stop, blocuri)

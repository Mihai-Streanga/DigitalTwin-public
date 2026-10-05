"""Promptul de sistem al Twin-ului: `persona/prompt/` plus dosarul de probe.

DE CE E UN MODUL SEPARAT, cand e vorba de cateva citiri de fisier:

  Fiindca aici sta o taietura care nu se poate tine cu disciplina. Bancul de
  probe orb din `persona/banc-orb/` nu are voie sa ajunga niciodata in prompt —
  altfel proba nu mai e oarba si nu se mai poate evalua nimic.

  De-aia `compune()` NU primeste o cale ca argument. Sursele sunt constante in
  modul. Nu exista parametru prin care bancul sa ajunga in prompt din greseala,
  dintr-o refolosire grabita a functiei peste sase luni.

DE CE INTRA SI DOSARUL, desi e un artefact separat de prompt: fiindca
regula „contrazicerea din dosar" din `20-partener.md` cere dosarul ca sa aiba pe
ce musca. Probat pe 30 august, in prima conversatie reala: fara el, regula nu
devine inactiva, se aplica pe ce gaseste — pe premisele conversatiei — si Twin-ul
demonteaza formulari in loc de fond.

  Dosarul NU se copiaza in `persona/prompt/`. Sursa lui unica ramane
  `persona/probe/dosar.md`, de unde il iau toate drumurile care il folosesc. Doua
  copii ale aceluiasi text ar diverge in tacere.

DE CE `utf-8-sig`: fisierele scrise in terminalul autorului poarta BOM-ul pus de
PowerShell 5.1. Citite ca `utf-8` curat, primul caracter al promptului devine un
caracter invizibil — si asta a mai oprit un server din pornire.

CE NU PLEACA IN CLOUD: comentariile HTML. Antetul de versiune al promptului
e cerut de regula de versionare a promptului, ca divergenta fata de arhiva sa
se vada dintr-o privire. Dar e scris pentru cine deschide fisierul, nu pentru
model: pe 30 august, randul de versiune, care numea etapa de dezvoltare, i-a
spus Twin-ului in ce etapa e, si el a dedus din eticheta ca exista o etapa
anterioara pe care n-o vede. A inventat un document. Deci notele de
mecanism stau in `<!-- -->`, vizibile in fisier, taiate inainte de plecare.

ORDINEA e alfabetica dupa nume de fisier, de-aia se numeroteaza: `00-cadru.md`
(cine esti), `10-sine.md` (din ce faci parte), `20-partener.md` (cum te porti),
`30-stil.md` (cum suna) cand va exista. Dosarul intra dupa ele, iar exemplele
ultimele. Tot prefixul e stabil intre replici, deci se tine in cache.

DE CE INTRA SI EXEMPLELE, din 3 septembrie 2026: fiindca regula de la inceput
spune — „exemplele integrale bat regulile despre ele; un model imita mai
bine trei pagini adevarate decat zece reguli care le descriu" — si pana azi
modulul asta nu le lua. Nu era o taietura decisa undeva: pachetul de chat le
continea, iar aici lipseau, deci cele doua suprafete rulau cu
personalitati diferite. Bancul orb a rulat prin `compune()`, adica
prin suprafata fara exemple, si a dat fidelitatea sub prag cu zero mostre de voce
in prompt.

  Garantia despre banc nu slabeste: `EXEMPLE` e tot o cale constanta in modul, ca
  `SURSA` si `DOSAR`. Nu s-a adaugat niciun parametru prin care sa se aleaga ce
  intra. Ce e in `persona/probe/exemple/` intra tot, si acolo se pun numai texte
  scrise de autor.

  Ce NU are voie sa ajunga acolo: raspunsurile lui de la bancul orb. Sunt exact
  „el, raspunzand la o intrebare", deci ar fi materialul ideal — si tocmai de-aia
  fac nota de fidelitate autoreferentiala: masori cat de bine copiaza exemplul,
  pe aceleasi subiecte.
"""

import re
from pathlib import Path

RADACINA = Path(__file__).resolve().parent.parent
SURSA = RADACINA / "persona" / "prompt"
DOSAR = RADACINA / "persona" / "probe" / "dosar.md"
EXEMPLE = RADACINA / "persona" / "probe" / "exemple"

_COMENTARIU = re.compile(r"<!--.*?-->", re.DOTALL)
# Comentariul taiat lasa in urma randurile goale care il inconjurau. Se string la
# unul singur: gaura nu se vede in raspuns, dar se numara la fiecare replica.
_GOLURI = re.compile(r"\n{3,}")


def fisierele() -> list[Path]:
    """Fisierele care compun promptul, in ordinea in care intra."""
    lista = sorted(SURSA.glob("*.md")) if SURSA.is_dir() else []
    if DOSAR.exists():
        lista.append(DOSAR)
    if EXEMPLE.is_dir():
        lista += sorted(EXEMPLE.glob("*.md"))
    return lista


def compune() -> str:
    """Promptul de sistem, ca text.

    Fara argumente, deliberat: vezi antetul modulului.
    """
    bucati = []
    for f in fisierele():
        text = _COMENTARIU.sub("", f.read_text(encoding="utf-8-sig"))
        text = _GOLURI.sub("\n\n", text).strip()
        if text:
            bucati.append(text)
    return "\n\n---\n\n".join(bucati)


def versiunea() -> str:
    """Ce scrie in jurnal si in /api/stare, ca sa se vada cu ce a raspuns.

    Numele fisierelor plus numarul lor. Cand promptul creste, randul asta
    se schimba singur — nu e o cifra tinuta de mana, care ramane in urma.
    """
    nume = [f.stem for f in fisierele()]
    if not nume:
        return "prompt gol"
    return f"{len(nume)} fisiere: {', '.join(nume)}"


if __name__ == "__main__":
    # Consola Windows e cp1252 si crapa la prima litera cu sedila. Fara randul
    # asta, proba care cauta o scurgere in prompt "trece" fiindca iesirea a
    # murit inainte sa scrie ceva — adica unealta de observare sterge proba.
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    p = compune()
    print(f"--- {versiunea()} --- {len(p)} caractere ---")
    print(p)

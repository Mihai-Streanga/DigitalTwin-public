// Pagina Mih.AI.
//
// De ce fetch cu citire manuala a fluxului si nu EventSource: EventSource stie
// doar GET, iar mesajul pleaca prin POST. Deci SSE se despacheteaza aici, de
// mana — sunt douazeci de randuri si nu aduc nicio dependenta in pagina.

import { Ureche } from "/web/ureche.js";
import { Chip } from "/web/chip.js";

const fir = document.getElementById("fir");
const camp = document.getElementById("camp");
const formular = document.getElementById("formular");
const butonTrimite = document.getElementById("trimite");
const stare = document.getElementById("stare");

let idConversatie = null;
let ocupat = false;
// Rostire sosită cât Twin-ul răspundea: pleacă de îndată ce termină.
let asteaptaUrechea = false;

function replica(cine, clasa) {
  const div = document.createElement("div");
  div.className = "replica " + clasa;
  // Gindirea sta INAINTEA replicii, pliata, si ramine ascunsa pina cind chiar
  // vine ceva pe canalul ei — o sageata goala la fiecare bula ar fi zgomot.
  div.innerHTML = '<span class="cine"></span>'
    + '<details class="gand" hidden><summary>gândirea</summary>'
    + '<span class="gand-text"></span></details>'
    + '<span class="text"></span>';
  div.querySelector(".cine").textContent = cine;
  fir.appendChild(div);
  jos();
  return div.querySelector(".text");
}

function jos() { fir.scrollTop = fir.scrollHeight; }

async function arataStarea() {
  try {
    const s = await (await fetch("/api/stare")).json();
    // Urechea pe rezervă se scrie AICI, permanent, nu doar la pornire: o
    // transcriere de 2,5 s în loc de 0,3 arată ca un microfon stricat, iar o
    // notificare de acum zece minute nu mai e în dreptul ochilor.
    const rezerva = s.ureche && s.ureche_dispozitiv !== "GPU" ? " · urechea pe procesor" : "";
    // Rândurile de consum care n-au putut fi citite lipsesc din cifră: se spun,
    // altfel suma pare doar mică.
    const stricate = s.consum_randuri_stricate
      ? ` (+${s.consum_randuri_stricate} rânduri de consum necitite)` : "";
    stare.textContent = `${s.model} · ${s.conversatii} conversații · ${s.consum_luna_dolari} $ luna asta${stricate}${rezerva}`;
  } catch {
    stare.textContent = "serverul nu răspunde";
  }
}

async function conversatieNoua() {
  const r = await (await fetch("/api/conversatie-noua")).json();
  idConversatie = r.id;
  fir.innerHTML = "";
  camp.focus();
  arataStarea();
}

async function trimite(text) {
  if (ocupat || !text.trim() || !idConversatie) return;
  ocupat = true;
  butonTrimite.disabled = true;
  cum.gandeste = true;
  chipul();
  surd();

  replica("Ana", "mihai").textContent = text;
  const tinta = replica("Mih.AI", "twin");
  tinta.parentElement.classList.add("scrie");

  // VOCEA URMEAZA AUZUL. Cu microfonul deschis, răspunsul pleacă rostit singur;
  // cu el închis, scrii și citești și nimic nu vorbește neîntrebat. Butonul
  // „ascultă" de sub fiecare replică a ieșit din pagină: era un plasture, și
  // apărea abia după ce răspunsul era deja scris — adică prea târziu.
  //
  // SE HOTARASTE ACUM, nu la sfârșit, fiindcă prima frază pleacă la sinteză cât
  // modelul încă scrie. Cât vorbește el, urechea e oricum surdă.
  const rostesc = ureche.pornita;
  if (rostesc) incepeRostirea();

  // A VENIT VREO LITERA? Pe 30 august, de doua ori, apelul a plecat, a fost
  // platit si n-a intors nimic — iar pagina a ramas cu o bula goala si atat.
  // Autorul a crezut ca s-a pierdut dictarea si a redictat un paragraf de sase
  // randuri, degeaba. Serverul spune acum de ce (vezi `flux()` din `app.py`);
  // aici se repara partea care doare: textul lui NU se arunca.
  let aScris = false;

  try {
    const raspuns = await fetch("/api/mesaj", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: idConversatie, text }),
    });

    const cititor = raspuns.body.getReader();
    const decodor = new TextDecoder();
    let rest = "";

    while (true) {
      const { done, value } = await cititor.read();
      if (done) break;
      rest += decodor.decode(value, { stream: true });

      // Un eveniment SSE se termina la randul gol. Ce ramane dupa ultimul
      // rand gol e un eveniment taiat la mijloc: ramane in `rest`.
      const bucati = rest.split("\n\n");
      rest = bucati.pop();

      for (const bucata of bucati) {
        const tip = (bucata.match(/^event: (.*)$/m) || [])[1];
        const date = (bucata.match(/^data: (.*)$/m) || [])[1];
        if (!tip || !date) continue;
        const continut = JSON.parse(date);
        if (tip === "text") {
          aScris = true;
          tinta.textContent += continut.text;
          jos();
          if (rostesc) hraneste(continut.text);
        } else if (tip === "gand") {
          // Se arata, nu se rosteste: gindirea e de citit cu ochiul, iar
          // trimisa la difuzor ar dubla si timpul, si ce se aude.
          const g = tinta.parentElement.querySelector(".gand");
          g.hidden = false;
          g.querySelector(".gand-text").textContent += continut.text;
          jos();
        } else if (tip === "eroare") {
          tinta.parentElement.classList.add("eroare");
          tinta.textContent += "\n[" + continut.text + "]";
          // Ce s-a auzit pana aici s-a auzit; ce n-a plecat inca nu mai pleaca.
          if (rostesc) opresteRostirea();
        }
      }
    }
  } catch (e) {
    tinta.parentElement.classList.add("eroare");
    tinta.textContent += "\n[conexiunea s-a rupt: " + e.message + "]";
  } finally {
    tinta.parentElement.classList.remove("scrie");
    ocupat = false;
    butonTrimite.disabled = false;
    cum.gandeste = false;
    chipul();
    camp.focus();
    arataStarea();

    // Ce a ramas in tampon pleaca acum: ultima fraza a unui raspuns nu se
    // termina intotdeauna cu punct urmat de spatiu.
    if (rostesc && !tinta.parentElement.classList.contains("eroare")) {
      hraneste("", true);
      inchideRostirea();
    }
    // Daca nu s-a rostit nimic, urechea se redeschide de aici. Daca da, o
    // redeschide `opresteRostirea`, cand coada s-a golit de tot.
    if (!coadaMerge) asculta();

    if (!aScris) {
      // Textul se pune INAINTEA a ce s-a mai adunat in camp cat asteptai — daca
      // ai vorbit peste tacerea aia, ordinea rostirilor ramane ordinea in care
      // le-ai spus. Si NU se retrimite singur: un apel care tocmai a cazut ar
      // cadea la fel a doua oara, in bucla, pe banii tai. Apesi tu.
      camp.value = camp.value.trim() ? text + " " + camp.value : text;
      camp.dispatchEvent(new Event("input"));
      asteaptaUrechea = false;
    } else if (asteaptaUrechea && camp.value.trim()) {
      asteaptaUrechea = false;
      formular.requestSubmit();
    } else {
      asteaptaUrechea = false;
    }
  }
}

formular.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = camp.value;
  camp.value = "";
  camp.style.height = "auto";
  trimite(text);
});

camp.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    formular.requestSubmit();
  }
});

// Campul creste cu textul, pana la plafonul din CSS.
camp.addEventListener("input", () => {
  camp.style.height = "auto";
  camp.style.height = camp.scrollHeight + "px";
});

document.getElementById("noua").addEventListener("click", conversatieNoua);

// ── Urechea ──────────────────────────────────────────────────────────────────
//
// Pornește OPRITĂ, cu un clic PE CHIP, și rămâne pornită până o închizi.
// Motivul: **cât urechea e
// deschisă, orice se vorbește în cameră devine un apel plătit.** Un microfon
// deschis nu e o stare neutră, e o cheltuială.
//
// Butonul din bară a dispărut: comanda e chipul. Nu e mutare de estetică — cât
// urechea era un buton printre altele, starea ei se citea dintr-o etichetă de
// text, iar forma din mijlocul paginii nu spunea nimic.

const ureche = new Ureche({
  // SINGURUL LOC în care se reglează pragurile. Aceleași cifre există ca
  // implicite — încrederea în `ureche.js`, celelalte în `ureche-worklet.js` —
  // dar acolo sunt plasă pentru cazul în care nu vine nimic; comanda e aici. Cifrele sunt cele reglate pe măsurători în
  // JA.S.Mine, nu ghicite; se schimbă pe folosire.
  praguri: {
    pragTacere: 2.0,     // atâta tăcere înseamnă „am terminat de vorbit"
    pragVolum: 0.012,    // sub atât e zgomot de cameră
    minimVorbire: 0.15,  // o ușă sau o tastă trec pragul, dar nu durează
    // Cât trebuie să fi trecut de `pragVolum` ca rostirea să plece la
    // transcriere. A stat la 0,4 cât ăsta era singurul filtru; de pe 25
    // august judecă Silero VAD, pe server, care separă vorbirea de zgomot
    // fără să se uite la amplitudine. Prag mare aici ar tăia exact ce VAD-ul
    // știe să lase să treacă: „da", „nu", „bine".
    incredere: 0.15,
    maximRostire: 60.0,
    preRoll: 0.25,       // ce se ia dinaintea primei silabe auzite
  },
  laStare: (s) => {
    // Cuvintele urechii („ascult", „te aud") au plecat de aici: singurul loc în
    // care o stare primește nume și formă e tabelul `STARI` din `chip.js`.
    cum.aude = s === "vorbesti";
    cum.transcriu = s === "transcriu";
    if (s.startsWith("eroare")) greseala(s.replace(/^eroare:\s*/, ""));
    else chipul();
  },
  // Vine de ~10 ori pe secundă, din worklet. Forma pulsează pe ce se aude.
  laVolum: (v) => chip.nivel(v / VARF_MICROFON),
  laText: (text) => {
    camp.value = camp.value ? camp.value + " " + text : text;
    if (ocupat) {
      // Ai vorbit peste răspunsul lui. Textul se adună în câmp și pleacă
      // singur când termină — altfel ar rămâne blocat acolo până vorbești
      // din nou, ceea ce arată exact ca o rostire pierdută.
      asteaptaUrechea = true;
    } else {
      formular.requestSubmit();
    }
  },
});

let sePregateste = false; // cât ține pregătirea, al doilea clic nu face nimic

async function comutaUrechea() {
  if (sePregateste) return;
  if (ureche.pornita) {
    ureche.opreste();
    opresteRostirea();
    chipul();
    return;
  }
  sePregateste = true;
  cum.eroare = false;
  cuvant.textContent = "pregătesc urechea…";
  try {
    // Compilarea pe iGPU ține 3,4–4,7 s, o singură dată pe pornire de server.
    const r = await fetch("/api/ureche", { method: "POST" });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.eroare || "motorul nu a pornit");
    await ureche.porneste();
    chipul();
    // Placa n-a fost, motorul a căzut pe procesor. Se spune o dată, în fir,
    // fiindcă altfel prima rostire pare pierdută; starea rămâne apoi în bară.
    if (d.dispozitiv && d.dispozitiv !== "GPU") {
      replica("urechea", "twin").textContent =
        "Placa grafică n-a fost liberă, așa că transcriu pe procesor: aceleași cuvinte, " +
        "dar ~2,5 secunde în loc de ~0,3. Repornește serverul ca să încerce placa din nou.";
    }
    arataStarea();
  } catch (e) {
    greseala(e.message);
  } finally {
    sePregateste = false;
  }
}

document.getElementById("chip").addEventListener("click", comutaUrechea);

// ── Chipul ───────────────────────────────────────────────────────────────────
//
// SINGURUL loc în care starea programului devine formă. `chip.stare()` nu se
// cheamă de nicăieri altundeva: dacă s-ar putea pune din două locuri, cele două
// s-ar bate exact când pagina e cel mai greu de citit — și așa a ajuns starea
// urechii să fie scrisă în trei fișiere.

// Fundalul se dă explicit: chipul stinge dârele vopsind peste ele cu culoarea
// de sub el, iar scena e mai adâncă decât pagina (`--scena` în `stil.css`). Cu
// culoarea greșită, urma fiecărei particule rămâne un dreptunghi mai deschis.
const chip = new Chip(document.getElementById("panza"), { fundal: "#08060d" }).porneste();
const cuvant = document.getElementById("cuvant");

// Cât de tare trebuie vorbit ca forma să pulseze la maximum. RMS-ul unei vorbiri
// normale la microfonul de birou stă între 0,02 și 0,15. Cifra se schimbă pe
// folosire, nu pe teorie — și e a microfonului ăstuia, nu a microfoanelor.
const VARF_MICROFON = 0.18;
const VARF_REDARE = 0.30;

const cum = {
  eroare: false,
  vorbeste: false,   // Mih.AI citește cu voce tare
  gandeste: false,   // modelul scrie răspunsul
  transcriu: false,  // Whisper lucrează
  aude: false,       // microfonul a prins o rostire în curs
};
let cuvantRau = "";

function chipul() {
  // Ordinea E contractul: ce se întâmplă acum bate ce s-a întâmplat înainte.
  const s = cum.eroare ? "rau"
    : cum.vorbeste ? "vorbeste"
    : cum.gandeste ? "gandeste"
    : cum.transcriu ? "transcriu"
    : cum.aude ? "aude"
    : ureche.pornita ? "ascult"
    : "repaus";
  chip.stare(s);
  cuvant.textContent = s === "rau" && cuvantRau ? cuvantRau : chip.cuvant;
  cuvant.classList.toggle("rau", s === "rau");
}

function greseala(text) {
  cuvantRau = text;
  cum.eroare = true;
  chipul();
}

// CAT LUCREAZA EL, URECHEA NU AUDE. Nu doar cât vorbește: și cât gândește, și
// cât se sintetizează rostirea. Fereastra aia e de câteva secunde bune (69 de
// cuvinte = 4,9 s de sinteză, măsurat), iar o tuse prinsă în ea devine mesaj
// nou și taie răspunsul la mijloc. S-a întâmplat, pe 25 august, la 09:22:54.
//
// Consecința, asumată: nu-l poți întrerupe vorbind. Îl întrerupi cu un clic pe
// chip, care închide urechea și taie rostirea.
function surd() {
  if (ureche.pornita) ureche.surd(true);
}

function asculta() {
  if (ureche.pornita && !cum.gandeste && !cum.vorbeste) ureche.surd(false);
}

// ── mih.AI, vocea care iese ──────────────────────────────────────────────────
//
// Perechea e `mihai` (ce intră, prin microfon) și `mih.AI` (ce iese, prin
// difuzor): pe canalul de intrare vorbește omul, pe cel de ieșire vorbește
// programul. În fir, replicile poartă deja exact numele astea.
//
// Twin-ul citește cu voce tare, local, pe procesor. NU COSTA NICIUN TOKEN, ca
// și urechea — Piper rulează pe mașină.
//
// CAT VORBESTE EL, URECHEA STA PE PAUZA. Altfel microfonul aude difuzorul,
// transcrie ce tocmai a spus Twin-ul și i-l trimite înapoi ca întrebare. Bucla
// aia nu se oprește singură.

// Un SINGUR element de sunet pentru toata sesiunea. Un `MediaElementSource` se
// poate lega de un element o singura data in viata lui, iar rostirea pe fraze ar
// fi cerut cate unul la fiecare propozitie.
const difuzor = new Audio();
let rostireaMea = 0;   // numarul rostirii curente; una veche nu invie peste una noua
let ceasRedare = null;

// Amplitudinea redarii, ca forma umana sa pulseze pe ce se aude, nu pe un
// cronometru. Un chip care se misca pe cronometru e decor; unul care se misca pe
// semnal e instrument de citit starea.
let ctxRedare = null;
let analizor = null;
let unde = null;

function legDifuzorul() {
  if (analizor) return;
  ctxRedare = new AudioContext();
  analizor = ctxRedare.createAnalyser();
  analizor.fftSize = 512;
  unde = new Uint8Array(analizor.fftSize);
  ctxRedare.createMediaElementSource(difuzor).connect(analizor);
  analizor.connect(ctxRedare.destination);
}

function urmaresteRedarea() {
  clearInterval(ceasRedare);
  // Aceeasi zecime de secunda ca la microfon: o singura cadenta in toata pagina.
  ceasRedare = setInterval(() => {
    if (!analizor) return;
    analizor.getByteTimeDomainData(unde);
    let suma = 0;
    for (let i = 0; i < unde.length; i++) {
      const x = (unde[i] - 128) / 128;
      suma += x * x;
    }
    chip.nivel(Math.sqrt(suma / unde.length) / VARF_REDARE);
  }, 100);
}

// FRAZELE. Sinteza intregului raspuns se cere odata si costa: masurat pe 25
// august, 69 de cuvinte au cerut 4,89 s, si atata a stat pagina muta dupa ce
// textul era deja scris pe ecran. Pe fraze, prima pleaca dupa o jumatate de
// secunda, iar urmatoarea se pregateste cat se aude cea dinainte.
//
// Taietura e pe semnul de punctuatie urmat de spatiu, si pe randul nou —
// punctele unei liste sunt unitati de rostit, nu o singura fraza lunga. Frazele foarte scurte se
// lipesc de urmatoarea: „Da." trimis singur la sinteza costa mai mult in dus-intors
// decat dureaza rostit.
function fraze(text) {
  const brute = text.split(/(?<=[.!?…:;])[ ]+|\n+/)
  const iesire = [];
  for (const b of brute) {
    const f = b.trim();
    if (!f) continue;
    if (iesire.length && iesire[iesire.length - 1].length < 24) iesire[iesire.length - 1] += " " + f;
    else iesire.push(f);
  }
  return iesire;
}

async function adu(text) {
  const r = await fetch("/api/vorbeste", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    throw new Error(d.eroare || "vocea n-a raspuns");
  }
  return URL.createObjectURL(await r.blob());
}

// Cine asteapta sfarsitul unei fraze trebuie trezit si cand fraza e TAIATA, nu
// doar cand se termina de la sine. Altfel bucla ramane agatata pe o promisiune
// care nu se implineste niciodata, si cu ea raman si adresele nedesfacute.
let taieCantecul = null;

function canta(adresa) {
  return new Promise((gata, rau) => {
    taieCantecul = gata;
    difuzor.src = adresa;
    difuzor.onended = gata;
    difuzor.onerror = () => rau(new Error("redarea a eșuat"));
    difuzor.play().catch(rau);
  });
}

function opresteRostirea() {
  rostireaMea++;
  // Coada moare odata cu rostirea. Bucla care doarme pe ea trebuie TREZITA,
  // altfel ramane agatata pe o promisiune care nu se mai implineste niciodata —
  // aceeasi capcana ca la fraza taiata la mijloc, cu `taieCantecul`.
  laRostit.length = 0;
  deRostit = "";
  coadaInchisa = true;
  trezeste();
  difuzor.onended = difuzor.onerror = null;
  difuzor.pause();
  if (taieCantecul) {
    const trezeste = taieCantecul;
    taieCantecul = null;
    trezeste();
  }
  clearInterval(ceasRedare);
  ceasRedare = null;
  chip.nivel(0);
  if (cum.vorbeste) {
    cum.vorbeste = false;
    chipul();
  }
  asculta();
}

// ── Coada de rostit ──────────────────────────────────────────────────────────
//
// DE CE O COADA SI NU O FUNCTIE PESTE TOT TEXTUL: fraza pleaca la sinteza in
// timp ce modelul inca scrie. Producatorul — fluxul SSE — si consumatorul —
// difuzorul — merg in ritmuri complet diferite si nu se pot astepta unul pe
// altul.
//
// CE ERA INAINTE, si de ce s-a schimbat: vocea pornea in `finally`, adica dupa
// ce TOT raspunsul era scris. La un raspuns de trei-patru fraze asta inseamna
// ca ultimul cuvant statea scris pe ecran secunde bune inainte sa se auda
// primul. Acum se asteapta doar prima propozitie.
//
// Ce NU s-a schimbat: doua fraze nu se aud niciodata odata. Coada e strict
// serial, si `rostireaMea` taie in continuare o rostire veche peste una noua.

const laRostit = [];       // fraze incheiate, care asteapta sinteza
let coadaMerge = false;    // o SINGURA bucla goleste coada
let coadaInchisa = true;   // fluxul s-a terminat: dupa ultima fraza, gata
let trezesteCoada = null;  // bucla doarme cand coada e goala si fluxul deschis

function trezeste() {
  if (!trezesteCoada) return;
  const t = trezesteCoada;
  trezesteCoada = null;
  t();
}

function incepeRostirea() {
  opresteRostirea();       // taie ce se auzea, si goleste coada veche
  coadaInchisa = false;
  return rostireaMea;
}

function pentruRostit(fraza) {
  if (coadaInchisa) return;
  laRostit.push(fraza);
  trezeste();
  if (!coadaMerge) golesteCoada(rostireaMea);
}

function inchideRostirea() {
  coadaInchisa = true;
  trezeste();
}

// Urmatoarea fraza, sau `null` cand fluxul s-a inchis si n-a mai ramas nimic.
// Cat fluxul e deschis si coada goala, bucla doarme — nu invarte procesorul.
function urmatoareaFraza() {
  if (laRostit.length) return Promise.resolve(laRostit.shift());
  if (coadaInchisa) return Promise.resolve(null);
  return new Promise((t) => (trezesteCoada = t)).then(urmatoareaFraza);
}

async function golesteCoada(eu) {
  coadaMerge = true;
  const adrese = [];
  try {
    legDifuzorul();
    if (ctxRedare.state === "suspended") await ctxRedare.resume();
    if (eu !== rostireaMea) return;
    surd();
    cum.vorbeste = true;
    chipul();
    urmaresteRedarea();

    // Una se aude, urmatoarea se sintetizeaza. De-aia se cere INAINTE de a
    // astepta sfarsitul celei care canta.
    let inSinteza = urmatoareaFraza().then((f) => (f ? adu(f) : null));
    while (true) {
      const adresa = await inSinteza;
      if (eu !== rostireaMea) return;
      if (!adresa) break;
      adrese.push(adresa);
      const canteceul = canta(adresa);
      inSinteza = urmatoareaFraza().then((f) => (f ? adu(f) : null));
      await canteceul;
      if (eu !== rostireaMea) return;
    }
  } catch (e) {
    if (eu === rostireaMea) greseala("vocea: " + e.message);
  } finally {
    coadaMerge = false;
    for (const a of adrese) URL.revokeObjectURL(a);
    if (eu === rostireaMea) opresteRostirea();
  }
}

// ── Ce se taie in fraze, si cand ─────────────────────────────────────────────
//
// Fluxul vine pe bucati de cateva litere, deci textul se aduna intr-un tampon
// si pleaca la rostit numai ce e SIGUR incheiat: semn de punctuatie urmat de
// spatiu, sau rand nou. Un punct la capatul tamponului nu e destul — poate fi
// mijlocul unui numar, sau doar bucata pana la care a ajuns modelul.
let deRostit = "";  // ce a venit din flux si n-a plecat inca la sinteza

function hraneste(bucata, ultima = false) {
  deRostit += bucata;
  let gata;
  if (ultima) {
    gata = deRostit;
    deRostit = "";
  } else {
    const m = deRostit.match(/^[\s\S]*(?:[.!?…:;][ ]|\n)/);
    if (!m) return;
    gata = m[0];
    deRostit = deRostit.slice(gata.length);
  }
  const bucati = fraze(gata);
  // O fraza scurta ramasa la coada se tine pentru urmatoarea transa: `fraze`
  // lipeste scurtele de vecina din stanga, dar aici vecina n-a venit inca.
  if (!ultima && bucati.length && bucati[bucati.length - 1].length < 24) {
    deRostit = bucati.pop() + " " + deRostit;
  }
  for (const f of bucati) pentruRostit(f);
}

conversatieNoua();

// `?ureche=auto` pornește urechea fără clic. Browserul cere permisiunea de
// microfon o dată per adresă; după ce ai dat-o, adresa asta te ascultă din
// clipa în care se deschide. E și felul în care se probează lanțul audio cu
// microfon fals, fără mână de om.
if (new URLSearchParams(location.search).get("ureche") === "auto") {
  comutaUrechea();
}

// ── ESC: fereastra în bară ───────────────────────────────────────────────────
//
// Fereastra pornește pe tot ecranul, fără bară de titlu (`porneste.vbs`), deci
// n-are butonul de minimizare la îndemână. ESC o bagă în bară.
//
// DE CE PRIN SERVER: o pagină nu se poate minimiza singură — `window.minimize`
// nu există și nici nu va exista, e o poartă închisă din motive de securitate.
// Serverul e local și e al nostru, deci face el gestul, cu `user32`. Vezi
// `/api/fereastra/ascunde` în `server/app.py`.
//
// ESC nu golește câmpul și nu oprește răspunsul în curs: fereastra pleacă în
// bară cu tot cu ce scria, și revine întreagă la un clic.
addEventListener("keydown", (e) => {
  if (e.key !== "Escape" || e.repeat) return;
  e.preventDefault();
  fetch("/api/fereastra/ascunde", { method: "POST" }).catch(() => {});
});

// ── Dictarea rămâne deasupra ─────────────────────────────────────────────────
//
// Iris, unealta de dictare a autorului, e o ferestruică „mereu deasupra". Când
// dai clic în caseta de scris, pagina ia focus și Iris ajunge dedesubt — atunci
// n-ai pe ce apăsa ca să transmiți ce ai dictat.
//
// Pagina nu poate ridica singură fereastra altui program, deci cere serverului,
// care o urcă la loc FĂRĂ să-i dea focus: cursorul rămâne în casetă.
//
// Se cheamă la focus, nu la fiecare tastă, și cu un plafon de o secundă: e un
// apel local și gratuit, dar tot n-are rost de zece ori pe secundă.
let ultimaRidicare = 0;
function dictareaDeasupra() {
  const acum = Date.now();
  if (acum - ultimaRidicare < 1000) return;
  ultimaRidicare = acum;
  fetch("/api/fereastra/dictarea-deasupra", { method: "POST" }).catch(() => {});
}

addEventListener("focus", dictareaDeasupra);
camp.addEventListener("focus", dictareaDeasupra);
camp.addEventListener("click", dictareaDeasupra);
dictareaDeasupra();

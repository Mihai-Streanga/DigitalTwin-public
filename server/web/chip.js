// Chipul lui Mih.AI — contractul de stări și norul de particule.
//
// DE CE CONTRACTUL SE SCRIE INAINTEA DESENULUI: cele șapte stări existau deja
// pe disc, împrăștiate în trei fișiere — `pagina.js` ținea „ocupat", `ureche.js`
// ținea „ascult / te aud / transcriu", worklet-ul ținea începutul rostirii —
// fiecare cu cuvintele ei. Tabelul `STARI` de mai jos e SINGURUL loc în care o
// stare primește formă, culoare, puls și cuvânt. O stare nouă se adaugă aici.
// Dacă formele s-ar face primele, fiecare stare nouă s-ar lipi unde apucă,
// exact cum s-a lipit butonul „ascultă" sub replică.
//
// DE CE PARTICULE SI NU MORFING DE CAI SVG: morfingul cere același număr de
// puncte, în aceeași ordine, în ambele siluete — muncă de mână care se rupe la
// prima retușare a desenului. Norul mută aceleași ~3.200 de puncte între două
// mulțimi de ținte eșantionate din desen, deci transformarea „ca în anime" iese
// din tehnică, nu se animează cadru cu cadru. Siluetele pot fi grosolane:
// norul face impresia.
//
// E ACEEASI PISICA. SE SCHIMBA CULOAREA, NU FORMA.
//
// Locul interlocutorului — `gandeste` și `vorbeste` — a înghițit pe rând patru
// desene de om (bust, siluetă, contur: toate refuzate la vedere), o pisică
// agățată de tavan, o fotografie și o vrăbiuță. Fiecare încerca să spună „aici
// vorbește altcineva" printr-o FORMA nouă, și fiecare a costat un desen.
//
// Regula pe care a numit-o autorul pe 31 august, după ce a văzut vrăbiuța, e că
// nu se distinge prin formă, ci prin COD DE CULOARE — un principiu pe care-l
// folosește deja în celelalte programe ale lui. Deci: aceeași pisică peste tot,
// violetul rece cât ascultă și așteaptă, roșul lui Iris (`--iris`, `#ff3b5c`,
// din `stil.css`) cât gândește și vorbește Mih.AI. Nimic de desenat, nimic de
// refuzat: culoarea nu are proporții pe care să le greșești.
//
// CE DEOSEBESTE ROSUL DE VORBIT DE ROSUL DE EROARE, fiindcă e același roșu:
// FORMA. `rau` n-are siluetă deloc — e norul destrămat, fără ochi, cu agitația
// la 0,75 și cu vorba „ceva e rău" sub el. O pisică roșie liniștită și un nor
// roșu care tremură nu se confundă. Culoarea spune CINE, forma spune CE.
//
// FISIERUL ASTA NU STIE DE SERVER si nu cheamă nimic.
//
// CE S-A SCOS PE 5 SEPTEMBRIE 2026, la audit: poza și mașinăria ei (`POZA`,
// `foto`, `fotografia()`), pisica agățată (`pisicaAtarna`, `ochiiAtarna`, forma
// `atarna`) și scena din jurul ei (`aura`, `tavan`, `podea`, `scena`), plus
// `chip-foto.png` — 859 KB, cel mai mare fișier din depozit după modele. Nicio
// stare din `STARI` nu le mai cerea de pe 31 august, când codul de culoare a
// luat locul formelor, deci se desenau degeaba sau nu se desenau deloc. Git le
// ține: se scot ca să nu mai fie citite, nu ca să dispară.

// ── Contractul ───────────────────────────────────────────────────────────────
//
// forma     — din ce siluetă își ia norul țintele: `pisica` sau `nor`
//             (`nor` = fără siluetă, particulele orbitează; e forma stărilor în
//             care programul nu e nici ascultător, nici vorbitor).
// cald      — 0 corp rece (violetul adânc), 1 viu aprins (magenta).
// puls      — cât respiră norul de la sine, când nu vine niciun semnal.
// agitatie  — cât de tare tremură particulele în jurul țintei.
// peSemnal  — dacă `true`, forma urmează amplitudinea reală dată cu `nivel()`:
//             volumul microfonului la intrare, al redării la ieșire.
// iris      — dacă `true`, accentul viu al norului nu mai e magenta, ci roșul
//             irisului. E CODUL DE CULOARE al interlocutorului, nu un semnal de
//             eroare: îl poartă `gandeste`, `vorbeste` și `rau`. Ce le deosebește
//             între ele e forma, nu culoarea — vezi capul fișierului.
export const STARI = {
  repaus: {
    forma: "pisica", cuvant: "", cald: 0.28, puls: 0.30, agitatie: 0.12,
  },
  ascult: {
    forma: "pisica", cuvant: "ascult", cald: 0.50, puls: 0.55, agitatie: 0.22,
  },
  aude: {
    forma: "pisica", cuvant: "te aud", cald: 0.65, puls: 0.9, agitatie: 0.40,
    peSemnal: true,
  },
  transcriu: {
    forma: "nor", cuvant: "transcriu…", cald: 0.45, puls: 0.5, agitatie: 0.55,
  },
  // Cele două stări ale interlocutorului. NU SE DEOSEBESC PRIN FORMA, ci prin
  // culoare: e aceeași pisică, în roșul irisului. Vezi capul fișierului.
  //
  // `cald` la gândit e 1,0, nu 0,25 cât era cu poza, și cifra nu e o alegere de
  // gust: fără semnal, `deseneaza()` înmulțește `cald` cu 0,6, deci 1,0 ajunge
  // 0,60 pe ecran — atât se poate obține când nu vorbește nimeni. La 0,55 ieșea
  // 0,33, adică o pisică violetă care nu se deosebea de cea în repaus (0,168).
  // Cât ținea poza, cele două se deosebeau prin ea; fără ea, deosebirea trebuie
  // să fie în cifră. Gânditul e roșu stins fiindcă e liniștit, nu fiindcă
  // așa s-a nimerit; vorbitul urcă singur la roșu plin, pe semnal.
  gandeste: {
    forma: "pisica", iris: true, cuvant: "gândesc…", cald: 1.0, puls: 0.45,
    agitatie: 0.24,
  },
  vorbeste: {
    forma: "pisica", iris: true, cuvant: "vorbesc", cald: 0.9, puls: 0.55,
    agitatie: 0.15, peSemnal: true,
  },
  rau: {
    forma: "nor", cuvant: "ceva e rău", cald: 1.0, puls: 0.25, agitatie: 0.75,
    iris: true,
  },
};

// Culorile vin din referințele aduse de autor pe 25 august: pisici și siluete
// desenate în neon violet-magenta pe negru, cu cyan ca al doilea accent. Au
// înlocuit chihlimbarul punții JA.S.Mine, care era o culoare împrumutată de la
// alt program. Ce s-a păstrat e ROLUL fiecărei culori, nu nuanța: structura
// rece, accentul viu, irisul pentru celălalt glas. (Irisul a fost la început
// numai culoarea a ce e rupt; din 31 august e codul de culoare al
// interlocutorului, iar eroarea se deosebește prin formă — vezi capul.)
const RECE = [0x5b, 0x21, 0xb6];          // violet adânc, particulele „grele"
const RECE_DESCHIS = [0x22, 0xd3, 0xee];  // cyan, particulele ușoare
const LAMPA = [0xa8, 0x55, 0xf7];         // violet
const AUR = [0xf0, 0x9c, 0xff];           // magenta deschis, miezul aprins
const IRIS = [0xff, 0x3b, 0x5c];          // roșul lui Iris; vezi `--iris` din `stil.css`
const OCHI = [0xff, 0xe8, 0xff];          // ochii pisicii: aproape alb, vezi `deseneaza()`

// 2000 de particule erau destule cât chipul stătea într-un pătrat de 34% din
// pagină. Pe scena de jumătate de ecran aceeași mulțime se întinde pe de patru
// ori mai mulți pixeli și silueta iese ciuruită. 3200 e cifra la care norul
// redevine corp.
const NUMAR = 3200;
const OCHI_PARTE = 0.085; // ce felie din particule se duce în ochi când e pisică
const GALETI = 16; // câte nuanțe se desenează; vezi `deseneaza()`
const TAU = Math.PI * 2;

const amesteca = (a, b, t) => [
  a[0] + (b[0] - a[0]) * t,
  a[1] + (b[1] - a[1]) * t,
  a[2] + (b[2] - a[2]) * t,
];

export class Chip {
  constructor(panza, { fundal = "#0e0d0b", numar = NUMAR } = {}) {
    this.panza = panza;
    this.c = panza.getContext("2d");
    this.bg = [1, 3, 5].map((i) => parseInt(fundal.slice(i, i + 2), 16));
    this.numar = numar;

    this.acum = "repaus";
    this.def = STARI.repaus;
    this.semnal = 0;      // ce vine de afară, 0..1
    this.nivelNeted = 0;  // ce se desenează, cu atac rapid și cădere lentă
    this.t = 0;
    this.cadru = null;
    this.ultima = 0;

    // Siluetele se eșantionează O SINGURA DATA, în coordonate normalizate. La
    // redimensionare se rescalează punctele, nu se desenează silueta din nou.
    //
    // ULTIMELE `nOchi` puncte nu vin din corp, ci din partea aprinsă. La pisică
    // aia e ochiul. În toate referințele aduse de
    // autor norul are UN loc mai aprins decât restul — iar un nor uniform nu are
    // cum să-l scoată singur, fiindcă densitatea e aceeași peste tot. La `nor`
    // aceleași particule își iau ținta și culoarea ca toate celelalte.
    this.nOchi = Math.round(this.numar * OCHI_PARTE);
    this.brut = {
      pisica: esantion(pisica, this.numar - this.nOchi).concat(
        esantion(ochii, this.nOchi)),
    };
    this.tinte = { pisica: [] };

    this.puls = 1;   // ultimul puls calculat în `pas()`

    this.masoara();
    this.naste();
    this._laMasura = () => { this.masoara(); this.rescaleaza(); };
    addEventListener("resize", this._laMasura);
  }

  // ── Ce se cheamă din pagină ────────────────────────────────────────────────

  stare(nume) {
    if (!STARI[nume]) { console.warn("[chip] stare necunoscută:", nume); nume = "rau"; }
    this.acum = nume;
    this.def = STARI[nume];
    return this;
  }

  /** Amplitudinea reală, 0..1. Se dă plafonat la ~10 pe secundă: mai des nu se
   *  vede, dar costă cadre. Netezirea o face chipul, nu apelantul. */
  nivel(v) {
    this.semnal = Math.max(0, Math.min(1, v || 0));
  }

  get cuvant() { return this.def.cuvant; }

  porneste() {
    if (this.cadru) return this;
    this.ultima = performance.now();
    const bucla = (acum) => {
      const dt = Math.max(0.4, Math.min(2.5, (acum - this.ultima) / 16.7));
      this.ultima = acum;
      this.pas(dt);
      this.deseneaza();
      this.cadru = requestAnimationFrame(bucla);
    };
    this.cadru = requestAnimationFrame(bucla);
    return this;
  }

  opreste() {
    if (this.cadru) cancelAnimationFrame(this.cadru);
    this.cadru = null;
    return this;
  }

  distruge() {
    this.opreste();
    removeEventListener("resize", this._laMasura);
  }

  // ── Măsura pânzei ──────────────────────────────────────────────────────────

  masoara() {
    const dpr = Math.min(devicePixelRatio || 1, 2);
    this.l = Math.max(1, Math.round(this.panza.clientWidth * dpr));
    this.i = Math.max(1, Math.round(this.panza.clientHeight * dpr));
    this.panza.width = this.l;
    this.panza.height = this.i;
    this.dpr = dpr;

    // RAZA CRESTE CU SCENA. Cât chipul stătea într-un pătrat de vreo 420 px,
    // particule de 1–2 px făceau un corp. Pe jumătate de ecran, aceleași
    // particule sînt praf împrăștiat: forma se ghicește, nu se vede. Plafonul
    // de 2,4 e pus fiindcă peste el norul devine o supă de bile.
    this.scaraRaza = Math.min(2.4, Math.max(1, Math.min(this.l, this.i) / 420));
    this.rescaleaza();
  }

  rescaleaza() {
    const latura = this.latura = Math.min(this.l, this.i) * 0.88;
    const ox = this.ox = (this.l - latura) / 2;
    const oy = this.oy = (this.i - latura) / 2;

    this.tinte.pisica = this.brut.pisica.map(
      ([x, y]) => [ox + x * latura, oy + y * latura]);
  }

  naste() {
    const cx = this.l / 2, cy = this.i / 2;
    this.particule = [];
    this.ochii = [];
    this.galeti = Array.from({ length: GALETI }, () => []);
    for (let i = 0; i < this.numar; i++) {
      const p = {
        x: cx + (Math.random() - 0.5) * this.l * 0.5,
        y: cy + (Math.random() - 0.5) * this.i * 0.5,
        vx: 0, vy: 0,
        r: Math.random(),                       // cât de „greu" e: leagă viteza, raza orbitei și nuanța
        unghi: Math.random() * TAU,
        sens: Math.random() < 0.5 ? -1 : 1,
        raza: (0.8 + Math.random() * 1.5) * this.dpr,
      };
      this.particule.push(p);
      if (i >= this.numar - this.nOchi) {
        p.ochi = true;
        p.raza *= 1.35;
        this.ochii.push(p);
      } else {
        this.galeti[Math.floor(p.r * GALETI) % GALETI].push(p);
      }
    }
  }

  // ── Mișcarea ───────────────────────────────────────────────────────────────

  pas(dt) {
    const d = this.def;
    this.t += 0.016 * dt;

    // Semnalul urcă repede și coboară încet. Cu aceeași constantă în ambele
    // sensuri, chipul ar clipi pe fiecare consoană — arată ca o defecțiune.
    const catre = d.peSemnal ? this.semnal : 0;
    const k = catre > this.nivelNeted ? 0.30 : 0.05;
    this.nivelNeted += (catre - this.nivelNeted) * k * dt;

    const cx = this.l / 2, cy = this.i / 2;
    const puls = this.puls = 1
      + 0.035 * d.puls * Math.sin(this.t * 1.9)
      + 0.18 * this.nivelNeted;
    const tinte = d.forma === "nor" ? null : this.tinte[d.forma];

    const latura = Math.min(this.l, this.i);
    const agitatie = d.agitatie * (0.55 + 0.9 * this.nivelNeted) * this.dpr;

    for (let i = 0; i < this.particule.length; i++) {
      const p = this.particule[i];
      let tx, ty;
      if (tinte) {
        const t = tinte[i];
        tx = cx + (t[0] - cx) * puls;
        ty = cy + (t[1] - cy) * puls;
      } else {
        // Fără siluetă: fiecare particulă își ține orbita ei, în ritmul ei.
        // Norul rămâne nor cât ține starea, nu se scurge într-un inel.
        const raza = latura * (0.04 + 0.24 * p.r * p.r) * puls;
        const a = p.unghi + this.t * (0.25 + 0.55 * p.r) * p.sens;
        tx = cx + Math.cos(a) * raza;
        ty = cy + Math.sin(a) * raza * 0.82;
      }

      // Cât de tare trage ținta. Cu 0.007 norul se așeza în ~2,5 s: prea
      // moale pentru „ca în anime". Cu 0.011 zborul ține ~1,5 s și
      // dârele se mai văd.
      const arc = 0.011 * (0.55 + p.r) * dt;
      p.vx += (tx - p.x) * arc + (Math.random() - 0.5) * agitatie;
      p.vy += (ty - p.y) * arc + (Math.random() - 0.5) * agitatie;
      const frana = Math.pow(0.91, dt);
      p.vx *= frana; p.vy *= frana;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
    }
  }

  // ── Desenul ────────────────────────────────────────────────────────────────

  deseneaza() {
    const c = this.c, d = this.def;

    // Fundalul se pune cu alfa, nu se șterge: rămâne o dâră scurtă în urma
    // fiecărei particule, și din dâre se vede direcția transformării.
    c.globalCompositeOperation = "source-over";
    c.fillStyle = `rgba(${this.bg[0]},${this.bg[1]},${this.bg[2]},0.34)`;
    c.fillRect(0, 0, this.l, this.i);

    this.grila();
    this.ploaie();

    // `lighter` adună lumina acolo unde particulele se suprapun: miezul formei
    // iese de la sine mai aprins decât marginea, fără nicio umbră desenată.
    c.globalCompositeOperation = "lighter";

    const cald = Math.min(1, d.cald * (0.6 + 0.4 * this.nivelNeted) + 0.30 * this.nivelNeted);

    // Haloul: aceleași particule, de trei ori mai mari, cu alfa aproape de zero.
    // Adunate în `lighter` dau strălucirea de neon din referințe. `shadowBlur`
    // ar fi dat același lucru mai frumos și de zece ori mai scump — se
    // recalculează pentru fiecare cerc, iar aici sunt două mii pe cadru.
    const mediu = amesteca(
      amesteca(RECE, RECE_DESCHIS, 0.5),
      d.iris ? IRIS : amesteca(LAMPA, AUR, 0.5),
      cald,
    );
    c.fillStyle = `rgba(${mediu[0] | 0},${mediu[1] | 0},${mediu[2] | 0},${(0.020 + 0.022 * this.nivelNeted).toFixed(3)})`;
    c.beginPath();
    for (const p of this.particule) {
      const r = p.raza * this.scaraRaza * 3.4;
      c.moveTo(p.x + r, p.y);
      c.arc(p.x, p.y, r, 0, TAU);
    }
    c.fill();

    for (let g = 0; g < GALETI; g++) {
      const u = g / (GALETI - 1);
      // `u*u`, nu `u`: cu amestec liniar jumătate din nor ieșea cyan și
      // dominanta se muta de pe violet pe albastru. Așa cyanul rămâne scânteia
      // de la vârf, cum e în referințe.
      const rece = amesteca(RECE, RECE_DESCHIS, u * u);
      const viu = d.iris ? IRIS : amesteca(LAMPA, AUR, u);
      const col = amesteca(rece, viu, cald);
      c.fillStyle = `rgba(${col[0] | 0},${col[1] | 0},${col[2] | 0},${(0.115 + 0.175 * u).toFixed(3)})`;
      c.beginPath();
      for (const p of this.galeti[g]) {
        const r = p.raza * this.scaraRaza;
        c.moveTo(p.x + r, p.y);
        c.arc(p.x, p.y, r, 0, TAU);
      }
      c.fill();
    }

    // Ochii. Sînt singura lumină albă din nor, și RAMIN ALBI si cind corpul e
    // roșu. Ramura care-i înroșea odată cu `iris` era moartă cît irisul era
    // numai al lui `rau` — `rau` n-are siluetă, deci n-are ochi — și ar fi
    // înviat greșit acum, cînd irisul e culoarea interlocutorului: o pisică
    // roșie cu ochii roșii nu mai citește a pisică. La `nor` particulele astea
    // sînt ca toate celelalte, altfel ar rămâne două pete albe plutind în gol.
    const areOchi = d.forma !== "nor";
    const colOchi = areOchi
      ? amesteca(amesteca(RECE_DESCHIS, OCHI, 0.55), OCHI, cald)
      : mediu;
    const alfaOchi = areOchi ? 0.34 + 0.30 * this.nivelNeted : 0.16;
    c.fillStyle = `rgba(${colOchi[0] | 0},${colOchi[1] | 0},${colOchi[2] | 0},${alfaOchi.toFixed(3)})`;
    c.beginPath();
    for (const p of this.ochii) {
      const r = p.raza * this.scaraRaza;
      c.moveTo(p.x + r, p.y);
      c.arc(p.x, p.y, r, 0, TAU);
    }
    c.fill();

    c.globalCompositeOperation = "source-over";
    c.globalAlpha = 1;
  }

  /** Grila de circuit din spatele norului: cadrul în care stă chipul, luat din
   *  referințele cu podea de circuite și ploaie de date. Respiră pe același
   *  `nivelNeted` ca forma, deci vocea se vede și în fundal, nu doar în nor.
   *  Se desenează în `lighter` peste fundalul deja pus, ca să nu taie dârele. */
  grila() {
    const c = this.c;
    const pas = Math.max(26 * this.dpr, Math.min(this.l, this.i) / 11);
    // Grila e violet, nu cyan: pe voce tare cyanul urca peste nor și ochiul se
    // ducea la fundal, nu la chip. Și crește puțin cu nivelul, nu mult.
    const viu = 0.030 + 0.028 * this.nivelNeted;
    if (viu < 0.002) return;

    c.globalCompositeOperation = "lighter";
    c.lineWidth = Math.max(1, this.dpr * 0.55);
    c.strokeStyle = `rgba(${LAMPA[0]},${LAMPA[1]},${LAMPA[2]},${viu.toFixed(3)})`;
    c.beginPath();
    const ox = (this.l % pas) / 2, oy = (this.i % pas) / 2;
    for (let x = ox; x <= this.l; x += pas) { c.moveTo(x, 0); c.lineTo(x, this.i); }
    for (let y = oy; y <= this.i; y += pas) { c.moveTo(0, y); c.lineTo(this.l, y); }
    c.stroke();

  }

  /** Ploaia de date: șapte trasee palide, care se aprind pe `nivelNeted`, ca
   *  grila — vocea se vede și în fundal.
   *
   *  Zarul e sinusoidal, nu `Math.random`: trebuie ca traseul `i` să cadă în
   *  același loc la fiecare cadru, altfel ploaia clipește. */
  ploaie() {
    const c = this.c;
    const n = 7;
    const zar = (k) => { const v = Math.sin(k * 12.9898) * 43758.5453; return v - Math.floor(v); };

    c.globalCompositeOperation = "lighter";
    for (let i = 0; i < n; i++) {
      const x = Math.round(zar(i + 1) * this.l) + 0.5;
      const lung = this.i * (0.20 + 0.85 * zar(i + 61));
      const viteza = 0.040 + 0.075 * zar(i + 131);
      const y = (((this.t * viteza + zar(i + 197)) % 1) * (this.i + lung)) - lung;

      const a = (0.05 + 0.16 * this.nivelNeted) * (0.45 + 1.5 * zar(i + 263));

      const sus = zar(i + 331) < 0.3 ? RECE_DESCHIS : LAMPA;
      const g = c.createLinearGradient(0, y, 0, y + lung);
      g.addColorStop(0, `rgba(${sus[0]},${sus[1]},${sus[2]},0)`);
      g.addColorStop(1, `rgba(${AUR[0]},${AUR[1]},${AUR[2]},${Math.min(0.62, a).toFixed(3)})`);
      c.strokeStyle = g;
      c.lineWidth = Math.max(1, this.dpr * (0.6 + 1.9 * zar(i + 397)));
      c.beginPath();
      c.moveTo(x, y); c.lineTo(x, y + lung);
      c.stroke();
    }
  }

}

// ── Siluetele ────────────────────────────────────────────────────────────────
//
// Se desenează o dată, alb pe negru, pe o pânză de 240 px, și din ele se trag
// puncte la întâmplare. Coordonatele sunt fracțiuni din latură, ca desenul să
// nu depindă de mărimea pânzei.

/** Pisica: șade, coada groasă ridicată în cârlig. Ce ascultă și ce așteaptă.
 *
 *  Desenul de dinainte era o pisică „de pictogramă": cap mic, urechi mici,
 *  coadă subțire. Referințele din 25 august sînt toate chibi — cap cât o
 *  treime din înălțime, urechi cât capul, coadă cât corpul. Proporția e ce s-a
 *  schimbat, nu tehnica. */
function pisica(c, L) {
  const p = (v) => v * L;
  c.lineCap = "round";
  c.lineJoin = "round";
  c.strokeStyle = c.fillStyle;

  // coada, prima: trece pe sub corp, iar norul n-are straturi — ce se suprapune
  // se adună.
  c.beginPath();
  c.moveTo(p(0.66), p(0.90));
  c.bezierCurveTo(p(0.94), p(0.92), p(0.98), p(0.62), p(0.83), p(0.50));
  c.lineWidth = p(0.105);
  c.stroke();

  // corpul: un clopot îngust. Capul e mai lat decât umerii — asta face
  // proporția chibi din referințe; cu corp cât capul iese un urs.
  c.beginPath();
  c.moveTo(p(0.295), p(0.955));
  c.bezierCurveTo(p(0.275), p(0.75), p(0.345), p(0.585), p(0.50), p(0.585));
  c.bezierCurveTo(p(0.655), p(0.585), p(0.725), p(0.75), p(0.705), p(0.955));
  c.closePath();
  c.fill();

  // lăbuțele din față, strânse una lângă alta. Erau două ovale goale; acum au
  // degete, tăiate din umplutură — pe un nor uniform ce se vede sînt golurile,
  // nu liniile.
  c.beginPath();
  c.ellipse(p(0.424), p(0.912), p(0.075), p(0.055), 0, 0, TAU);
  c.ellipse(p(0.576), p(0.912), p(0.075), p(0.055), 0, 0, TAU);
  c.fill();
  degete(c, L, [0.424, 0.576], 0.898, 0.048, 0.046);

  // capul, lat și rotund
  c.beginPath();
  c.ellipse(p(0.50), p(0.355), p(0.235), p(0.200), 0, 0, TAU);
  c.fill();

  // urechile: mari, ascuțite, cu vârful ieșit mult peste cap
  c.beginPath();
  c.moveTo(p(0.315), p(0.300)); c.lineTo(p(0.245), p(0.045)); c.lineTo(p(0.510), p(0.195));
  c.closePath();
  c.moveTo(p(0.685), p(0.300)); c.lineTo(p(0.755), p(0.045)); c.lineTo(p(0.490), p(0.195));
  c.closePath();
  c.fill();

  // mustățile: curbate și scurte. Drepte și lungi ieșeau antene, nu mustăți.
  c.lineWidth = p(0.015);
  c.beginPath();
  c.moveTo(p(0.30), p(0.415)); c.quadraticCurveTo(p(0.19), p(0.395), p(0.115), p(0.345));
  c.moveTo(p(0.30), p(0.445)); c.quadraticCurveTo(p(0.19), p(0.465), p(0.120), p(0.475));
  c.moveTo(p(0.70), p(0.415)); c.quadraticCurveTo(p(0.81), p(0.395), p(0.885), p(0.345));
  c.moveTo(p(0.70), p(0.445)); c.quadraticCurveTo(p(0.81), p(0.465), p(0.880), p(0.475));
  c.stroke();
}

/** Ochii pisicii, separat: ei primesc particulele lor și culoarea lor.
 *  Coordonatele TREBUIE să cadă în capul desenat de `pisica`, altfel lumina
 *  plutește lângă cap. */
function ochii(c, L) {
  const p = (v) => v * L;
  c.beginPath();
  c.ellipse(p(0.410), p(0.355), p(0.072), p(0.090), 0, 0, TAU);
  c.ellipse(p(0.590), p(0.355), p(0.072), p(0.090), 0, 0, TAU);
  c.fill();
}

/** Degetele unei labe: se TAIE din ce e deja umplut.
 *
 *  Pe un nor uniform o linie desenată peste umplutură nu se vede — densitatea e
 *  aceeași peste tot. Ce se vede sînt golurile. `centre` sînt mijloacele
 *  labelor, `y` unde încep tăieturile. */
function degete(c, L, centre, y, lat, lung) {
  const p = (v) => v * L;
  c.save();
  c.globalCompositeOperation = "destination-out";
  c.lineCap = "butt";
  c.lineWidth = p(0.013);
  c.beginPath();
  for (const cx of centre) {
    for (const dx of [-lat, 0, lat]) {
      c.moveTo(p(cx + dx * 0.55), p(y));
      c.lineTo(p(cx + dx), p(y + lung));
    }
  }
  c.stroke();
  c.restore();
}

function esantion(deseneaza, numar) {
  const L = 240;
  const aux = document.createElement("canvas");
  aux.width = aux.height = L;
  const c = aux.getContext("2d", { willReadFrequently: true });
  c.fillStyle = "#fff";
  deseneaza(c, L);

  const px = c.getImageData(0, 0, L, L).data;
  const puncte = [];
  let incercari = 0;
  const plafon = numar * 400;
  while (puncte.length < numar && incercari < plafon) {
    incercari++;
    const x = Math.random() * L, y = Math.random() * L;
    if (px[(((y | 0) * L) + (x | 0)) * 4 + 3] > 128) puncte.push([x / L, y / L]);
  }
  if (puncte.length < numar) {
    // Silueta e prea subțire pentru câte puncte s-au cerut. Se spune, nu se
    // umple cu zerouri: o siluetă care nu se poate eșantiona e o siluetă
    // greșită, iar norul ar arăta ca o grămadă în colț.
    console.warn("[chip] siluetă prea subțire:", puncte.length, "din", numar);
    const gasite = puncte.length;
    if (!gasite) return Array.from({ length: numar }, () => [0.5, 0.5]);
    for (let i = 0; puncte.length < numar; i++) puncte.push(puncte[i % gasite]);
  }
  return puncte;
}

// Urechea lui Mih.AI — pragurile și tăierea rostirii.
//
// DE CE UN AudioWorklet SI NU requestAnimationFrame:
//
//   rAF se oprește complet cât fereastra e ascunsă — măsurat în JA.S.Mine pe
//   4 august: zero cadre în șase secunde, cât `setInterval` bătea de șase ori,
//   adică 1 Hz. La 1 Hz nu poți tăia o rostire de 0,8 s. Aici ceasul e chemat de
//   placa de sunet, nu de compozitorul de ferestre, iar pasul se ia din
//   `sampleRate` — deci e exact și când fereastra e minimizată.
//
// CE FACE SI CE NU: numără, decide unde începe și unde se termină o rostire, și
// anunță. Nu trimite nimic și nu vorbește cu serverul — asta face `ureche.js`.
//
// PRE-ROLL: când volumul trece pragul, primele silabe au trecut deja. De-aia
// tamponul curge tot timpul, iar la începutul unei rostiri se ia și sfertul de
// secundă dinainte. Fără el, "da" devine "a".

const PAS = 128; // cadrele pe care le dă placa de sunet la un apel

class Ureche extends AudioWorkletProcessor {
  constructor(optiuni) {
    super();
    const p = optiuni.processorOptions || {};
    this.pragVolum = p.pragVolum ?? 0.012;
    this.minimVorbire = p.minimVorbire ?? 0.15;
    this.pragTacere = p.pragTacere ?? 2.0;
    this.maximRostire = p.maximRostire ?? 60.0;
    this.preRoll = p.preRoll ?? 0.25;

    this.rata = sampleRate;
    this.pasSecunde = PAS / this.rata;

    // Tamponul de pre-roll, circular, mereu în mișcare.
    this.inainte = new Float32Array(Math.ceil(this.preRoll * this.rata));
    this.pozitie = 0;
    this.plin = false;

    this.inRostire = false;
    this.pauzat = false;
    // SURD nu e acelasi lucru cu PAUZAT, si confuzia a costat.
    //
    //   `pauzat` e pentru fereastra de transcriere: tacerea nu mai numara, dar
    //   ce spui se aduna in continuare, ca sa nu pierzi fraza rostita peste ea.
    //   `surd` e pentru fereastra in care VORBESTE EL: nu se aduna nimic, si o
    //   rostire inceputa se arunca.
    //
    // Cat au fost acelasi lucru, o tuse prinsa cat se sintetiza raspunsul
    // ajungea mesaj nou, iar mesajul nou taia rostirea la mijloc. Masurat pe 25
    // august: raspunsul de 69 de cuvinte cere 4,9 s de sinteza, si tot
    // intervalul ala urechea era deschisa.
    this.surd = false;
    this.bucati = [];
    this.secundeVorbire = 0;
    this.secundeTacere = 0;
    this.secundeRostire = 0;

    // Vârful de volum din ultima zecime de secundă, pentru chip.
    this.varf = 0;
    this.deLaVolum = 0;

    // Cât se transcrie, tăcerea nu mai numără — dar zgomotul tot se adună.
    // Altfel vorbirea rostită peste transcriere n-ar mai fi vorbire, iar
    // tamponul ei s-ar recicla.
    this.port.onmessage = (e) => {
      if (!e.data) return;
      if (e.data.tip === "pauza") this.pauzat = !!e.data.valoare;
      if (e.data.tip === "surd") {
        this.surd = !!e.data.valoare;
        if (this.surd) this.reseteaza();
      }
    };
  }

  scrieInainte(cadre) {
    for (let i = 0; i < cadre.length; i++) {
      this.inainte[this.pozitie] = cadre[i];
      this.pozitie = (this.pozitie + 1) % this.inainte.length;
      if (this.pozitie === 0) this.plin = true;
    }
  }

  citesteInainte() {
    if (!this.plin) return this.inainte.slice(0, this.pozitie);
    const iesire = new Float32Array(this.inainte.length);
    iesire.set(this.inainte.subarray(this.pozitie));
    iesire.set(this.inainte.subarray(0, this.pozitie), this.inainte.length - this.pozitie);
    return iesire;
  }

  inchide(motiv) {
    let total = 0;
    for (const b of this.bucati) total += b.length;
    const tot = new Float32Array(total);
    let la = 0;
    for (const b of this.bucati) { tot.set(b, la); la += b.length; }

    this.port.postMessage(
      { tip: "rostire", pcm: tot, rata: this.rata,
        vorbire: this.secundeVorbire, motiv },
      [tot.buffer],
    );
    this.reseteaza();
  }

  reseteaza() {
    this.inRostire = false;
    this.bucati = [];
    this.secundeVorbire = 0;
    this.secundeTacere = 0;
    this.secundeRostire = 0;
  }

  process(intrari) {
    const canal = intrari[0] && intrari[0][0];
    if (!canal) return true;

    let suma = 0;
    for (let i = 0; i < canal.length; i++) suma += canal[i] * canal[i];
    const volum = Math.sqrt(suma / canal.length);
    const sunet = volum > this.pragVolum;

    // Cat e surd, tamponul de pre-roll curge mai departe — altfel prima silaba
    // de dupa s-ar pierde — dar nimic nu se aduna si nimic nu pleaca. Nici
    // volumul: chipul pulseaza atunci pe amplitudinea REDARII, iar doua surse
    // care scriu acelasi numar s-ar bate intre ele.
    if (this.surd) {
      this.scrieInainte(canal);
      return true;
    }

    // Volumul se trimite mai departe pentru chip, plafonat la ~10 mesaje pe
    // secundă: mai des nu se vede cu ochiul, dar costă mesaje pe fiecare cadru
    // audio. Pleacă VARFUL din interval, nu ultima valoare — o silabă ține mai
    // puțin de o zecime de secundă, și media ar netezi exact ce trebuie văzut.
    this.varf = Math.max(this.varf, volum);
    this.deLaVolum += this.pasSecunde;
    if (this.deLaVolum >= 0.1) {
      this.port.postMessage({ tip: "volum", volum: this.varf });
      this.varf = 0;
      this.deLaVolum = 0;
    }

    if (!this.inRostire) {
      this.scrieInainte(canal);
      if (sunet) {
        this.secundeVorbire += this.pasSecunde;
        // Un cadru peste prag nu e o frază: o ușă, o tastă, un oftat trec
        // pragul de volum, dar nu durează.
        if (this.secundeVorbire >= this.minimVorbire) {
          this.inRostire = true;
          this.bucati = [this.citesteInainte(), canal.slice()];
          this.secundeRostire = this.preRoll + this.pasSecunde;
          this.secundeTacere = 0;
          this.port.postMessage({ tip: "vorbeste" });
        }
      } else if (this.secundeVorbire > 0) {
        // Reciclarea: zgomotul care n-a devenit rostire se uită, ca să nu se
        // adune peste zi și să nască o "frază" din trei clicuri de mouse.
        this.secundeVorbire = 0;
      }
      return true;
    }

    this.bucati.push(canal.slice());
    this.secundeRostire += this.pasSecunde;

    if (sunet) {
      this.secundeVorbire += this.pasSecunde;
      this.secundeTacere = 0;
    } else if (!this.pauzat) {
      this.secundeTacere += this.pasSecunde;
      if (this.secundeTacere >= this.pragTacere) {
        this.inchide("tacere");
        return true;
      }
    }

    if (this.secundeRostire >= this.maximRostire) this.inchide("plafon");
    return true;
  }
}

registerProcessor("ureche", Ureche);

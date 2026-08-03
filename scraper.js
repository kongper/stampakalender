/* Stampakalender-skraper (maalefunksjon).
 *
 * VIKTIG: Tidene MAA leses fra en LIVE, ferdig-lastet StaticDay-side (navigert til,
 * ikke fetch+injisert). Sidens egen JavaScript posisjonerer booking-blokkene etter
 * lasting; raa HTML hentet med fetch og injisert gir blokkene ~10 min feil plassering.
 *
 * window.__measureDay(venue, dayISO) maaler den siden som er lastet NAA og returnerer
 * en liste [[venue, dato, ressurs, leietaker, fra, til], ...]. Tid beregnes fra de
 * faktiske time-etikettenes posisjon (getBoundingClientRect) som linjal — booking-
 * blokkenes offsetParent deler ikke origo med time-cellene, og cellenes offsetWidth
 * er ikke lik faktisk px/time.
 *
 * Bruk (driver): scrape_playwright.js navigerer til hver dag/arena og kaller __measureDay.
 * Bruk (manuelt i nettleser): naviger til
 *   https://statisk.bestille.no/Time/StaticDay.aspx?Day=YYYY-MM-DDT00:00:00&key=<KEY>
 * og kjor  window.__measureDay('eid'|'stamp', 'YYYY-MM-DD').
 */
(function () {
  function t(min) {
    min = Math.round(min / 5) * 5;
    if (min < 0) min = 0; if (min > 1440) min = 1440;
    const h = Math.floor(min / 60), m = min % 60;
    return String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0");
  }
  window.__measureDay = function (venue, dayISO) {
    const header = Array.from(document.querySelectorAll("#tabSchedule .B")).find(b => /topHeader/.test(b.className));
    const hcells = header
      ? Array.from(header.children)
          .filter(c => /TPTimeHour/.test(c.className))
          .map(c => ({ h: parseInt(c.textContent.trim(), 10), left: c.getBoundingClientRect().left }))
          .filter(x => !isNaN(x.h))
      : [];
    if (hcells.length < 2) return [];
    const A = hcells[0], B = hcells[hcells.length - 1];
    const pxPerHour = (B.left - A.left) / (B.h - A.h);
    const timeAt = (px) => t(Math.round((A.h + (px - A.left) / pxPerHour) * 60));
    const labels = Array.from(document.querySelectorAll("#divHeader .TPRes")).map(e => e.textContent.trim().replace(/\s+/g, " "));
    const rows = Array.from(document.querySelectorAll("#tabSchedule .B")).filter(b => !/topHeader/.test(b.className));
    const out = [];
    rows.forEach((r, i) => {
      const res = labels[i] || ("row" + i);
      Array.from(r.querySelectorAll(".A")).forEach(w => {
        const a = w.querySelector("a");
        const name = (a ? a.textContent : w.textContent).trim().replace(/\s+/g, " ");
        if (!name || /Stengt/i.test(name) || /^Ute$/i.test(name)) return;
        const rc = w.getBoundingClientRect();
        out.push([venue, dayISO, res, name, timeAt(rc.left), timeAt(rc.right)]);
      });
    });
    return out;
  };
})();
"scraper klar";

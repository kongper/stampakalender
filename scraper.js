/* Stampakalender-skraper. Kjores i konteksten til en statisk.bestille.no-side
   (same-origin fetch kreves). Definerer window.__scrapeRange + window.__ACC.
   Bruk:
     1) Naviger til https://statisk.bestille.no/Time/StaticDay.aspx?key=DF518BE1-E922-42C6-B381-C3B559EC32CC
     2) Kjor innholdet i denne filen.
     3) window.__accReset();
        Kall window.__scrapeRange('YYYY-MM-DD','YYYY-MM-DD') i ~30-dagers bolker,
        fra og med dagens dato og noen maaneder frem.
     4) Les JSON.stringify(window.__scrapeResult()) og lagre til scrape.json.
*/
(function () {
  const KEYS = { eid: "DF518BE1-E922-42C6-B381-C3B559EC32CC",
                 stamp: "914067A6-3198-44FB-81E6-F8B0F37BA427" };
  const START = 7 * 60;
  window.__ACC = window.__ACC || [];
  window.__META = window.__META || {};
  window.__accReset = function () { window.__ACC = []; window.__META = {}; };
  window.__scrapeResult = function () {
    const n = new Date();
    const today = n.getFullYear() + "-" + String(n.getMonth() + 1).padStart(2, "0") + "-" + String(n.getDate()).padStart(2, "0");
    return { today, from: window.__META.from, to: window.__META.to, bookings: window.__ACC };
  };
  function t(min) { min = Math.round(min / 5) * 5; const h = Math.floor(min / 60), m = min % 60; return String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0"); }
  async function parseDay(venue, dayISO) {
    let html;
    try { html = await fetch("StaticDay.aspx?Day=" + dayISO + "T00:00:00&key=" + KEYS[venue]).then(r => r.text()); }
    catch (e) { return; }
    const doc = new DOMParser().parseFromString(html, "text/html");
    const sched = doc.querySelector(".Schedule");
    if (!sched) return;
    let host = document.getElementById("__probe"); if (host) host.remove();
    host = document.createElement("div"); host.id = "__probe";
    host.style.cssText = "position:absolute;left:-9999px;top:0;width:3000px;";
    host.innerHTML = sched.outerHTML; document.body.appendChild(host);
    const labels = Array.from(host.querySelectorAll("#divHeader .TPRes")).map(e => e.textContent.trim().replace(/\s+/g, " "));
    const allRows = Array.from(host.querySelectorAll("#tabSchedule .B"));
    const header = allRows.find(b => /topHeader/.test(b.className));
    let pxh = 73;
    if (header) { const hs = Array.from(header.children).filter(c => /TPTimeHour/.test(c.className)); if (hs.length) pxh = hs.reduce((a, c) => a + c.offsetWidth, 0) / hs.length; }
    const rows = allRows.filter(b => !/topHeader/.test(b.className));
    rows.forEach((r, i) => {
      const res = labels[i] || ("row" + i);
      Array.from(r.querySelectorAll(".A")).forEach(b => {
        const name = b.textContent.trim().replace(/\s+/g, " ");
        if (!name || /Stengt/i.test(name) || /^Ute$/i.test(name)) return;
        const s = START + b.offsetLeft / pxh * 60;
        const e = START + (b.offsetLeft + b.offsetWidth) / pxh * 60;
        window.__ACC.push([venue, dayISO, res, name, t(s), t(e)]);
      });
    });
    host.remove();
  }
  window.__scrapeRange = async function (fromISO, toISO) {
    if (!window.__META.from || fromISO < window.__META.from) window.__META.from = fromISO;
    if (!window.__META.to || toISO > window.__META.to) window.__META.to = toISO;
    let d = new Date(fromISO + "T00:00:00Z"); const end = new Date(toISO + "T00:00:00Z");
    let days = 0;
    while (d <= end) {
      const iso = d.toISOString().slice(0, 10);
      await parseDay("eid", iso);
      await parseDay("stamp", iso);
      days++;
      d.setUTCDate(d.getUTCDate() + 1);
    }
    return { doneDays: days, totalB
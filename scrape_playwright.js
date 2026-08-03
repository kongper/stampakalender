/* Headless driver for the Stampakalender scraper.
 *
 * Runs in GitHub Actions (or locally). For each day (today .. today+DAYS_AHEAD)
 * and each venue it NAVIGATES to the live StaticDay page (so the page's own
 * JavaScript positions the booking blocks correctly), then reads the times with
 * window.__measureDay from scraper.js. Writes scrape.json in this directory.
 *
 * Why navigate instead of fetch+inject: the page repositions booking blocks after
 * load, so raw HTML fetched and injected places them ~10 min wrong. Only a live,
 * fully-loaded page gives grid-accurate times.
 *
 * Usage:  node scrape_playwright.js
 * Env:    DAYS_AHEAD (default 150)
 *
 * The produced scrape.json is consumed by nightly.py.
 */
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const HERE = __dirname;
const SCRAPER = fs.readFileSync(path.join(HERE, "scraper.js"), "utf8");
const VENUES = {
  eid: "DF518BE1-E922-42C6-B381-C3B559EC32CC",
  stamp: "914067A6-3198-44FB-81E6-F8B0F37BA427",
};
const DAYS_AHEAD = parseInt(process.env.DAYS_AHEAD || "150", 10);
const DAY_MS = 86400000;
const iso = (d) => d.toISOString().slice(0, 10);
const urlFor = (key, day) =>
  "https://statisk.bestille.no/Time/StaticDay.aspx?Day=" + day + "T00:00:00&key=" + key;

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  // Define window.__measureDay on every page load (survives navigation).
  await page.addInitScript(SCRAPER);

  const start = new Date(iso(new Date()) + "T00:00:00Z");
  const finalEnd = new Date(start.getTime() + DAYS_AHEAD * DAY_MS);

  const bookings = [];
  const tally = { eid: 0, stamp: 0 };
  let dayCount = 0;

  for (let cur = new Date(start); cur <= finalEnd; cur = new Date(cur.getTime() + DAY_MS)) {
    const day = iso(cur);
    for (const [venue, key] of Object.entries(VENUES)) {
      try {
        await page.goto(urlFor(key, day), { waitUntil: "load", timeout: 60000 });
        await page.waitForSelector("#tabSchedule .B", { timeout: 20000 }).catch(() => {});
        await page.waitForTimeout(150); // la sidens JS posisjonere blokkene
        const dayBk = await page.evaluate(
          ({ v, d }) => (window.__measureDay ? window.__measureDay(v, d) : []),
          { v: venue, d: day }
        );
        for (const bk of dayBk) { bookings.push(bk); tally[venue]++; }
      } catch (err) {
        console.error(`  ${day} ${venue}: ${err.message}`);
      }
    }
    dayCount++;
    if (dayCount % 15 === 0) {
      console.log(`  ${day}: eid=${tally.eid}, stamp=${tally.stamp} (${bookings.length} total so far)`);
    }
  }

  await browser.close();

  const total = bookings.length;
  // Abort if EITHER source is empty — almost always means the page structure
  // changed; proceeding would let nightly.py delete that venue's future bookings.
  if (tally.eid === 0 || tally.stamp === 0) {
    console.error(
      `ERROR: a source returned no bookings (eid=${tally.eid}, stamp=${tally.stamp}, total=${total}) — aborting so the DB is not wiped.`
    );
    process.exit(1);
  }

  const result = { today: iso(start), from: iso(start), to: iso(finalEnd), bookings };
  fs.writeFileSync(path.join(HERE, "scrape.json"), JSON.stringify(result));
  console.log(
    `Wrote scrape.json: eid=${tally.eid}, stamp=${tally.stamp}, ${total} total; window ${result.from} .. ${result.to}`
  );
})().catch((err) => {
  console.error(err);
  process.exit(1);
});

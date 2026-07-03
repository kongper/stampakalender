/* Headless driver for the Stampakalender scraper.
 *
 * Runs in GitHub Actions (or locally). Opens a real Chromium page on
 * statisk.bestille.no (same-origin fetch + layout offsets are required by
 * scraper.js), injects scraper.js, scrapes today .. today+DAYS_AHEAD in
 * ~30-day chunks, and writes scrape.json in this directory.
 *
 * Usage:  node scrape_playwright.js
 * Env:    DAYS_AHEAD (default 150)  CHUNK_DAYS (default 30)
 *
 * The produced scrape.json is consumed by nightly.py.
 */
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const HERE = __dirname;
const SCRAPER = fs.readFileSync(path.join(HERE, "scraper.js"), "utf8");
const EID_KEY = "DF518BE1-E922-42C6-B381-C3B559EC32CC";
const BASE = "https://statisk.bestille.no/Time/StaticDay.aspx?key=" + EID_KEY;
const DAYS_AHEAD = parseInt(process.env.DAYS_AHEAD || "150", 10);
const CHUNK_DAYS = parseInt(process.env.CHUNK_DAYS || "30", 10);
const DAY_MS = 86400000;

const iso = (d) => d.toISOString().slice(0, 10);

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log("Opening", BASE);
  await page.goto(BASE, { waitUntil: "domcontentloaded", timeout: 60000 });

  // Define window.__scrapeRange / __accReset / __scrapeResult in page context.
  await page.evaluate(SCRAPER);
  await page.evaluate(() => window.__accReset());

  const start = new Date(iso(new Date()) + "T00:00:00Z");
  const finalEnd = new Date(start.getTime() + DAYS_AHEAD * DAY_MS);

  let cur = new Date(start);
  while (cur <= finalEnd) {
    let chunkEnd = new Date(cur.getTime() + (CHUNK_DAYS - 1) * DAY_MS);
    if (chunkEnd > finalEnd) chunkEnd = finalEnd;
    const a = iso(cur), b = iso(chunkEnd);
    const res = await page.evaluate(
      async ({ a, b }) => await window.__scrapeRange(a, b),
      { a, b }
    );
    console.log(`  ${a} .. ${b}: ${res.doneDays} days, ${res.totalBookings} bookings so far`);
    cur = new Date(chunkEnd.getTime() + DAY_MS);
  }

  const result = await page.evaluate(() => window.__scrapeResult());
  await browser.close();

  if (!result.bookings || result.bookings.length === 0) {
    console.error("ERROR: no bookings scraped — aborting so the DB is not wiped.");
    process.exit(1);
  }

  fs.writeFileSync(path.join(HERE, "scrape.json"), JSON.stringify(result));
  console.log(
    `Wrote scrape.json: ${result.bookings.length} bookings, window ${result.from} .. ${result.to}`
  );
})().catch((err) => {
  console.error(err);
  process.exit(1);
});

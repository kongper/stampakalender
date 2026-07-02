# Stampakalender – oppsett

Interaktiv kalender over haller, baner og garderober på Stampesletta, Lillehammer,
med data fra bestille.no (Eidsiva Arena / Ungdomshallen + uteanleggene).

## Filer
- `stampakalender.db` – SQLite-database med alle bookinger (tabell `bookings`),
  endringslogg (`changes`) og `meta`. Dette er sannhetskilden.
- `stampakalender.html` – den interaktive kalenderen (åpne i nettleser). Genereres fra DB-en.
- `stampakalender_2026.json` – lesbart øyeblikksbilde av det opprinnelige uttrekket.
- `template.html` – HTML-mal med plassholderne `__DATA__` og `__TODAY__`.
- `stampa_lib.py`, `init_db.py`, `update_from_scrape.py` – bygge-/oppdateringsskript.
- `scraper.js` / `nightly.py` – brukes av den nattlige planlagte jobben (autoritativ
  kopi ligger i selve jobb-instruksjonen, siden mappen kan korrupte tekstfiler).

## Nattlig jobb (kl. 03:00)
Henter **kun dagens dato og fremover** fra bestille.no, sammenligner mot databasen,
oppdaterer den (rører aldri fortiden), logger endringer og regenererer kalenderen.
Gir en kort rapport over nye/fjernede bookinger.

## Merk
- Kilden har kun data fra og med juli 2026; januar–juni 2026 finnes ikke.
- «Stengt LK» (sommerstengt/vedlikehold) er utelatt fra bookinglisten og vist som stengt.
- SQLite kjøres på en lokal kopi og synkes tilbake som byte-kopi (mappen støtter ikke
  SQLite direkte).

# Stampakalender

Interaktiv kalender over haller, baner og garderober på **Stampesletta, Lillehammer** –
Eidsiva Arena / Ungdomshallen (innendørs) og uteanleggene. Data hentes fra Lillehammer
kommunes bookingsystem (bestille.no / Aktiv Kommune).

## Innhold

| Fil | Beskrivelse |
|-----|-------------|
| `stampakalender.html` | Den ferdige, interaktive kalenderen. Åpne i nettleser. |
| `stampakalender.db` | SQLite-database med alle bookinger (`bookings`), endringslogg (`changes`) og `meta`. Sannhetskilden. |
| `stampakalender_2026.json` | Lesbart øyeblikksbilde av det opprinnelige uttrekket. |
| `template.html` | HTML-mal med plassholderne `__DATA__` og `__TODAY__`. |
| `stampa_lib.py` | Delte hjelpefunksjoner (DB + HTML-generering). |
| `init_db.py` | Bygger databasen fra `stampakalender_2026.json`. |
| `update_from_scrape.py` | Oppdaterer DB fra et ferskt uttrekk og regenererer HTML. |
| `nightly.py` | Selvstendig nattlig oppdaterer (brukt av planlagt jobb). |
| `scraper.js` | Nettleser-skript som henter dagsdata fra bestille.no. |

## Funksjoner i kalenderen

- **Månedsvisning** med bookinger per dag og klikkbar dagsdetalj.
- **Dagsvisning** – tidslinje 07:00–23:30 med én ressurs per rad (opptatt = farget felt, ledig = tom rad).
- **Ressursfilter** med avkryssingsbokser gruppert per arena, flervalg.
- Sammenslåing av bookinger med samme leietaker og tid på tvers av flere baner.
- Søk på leietaker, måneds-/dagsnavigasjon.

## Slik bygges kalenderen

```bash
python3 init_db.py          # bygger stampakalender.db + stampakalender.html fra JSON
```

SQLite kan ikke kjøre direkte på nettverks-/synkroniserte mapper, så skriptene jobber mot
en lokal arbeidskopi (`/tmp/stampa`, kan overstyres med `STAMPA_WORK`) og byte-kopierer
`.db`/`.html` tilbake.

## Oppdatering

En planlagt jobb kjører hver natt: henter kun dagens dato og fremover fra kilden,
sammenligner mot databasen (rører aldri fortiden), logger nye/fjernede bookinger og
regenererer kalenderen. Manuell oppdatering:

```bash
python3 update_from_scrape.py scrape.json
```

## Merknader om data

- Kilden har typisk kun data noen måneder frem; historikk faller ut.
- «Stengt LK» (sommerstengt/vedlikehold) og ledige felt («Ute») utelates fra bookinglisten.
- Nøklene i `scraper.js` er offentlige visnings-nøkler fra bestille.nos delbare kalenderlenker (ikke hemmeligheter).

## Datakilde

statisk.bestille.no/Time/StaticDay (Lillehammer kommune / Aktiv Kommune).

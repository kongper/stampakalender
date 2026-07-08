#!/usr/bin/env python3
"""Selvstendig nattlig oppdaterer for Stampakalender.
Kjores i en lokal arbeidsmappe (ikke pa mounten - SQLite/tekst er upalitelig der).

Filer i arbeidsmappen (samme mappe som dette skriptet, eller angitt med STAMPA_RUN):
  stampakalender.db      - eksisterende DB (kopiert fra prosjektmappen av agenten)
  scrape.json            - ferskt uttrekk fra skraperen
  template.html          - (valgfri) HTML-mal; hvis gyldig regenereres kalenderen

Oppdaterer DB in-place, logger endringer i 'changes', skriver index.html
hvis mal finnes, og skriver en kort endringsrapport til stdout og til changes_report.txt.
"""
import os, sys, json, sqlite3, datetime

RUN = os.environ.get("STAMPA_RUN", os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(RUN, "stampakalender.db")
SCRAPE = os.path.join(RUN, "scrape.json")
TEMPLATE = os.path.join(RUN, "template.html")
HTML_OUT = os.path.join(RUN, "index.html")
REPORT = os.path.join(RUN, "changes_report.txt")

RES_EID = ["Idrettshall, vest- basishall","Idrettshall, øst","Ishall","Garderobe 3","Garderobe 4","Garderobe 5","Garderobe 6","Garderobe 7","Garderobe 8","Garderobe Dommere","Garderobe Vest","Ungdomshallen","Uhall - ishall","Uhall - garderobe 1","Uhall - garderobe 2","Uhall - garderobe 3","Uhall - garderobe 4","Uhall - garderobe 5","Uhall - garderobe 6"]
RES_STAMP = ["Garderobe Nord","Garderobe Syd","Søndre Bane Nord","Søndre bane Sør","Øvre Bane Nord","Øvre bane Sør","Nedre Bane","Vestre Bane","Nordre Grus","Treningssletta","Parkeringsareal","Røyslimoen Nord","Røyslimoen Sør","Røyslimoen 7er"]
STENGT = {"eidsiva": {"fra": "2026-06-30", "til": "2026-08-02", "beskrivelse": "Stengt LK (sommerstengt/vedlikehold) hele dagen, alle ressurser"}}
SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings(venue TEXT,date TEXT,resource TEXT,tenant TEXT,start TEXT,slutt TEXT,PRIMARY KEY(venue,date,resource,start,tenant));
CREATE TABLE IF NOT EXISTS changes(run_ts TEXT,change_type TEXT,venue TEXT,date TEXT,resource TEXT,tenant TEXT,start TEXT,slutt TEXT);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT);
CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(date);
"""

def rebuild_html(conn, today):
    rows = conn.execute("SELECT venue,date,resource,tenant,start,slutt FROM bookings").fetchall()
    tenants = sorted({r[3] for r in rows}); tidx = {n:i for i,n in enumerate(tenants)}
    reid, rstamp = list(RES_EID), list(RES_STAMP)
    def ridx(v, res):
        arr = reid if v=="eid" else rstamp
        if res not in arr: arr.append(res)
        return arr.index(res)
    eid, stamp = {}, {}
    for v,d,res,ten,s,e in rows:
        (eid if v=="eid" else stamp).setdefault(d, []).append([ridx(v,res), tidx[ten], s, e])
    for d in eid: eid[d].sort(key=lambda x:(x[2],x[0]))
    for d in stamp: stamp[d].sort(key=lambda x:(x[2],x[0]))
    from collections import Counter
    _byrun={}
    for _rt,_ct,_v,_d,_r,_t in conn.execute("SELECT run_ts,change_type,venue,date,resource,tenant FROM changes").fetchall():
        _e=_byrun.setdefault(_rt,{"a":[],"r":[]})
        (_e["a"] if _ct=="lagt til" else _e["r"]).append((_v,_d,_r,_t))
    _summ={}
    for _rt,_e in _byrun.items():
        _ac=Counter(_e["a"]); _rc=Counter(_e["r"])
        _m=sum(min(_ac[k],_rc[k]) for k in _ac if k in _rc)
        _s=_summ.setdefault(_rt[:10],[0,0,0])
        _s[0]+=sum(_ac.values())-_m; _s[1]+=_m; _s[2]+=sum(_rc.values())-_m
    _endr=[{"d":_d,"a":_summ[_d][0],"m":_summ[_d][1],"r":_summ[_d][2]} for _d in sorted(_summ,reverse=True)][:21]
    _sm=conn.execute("SELECT value FROM meta WHERE key='sist_oppdatert'").fetchone()
    DATA = {"navn":tenants,"resEid":reid,"resStamp":rstamp,"stengt":STENGT,"eid":eid,"stamp":stamp,"endringer":_endr,"sistOppdatert":(_sm[0] if _sm else "")}
    tpl = open(TEMPLATE, encoding="utf-8").read()
    if "__DATA__" not in tpl or not tpl.rstrip().endswith("</html>"):
        raise ValueError("mal ugyldig")
    out = tpl.replace("__DATA__", json.dumps(DATA, ensure_ascii=False, separators=(",",":"))).replace("__TODAY__", today)
    open(HTML_OUT, "w", encoding="utf-8").write(out)
    return len(rows)

def main():
    scrape = json.load(open(SCRAPE, encoding="utf-8"))
    today = scrape["today"]; frm = max(scrape["from"], today); to = scrape["to"]
    fresh = {tuple(b) for b in scrape["bookings"] if b[1] >= today}

    conn = sqlite3.connect(DB); conn.executescript(SCHEMA)
    run = datetime.datetime.now().isoformat(timespec="seconds")
    existing = {tuple(r) for r in conn.execute(
        "SELECT venue,date,resource,tenant,start,slutt FROM bookings WHERE date>=? AND date<=?", (frm, to)).fetchall()}
    added = fresh - existing; removed = existing - fresh

    for r in sorted(removed):
        conn.execute("DELETE FROM bookings WHERE venue=? AND date=? AND resource=? AND start=? AND tenant=?", (r[0],r[1],r[2],r[4],r[3]))
        conn.execute("INSERT INTO changes VALUES(?,?,?,?,?,?,?,?)", (run,"fjernet",*r))
    for r in sorted(added):
        conn.execute("INSERT OR REPLACE INTO bookings VALUES(?,?,?,?,?,?)", r)
        conn.execute("INSERT INTO changes VALUES(?,?,?,?,?,?,?,?)", (run,"lagt til",*r))
    conn.execute("INSERT INTO meta VALUES('sist_oppdatert',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (run,))
    conn.execute("INSERT INTO meta VALUES('sist_vindu',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (frm+".."+to,))
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    html_status = "ikke regenerert (ingen/ugyldig mal)"
    if os.path.exists(TEMPLATE):
        try:
            n = rebuild_html(conn, today); html_status = "regenerert (%d bookinger)" % n
        except Exception as ex:
            html_status = "IKKE regenerert: %s" % ex
    conn.close()

    def fmt(r):
        vn = "Eidsiva" if r[0]=="eid" else "Stampesletta"
        return "  [%s] %s %s-%s %s - %s" % (vn, r[1], r[4], r[5], r[2], r[3])
    lines = ["Stampakalender - nattlig oppdatering %s" % run,
             "Vindu: %s .. %s" % (frm, to),
             "Lagt til: %d | Fjernet: %d | Totalt i DB: %d" % (len(added), len(removed), total),
             "HTML: %s" % html_status]
    if added:
        lines.append("Nye bookinger:"); lines += [fmt(r) for r in sorted(added)]
    if removed:
        lines.append("Fjernede bookinger:"); lines += [fmt(r) for r in sorted(removed)]
    if not added and not removed:
        lines.append("Ingen endringer denne kjoringen.")
    report = "\n".join(lines)
    open(REPORT, "w", encoding="utf-8").write(report)
    print(report)

if __name__ == "__main__":
    main()

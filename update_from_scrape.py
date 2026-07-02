"""Oppdaterer databasen fra et ferskt skrape-uttrekk (kun dagens dato og fremover).
Bruk: python3 update_from_scrape.py scrape.json
scrape.json: {"today":"YYYY-MM-DD","from":"...","to":"...","bookings":[["eid","2026-08-03","Ishall","LKK ...","08:00","12:00"], ...]}
Rører aldri datoer før 'today'. Logger alle endringer i 'changes'. Regenererer HTML.
"""
import os, sys, json, datetime
import stampa_lib as L

def main(path):
    scrape = json.load(open(path, encoding="utf-8"))
    today = scrape["today"]
    frm = max(scrape["from"], today)
    to = scrape["to"]
    fresh = set()
    for v, d, r, t, s, e in scrape["bookings"]:
        if d >= today:
            fresh.add((v, d, r, t, s, e))

    conn = L.connect(fresh=False)
    run = datetime.datetime.now().isoformat(timespec="seconds")
    cur = conn.execute("SELECT venue,date,resource,tenant,start,slutt FROM bookings WHERE date>=? AND date<=?", (frm, to))
    existing = set(tuple(r) for r in cur.fetchall())

    added = fresh - existing
    removed = existing - fresh

    for row in sorted(removed):
        conn.execute("DELETE FROM bookings WHERE venue=? AND date=? AND resource=? AND start=? AND tenant=?",
                     (row[0], row[1], row[2], row[4], row[3]))
        conn.execute("INSERT INTO changes(run_ts,change_type,venue,date,resource,tenant,start,slutt) VALUES(?,?,?,?,?,?,?,?)",
                     (run, "fjernet", *row))
    for row in sorted(added):
        conn.execute("INSERT OR REPLACE INTO bookings(venue,date,resource,tenant,start,slutt) VALUES(?,?,?,?,?,?)", row)
        conn.execute("INSERT INTO changes(run_ts,change_type,venue,date,resource,tenant,start,slutt) VALUES(?,?,?,?,?,?,?,?)",
                     (run, "lagt til", *row))

    L.set_meta(conn, "sist_oppdatert", run)
    L.set_meta(conn, "sist_vindu", frm + ".." + to)
    conn.commit()
    L.sync_db()
    rows, ne, ns = L.rebuild_html(conn, today=today)
    conn.close()

    def fmt(r):
        vn = "Eidsiva" if r[0] == "eid" else "Stampesletta"
        return "  [" + vn + "] " + r[1] + " " + r[4] + "-" + r[5] + " " + r[2] + " - " + r[3]
    print("Kjoring", run)
    print("Vindu:", frm, "..", to)
    print("Lagt til:", len(added), " | Fjernet:", len(removed))
    if added:
        print("Nye bookinger:")
        for r in sorted(added): print(fmt(r))
    if removed:
        print("Fjernede bookinger:")
        for r in sorted(removed): print(fmt(r))
    if not added and not removed:
        print("Ingen endringer.")
    print("HTML regenerert.", rows, "bookinger totalt i DB.")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "scrape.json")

"""Bygger SQLite-databasen fra det opprinnelige uttrekket (stampakalender_2026.json)."""
import os, json, datetime
import stampa_lib as L

HERE = os.path.dirname(os.path.abspath(__file__))
src = json.load(open(os.path.join(HERE, "stampakalender_2026.json"), encoding="utf-8"))

conn = L.connect(fresh=True)
run = datetime.datetime.now().isoformat(timespec="seconds")
for vkey, vid in (("eid", "eidsiva"), ("stamp", "stampesletta")):
    for date, liste in src["lokasjoner"][vid]["dager"].items():
        for b in liste:
            conn.execute(
                "INSERT OR IGNORE INTO bookings(venue,date,resource,tenant,start,slutt) VALUES(?,?,?,?,?,?)",
                (vkey, date, b["ressurs"], b["leietaker"], b["fra"], b["til"]))
n = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
L.set_meta(conn, "sist_full_import", run)
L.set_meta(conn, "kilde", src.get("kilde", ""))
conn.commit()
L.sync_db()
rows, ne, ns = L.rebuild_html(conn, today=datetime.date.today().isoformat())
conn.close()
print("DB bygget:", n, "bookinger. HTML:", rows, "rader,", ne, "eid-dager,", ns, "stamp-dager.")

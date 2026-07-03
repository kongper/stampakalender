"""Delte hjelpefunksjoner for Stampakalender.

Prosjektmappen er en montert (FUSE) mappe der SQLite ikke kan operere direkte,
og der shutil.copy (chmod) og enkelte skrivinger feiler. Vi jobber derfor mot en
lokal arbeidskopi i /tmp og byte-kopierer .db/.html tilbake til prosjektmappen.
"""
import os, json, sqlite3, datetime

PROJECT_DIR = os.environ.get("STAMPA_PROJECT", os.path.dirname(os.path.abspath(__file__)))
WORK_DIR = os.environ.get("STAMPA_WORK", "/tmp/stampa")
os.makedirs(WORK_DIR, exist_ok=True)

DB_PROJECT = os.path.join(PROJECT_DIR, "stampakalender.db")
DB_WORK = os.path.join(WORK_DIR, "stampakalender.db")
TEMPLATE_PATH = os.path.join(PROJECT_DIR, "template.html")
HTML_PROJECT = os.path.join(PROJECT_DIR, "index.html")
HTML_WORK = os.path.join(WORK_DIR, "index.html")

RES_EID = ["Idrettshall, vest- basishall","Idrettshall, øst","Ishall","Garderobe 3","Garderobe 4","Garderobe 5","Garderobe 6","Garderobe 7","Garderobe 8","Garderobe Dommere","Garderobe Vest","Ungdomshallen","Uhall - ishall","Uhall - garderobe 1","Uhall - garderobe 2","Uhall - garderobe 3","Uhall - garderobe 4","Uhall - garderobe 5","Uhall - garderobe 6"]
RES_STAMP = ["Garderobe Nord","Garderobe Syd","Søndre Bane Nord","Søndre bane Sør","Øvre Bane Nord","Øvre bane Sør","Nedre Bane","Vestre Bane","Nordre Grus","Treningssletta","Parkeringsareal","Røyslimoen Nord","Røyslimoen Sør","Røyslimoen 7er"]
STENGT = {"eidsiva": {"fra": "2026-06-30", "til": "2026-08-02", "beskrivelse": "Stengt LK (sommerstengt/vedlikehold) hele dagen, alle ressurser"}}
KEYS = {"eid": "DF518BE1-E922-42C6-B381-C3B559EC32CC", "stamp": "914067A6-3198-44FB-81E6-F8B0F37BA427"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings(
  venue TEXT NOT NULL, date TEXT NOT NULL, resource TEXT NOT NULL,
  tenant TEXT NOT NULL, start TEXT NOT NULL, slutt TEXT NOT NULL,
  PRIMARY KEY(venue, date, resource, start, tenant)
);
CREATE TABLE IF NOT EXISTS changes(
  run_ts TEXT NOT NULL, change_type TEXT NOT NULL,
  venue TEXT, date TEXT, resource TEXT, tenant TEXT, start TEXT, slutt TEXT
);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(date);
"""

def _bytecopy(src, dst):
    with open(src, "rb") as f, open(dst, "wb") as g:
        g.write(f.read())

def connect(fresh=False):
    if os.path.exists(DB_WORK):
        try: os.remove(DB_WORK)
        except OSError: pass
    if not fresh and os.path.exists(DB_PROJECT) and os.path.getsize(DB_PROJECT) > 0:
        try:
            _bytecopy(DB_PROJECT, DB_WORK)
            sqlite3.connect(DB_WORK).execute("SELECT 1 FROM sqlite_master LIMIT 1")
        except Exception:
            try: os.remove(DB_WORK)
            except OSError: pass
    conn = sqlite3.connect(DB_WORK)
    conn.execute("PRAGMA journal_mode=MEMORY")
    conn.executescript(SCHEMA)
    return conn

def sync_db():
    _bytecopy(DB_WORK, DB_PROJECT)

def set_meta(conn, key, value):
    conn.execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

def rebuild_html(conn, today=None):
    if today is None:
        today = datetime.date.today().isoformat()
    rows = conn.execute("SELECT venue,date,resource,tenant,start,slutt FROM bookings").fetchall()
    tenants = sorted({r[3] for r in rows})
    tidx = {n: i for i, n in enumerate(tenants)}
    def ridx(venue, res):
        arr = RES_EID if venue == "eid" else RES_STAMP
        if res not in arr:
            arr.append(res)
        return arr.index(res)
    eid, stamp = {}, {}
    for venue, date, resource, tenant, start, slutt in rows:
        entry = [ridx(venue, resource), tidx[tenant], start, slutt]
        (eid if venue == "eid" else stamp).setdefault(date, []).append(entry)
    for d in eid: eid[d].sort(key=lambda e: (e[2], e[0]))
    for d in stamp: stamp[d].sort(key=lambda e: (e[2], e[0]))
    DATA = {"navn": tenants, "resEid": RES_EID, "resStamp": RES_STAMP,
            "stengt": STENGT, "eid": eid, "stamp": stamp}
    tpl = open(TEMPLATE_PATH, encoding="utf-8").read()
    out = tpl.replace("__DATA__", json.dumps(DATA, ensure_ascii=False, separators=(",", ":")))
    out = out.replace("__TODAY__", today)
    open(HTML_WORK, "w", encoding="utf-8").write(out)
    _bytecopy(HTML_WORK, HTML_PROJECT)
    return len(rows), len(eid), len(stamp)
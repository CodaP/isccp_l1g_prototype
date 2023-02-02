import sqlite3
from utils import SAT_NAMES, WMO_IDS, ALL_BANDS
from pathlib import Path
from contextlib import contextmanager
import yaml
from tqdm import tqdm

DATABASE = Path('db.sqlite3')
NONNFS_ROOT = Path('/data/cphillips/isccp-ng/')
SEARCH_LOCATIONS = Path('search_locations.yml')


def delete_db():
    # if the symlink exists
    if DATABASE.exists():
        # resolve
        real_file = DATABASE.resolve()
        # delete the symlink
        DATABASE.unlink()
        # delete the real file if it exists
        if real_file.exists():
            real_file.unlink()


@contextmanager
def get_connection():
    if not DATABASE.exists():
        # we don't want to use the NFS for the database
        real_file = NONNFS_ROOT / DATABASE.name
        # create a symlink to the real file
        DATABASE.symlink_to(real_file)
    conn = sqlite3.connect(DATABASE)
    try:
        yield conn
    finally:
        conn.close()


def create_tables(conn):
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS l1b_files
        (file_id INTEGER PRIMARY KEY,
        path TEXT,
        platform_id INTEGER REFERENCES platforms(platform_id),
        filename_time1 TEXT,
        filename_time2 TEXT,
        UNIQUE(path)
        )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS platforms
        (platform_id INTEGER PRIMARY KEY,
        platform_name TEXT,
        short_name TEXT,
        wmo_id INTEGER,
        UNIQUE(platform_name),
        UNIQUE(short_name),
        UNIQUE(wmo_id)
        )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS time_slots
        (time_slot_id INTEGER PRIMARY KEY,
        time_window_start INTEGER,
        time_window_end INTEGER,
        UNIQUE(time_window_start, time_window_end)
        )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS time_map
        (time_map_id INTEGER PRIMARY KEY,
        file_id INTEGER REFERENCES l1b_files(file_id),
        time_slot_id INTEGER REFERENCES time_slots(time_slot_id),
        UNIQUE(file_id, time_slot_id)
        )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS bands
        (band_id INTEGER PRIMARY KEY,
        band_name TEXT,
        UNIQUE(band_name)
        )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS band_map
        (band_map_id INTEGER PRIMARY KEY,
        file_id INTEGER REFERENCES l1b_files(file_id),
        band_id INTEGER REFERENCES bands(band_id),
        UNIQUE(file_id, band_id)
    )
    """)

def init_platforms(conn):
    c = conn.cursor()
    for short_name, platform_name in SAT_NAMES.items():
        wmo_id = WMO_IDS[short_name]
        c.execute("""
        INSERT INTO platforms (platform_name, short_name, wmo_id)
        VALUES (?, ?, ?)
        """, (platform_name, short_name, wmo_id))
    conn.commit()


def init_bands(conn):
    c = conn.cursor()
    for band_name in ALL_BANDS:
        c.execute("""
        INSERT INTO bands (band_name)
        VALUES (?)
        """, (band_name,))
    conn.commit()


def load_search_locations():
    with open(SEARCH_LOCATIONS, 'r') as f:
        return yaml.load(f, yaml.SafeLoader)


def all_files(search_locations):
    for root in search_locations:
        glob = search_locations[root]['glob']
        for path in Path(root).glob(glob):
            yield path


def test():
    delete_db()
    with get_connection() as conn:
        create_tables(conn)
        init_platforms(conn)
        init_bands(conn)

    search_locations = load_search_locations()
    with get_connection() as conn:
        c = conn.cursor()
        # turn off fsync
        c.execute('PRAGMA synchronous = OFF')
        inserted = 0
        with tqdm(all_files(search_locations)) as bar:
            for path in bar:
                c.execute("""
                INSERT INTO l1b_files (path)
                VALUES (?)
                ON CONFLICT DO NOTHING
                """, (str(path),))
                inserted += c.rowcount
                bar.set_description(f'Inserted {inserted} files')
                conn.commit()

if __name__ == '__main__':
    test()

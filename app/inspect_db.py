import sqlite3

DB_PATH = "app.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("\nInspecting database:", DB_PATH)
print("-" * 60)

# List all tables
tables = cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
).fetchall()

if not tables:
    print("No tables found.")
else:
    print("Tables found:")
    for t in tables:
        print(" -", t[0])

# Inspect each table
for (table_name,) in tables:
    print("\n" + "=" * 60)
    print("TABLE:", table_name)
    print("=" * 60)

    # Show columns
    cols = cur.execute(f"PRAGMA table_info({table_name});").fetchall()
    col_names = [c[1] for c in cols]

    print("Columns:")
    for c in col_names:
        print(" -", c)

    # Show rows
    rows = cur.execute(f"SELECT * FROM {table_name};").fetchall()

    if not rows:
        print("\n(no rows)")
    else:
        print("\nRows:")
        for r in rows:
            print(r)

print("\nInspection complete.")
conn.close()
import os
import time
import socket
import psycopg2
import psycopg2.extras
from flask import Flask, request, redirect, jsonify

app = Flask(__name__)

DB_HOST = os.environ.get("DB_HOST", "postgres-service")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "bookstore")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")

SEED_BOOKS = [
    ("The Hobbit", "J.R.R. Tolkien", 1937, "Fantasy"),
    ("Dune", "Frank Herbert", 1965, "Sci-Fi"),
    ("1984", "George Orwell", 1949, "Dystopian"),
    ("The Pragmatic Programmer", "Andrew Hunt", 1999, "Tech"),
    ("Clean Code", "Robert C. Martin", 2008, "Tech"),
    ("Sapiens", "Yuval Noah Harari", 2011, "Non-fiction"),
]


def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD, connect_timeout=5,
    )


def wait_for_db(max_retries=30, delay=2):
    """Retry loop so the app tolerates the DB pod starting a bit later."""
    for attempt in range(1, max_retries + 1):
        try:
            conn = get_connection()
            conn.close()
            print(f"DB reachable after {attempt} attempt(s).")
            return
        except Exception as e:
            print(f"[{attempt}/{max_retries}] DB not ready yet: {e}")
            time.sleep(delay)
    raise RuntimeError("Database never became reachable.")


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            genre TEXT
        );
    """)
    cur.execute("SELECT COUNT(*) FROM books;")
    count = cur.fetchone()[0]
    if count == 0:
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO books (title, author, year, genre) VALUES %s",
            SEED_BOOKS,
        )
        print(f"Seeded {len(SEED_BOOKS)} books.")
    conn.commit()
    cur.close()
    conn.close()


@app.route("/")
def home():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, author, year, genre FROM books ORDER BY id;")
    books = cur.fetchall()
    cur.close()
    conn.close()

    rows = "".join(
        f"<tr><td>{b[0]}</td><td>{b[1]}</td><td>{b[2]}</td><td>{b[3]}</td><td>{b[4]}</td>"
        f"<td><form method='POST' action='/delete/{b[0]}' style='margin:0'>"
        f"<button type='submit'>Delete</button></form></td></tr>"
        for b in books
    )

    return f"""
    <html>
    <head>
      <title>Bookstore Inventory</title>
      <style>
        body {{ font-family: sans-serif; max-width: 720px; margin: 40px auto; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        th {{ background: #f4f4f4; }}
        form.add-form input {{ margin: 4px; padding: 6px; }}
        .meta {{ color: #666; font-size: 0.9em; }}
      </style>
    </head>
    <body>
      <h1>Bookstore Inventory</h1>
      <p class="meta">Served by pod: <b>{socket.gethostname()}</b> - data from Postgres ({DB_HOST})</p>

      <h3>Add a book</h3>
      <form class="add-form" method="POST" action="/add">
        <input type="text" name="title" placeholder="Title" required>
        <input type="text" name="author" placeholder="Author" required>
        <input type="number" name="year" placeholder="Year">
        <input type="text" name="genre" placeholder="Genre">
        <button type="submit">Add</button>
      </form>

      <table>
        <tr><th>ID</th><th>Title</th><th>Author</th><th>Year</th><th>Genre</th><th></th></tr>
        {rows}
      </table>
    </body>
    </html>
    """


@app.route("/add", methods=["POST"])
def add_book():
    title = request.form.get("title")
    author = request.form.get("author")
    year = request.form.get("year") or None
    genre = request.form.get("genre")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO books (title, author, year, genre) VALUES (%s, %s, %s, %s);",
        (title, author, year, genre),
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")


@app.route("/delete/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM books WHERE id = %s;", (book_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")


@app.route("/api/books")
def api_books():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, author, year, genre FROM books ORDER BY id;")
    books = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([
        {"id": b[0], "title": b[1], "author": b[2], "year": b[3], "genre": b[4]}
        for b in books
    ])


@app.route("/healthz")
def health():
    try:
        conn = get_connection()
        conn.close()
        return {"status": "ok", "db": "reachable"}, 200
    except Exception as e:
        return {"status": "error", "db": str(e)}, 500


if __name__ == "__main__":
    wait_for_db()
    init_db()
    app.run(host="0.0.0.0", port=5000)

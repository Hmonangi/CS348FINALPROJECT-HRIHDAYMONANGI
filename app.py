import streamlit as st
import sqlite3
import pandas as pd

conn = sqlite3.connect("tvshows.db", check_same_thread=False)
cursor = conn.cursor()

def create_tables():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TV_Shows (
        show_id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie TEXT,
        runtime INTEGER,
        certificate TEXT,
        description TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Ratings (
        rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
        show_id INTEGER,
        rating REAL,
        votes INTEGER,
        FOREIGN KEY(show_id) REFERENCES TV_Shows(show_id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Genres (
        genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
        genre_name TEXT UNIQUE
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Show_Genres (
        show_id INTEGER,
        genre_id INTEGER,
        FOREIGN KEY(show_id) REFERENCES TV_Shows(show_id),
        FOREIGN KEY(genre_id) REFERENCES Genres(genre_id)
    )
    """)
    conn.commit()
create_tables()
#Creation of the Indexes
def create_indexes():
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idxrating
        ON Ratings(rating)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idxratingsshow
        ON Ratings(show_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idxgenre
        ON Show_Genres(genre_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idxgenreshow
        ON Show_Genres(show_id)
    """)
    conn.commit()
create_indexes()
def load_data():
    df = pd.read_csv("IMBD.csv")
    for _, row in df.iterrows():
        movie = str(row.get("movie", "Unknown")).strip()
        runtime_raw = str(row.get("runtime", "0"))
        runtime = 0
        if "min" in runtime_raw:
            try:
                runtime = int(runtime_raw.replace("min", "").strip())
            except:
                runtime = 0
        certificate = str(row.get("certificate", "Unknown"))
        description = str(row.get("description", ""))
        rating = row.get("rating")
        rating = float(rating) if pd.notna(rating) else 0
        votes_raw = str(row.get("votes", "0")).replace(",", "")
        try:
            votes = int(votes_raw)
        except:
            votes = 0
        cursor.execute("""
            INSERT INTO TV_Shows (movie, runtime, certificate, description)
            VALUES (?, ?, ?, ?)
        """, (movie, runtime, certificate, description))
        show_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO Ratings (show_id, rating, votes)
            VALUES (?, ?, ?)
        """, (show_id, rating, votes))
        genre_raw = str(row.get("genre", "Unknown"))
        genre = genre_raw.split(",")[0].strip()
        cursor.execute("""
            INSERT OR IGNORE INTO Genres (genre_name)
            VALUES (?)
        """, (genre,))
        genre_id = cursor.execute("""
            SELECT genre_id FROM Genres WHERE genre_name = ?
        """, (genre,)).fetchone()[0]
        cursor.execute("""
            INSERT INTO Show_Genres (show_id, genre_id)
            VALUES (?, ?)
        """, (show_id, genre_id))
    conn.commit()
if cursor.execute("SELECT COUNT(*) FROM TV_Shows").fetchone()[0] == 0:
    load_data()
st.title("📺 IMDb TV Shows App (Stage 3)")


genres = cursor.execute("SELECT genre_id, genre_name FROM Genres").fetchall()
genre_dict = {name: gid for gid, name in genres}
tab1, tab2, tab3 = st.tabs(["📋 Current Database", "⚙️ Manage Shows", "📊 Reports"])

with tab1:
    st.subheader("📋 Current Shows in Database")
    shows = cursor.execute("""
    SELECT t.show_id, t.movie, r.rating, t.runtime, g.genre_name
    FROM TV_Shows t
    JOIN Ratings r ON t.show_id = r.show_id
    LEFT JOIN Show_Genres sg ON t.show_id = sg.show_id
    LEFT JOIN Genres g ON sg.genre_id = g.genre_id
    ORDER BY t.show_id DESC
    """).fetchall()
    df_shows = pd.DataFrame(shows, columns=[
        "Show ID", "Movie", "Rating", "Runtime", "Genre"
    ])
    st.dataframe(df_shows)

with tab2:
    st.subheader("➕ Add New Show")
    movie = st.text_input("Movie Title")
    runtime = st.number_input("Runtime (minutes)", 0, 300)
    certificate = st.text_input("Certificate")
    rating = st.slider("Rating", 0.0, 10.0, 5.0)
    votes = st.number_input("Votes", 0)
    description = st.text_area("Description")
    selected_genre = st.selectbox("Genre", list(genre_dict.keys()))
    if st.button("Add Show"):
        if not movie:
            st.error("Movie title is required")
        else:
            try:
                conn.execute("BEGIN")
#Injections
                cursor.execute("""
                    INSERT INTO TV_Shows (movie, runtime, certificate, description)
                    VALUES (?, ?, ?, ?)
                """, (movie, runtime, certificate, description))
                show_id = cursor.lastrowid
#Injections
                cursor.execute("""
                    INSERT INTO Ratings (show_id, rating, votes)
                    VALUES (?, ?, ?)
                """, (show_id, rating, votes))
#Injections
                cursor.execute("""
                    INSERT INTO Show_Genres (show_id, genre_id)
                    VALUES (?, ?)
                """, (show_id, genre_dict[selected_genre]))
#Transcation
                conn.commit()
                st.success("Show added!")
            except Exception as e:
                conn.rollback()
                st.error(f"Transaction failed: {e}")
            st.rerun()
    st.subheader("✏️ Update Rating")
    show_ids = [row[0] for row in cursor.execute("SELECT show_id FROM TV_Shows").fetchall()]
    selected_id = st.selectbox("Select Show ID", show_ids)
    new_rating = st.slider("New Rating", 0.0, 10.0, 5.0, key="update")
    if st.button("Update"):
#Injection
        cursor.execute("""
            UPDATE Ratings
            SET rating = ?
            WHERE show_id = ?
        """, (new_rating, selected_id))
#Transcation
        conn.commit()
        st.success("Updated!")
        st.rerun()
    st.divider()
    st.subheader("❌ Delete Show")
    delete_id = st.selectbox("Select ID to Delete", show_ids, key="delete")
    if st.button("Delete"):
        try:
            conn.execute("BEGIN")
            cursor.execute("DELETE FROM TV_Shows WHERE show_id = ?", (delete_id,))
            cursor.execute("DELETE FROM Ratings WHERE show_id = ?", (delete_id,))
            cursor.execute("DELETE FROM Show_Genres WHERE show_id = ?", (delete_id,))
            conn.commit()
            st.success("Deleted!")
        except Exception as e:
            conn.rollback()
            st.error(f"Delete failed: {e}")
        st.rerun()


with tab3:
    st.subheader("📊 Filter & Analyze Data")
    min_rating = st.slider("Min Rating", 0.0, 10.0, 0.0)
    max_rating = st.slider("Max Rating", 0.0, 10.0, 10.0)
    selected_genre_report = st.selectbox("Genre", list(genre_dict.keys()), key="report")
#Use of Index
    query = """
    SELECT t.movie, r.rating, t.runtime, g.genre_name
    FROM TV_Shows t
    JOIN Ratings r ON t.show_id = r.show_id
    JOIN Show_Genres sg ON t.show_id = sg.show_id
    JOIN Genres g ON sg.genre_id = g.genre_id
    WHERE r.rating BETWEEN ? AND ?
    AND g.genre_id = ?
    ORDER BY r.rating DESC
    LIMIT 200
    """
    results = cursor.execute(
        query,
        (min_rating, max_rating, genre_dict[selected_genre_report])
    ).fetchall()
    df_results = pd.DataFrame(results, columns=[
        "Movie", "Rating", "Runtime", "Genre"
    ])
    st.dataframe(df_results)
    st.divider()
    st.subheader("📊 Statistics")
#Use of Index
    avg_rating = cursor.execute("""
    SELECT AVG(rating) FROM Ratings
    WHERE rating BETWEEN ? AND ?
    """, (min_rating, max_rating)).fetchone()[0]
    count = cursor.execute("""
    SELECT COUNT(*) FROM Ratings
    WHERE rating BETWEEN ? AND ?
    """, (min_rating, max_rating)).fetchone()[0]
    st.write(f"Average Rating: {avg_rating}")
    st.write(f"Total Shows: {count}")

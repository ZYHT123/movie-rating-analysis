from pymongo import MongoClient
import pandas as pd
import math

# -----------------------------
# 1. Connect to MongoDB
# Local MongoDB connection settings
# -----------------------------
MONGO_URI = "mongodb://localhost:27017"
DATABASE_NAME = "movie_rating_analysis"
COLLECTION_NAME = "movies"

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
movies_col = db[COLLECTION_NAME]

#check if connection is successful
try:
    client.admin.command("ping")
    print("Connected successfully")
except Exception as e:
    print("Connection failed:", e)
# -----------------------------
# 2. Load cleaned CSV files
# -----------------------------
movies_df = pd.read_csv("movies.csv")
links_df = pd.read_csv("links.csv")
imdb_basics_df = pd.read_csv("imdb_basics.csv")
imdb_ratings_df = pd.read_csv("imdb_ratings.csv")
tmdb_df = pd.read_csv("tmdb_metadata.csv")
ml_ratings_df = pd.read_csv("ML_ratings.csv")
ml_tags_df = pd.read_csv("ML_tags.csv")

# -----------------------------
# 3. Helper functions
# -----------------------------
def split_genres(value):
    """
    Convert pipe-separated genre string into a list.
    Example: 'Comedy|Drama' -> ['Comedy', 'Drama']
    """
    if pd.isna(value) or value == "(no genres listed)":
        return []
    return [g.strip() for g in str(value).split("|") if g.strip()]

def clean_value(value):
    """
    Convert pandas/numpy values to standard Python values.
    Replace NaN with None so MongoDB can store them properly.
    """
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value

def clean_int(value):
    value = clean_value(value)
    return int(value) if value is not None else None

def clean_float(value):
    value = clean_value(value)
    return float(value) if value is not None else None

# -----------------------------
# 4. Aggregate MovieLens ratings
# -----------------------------
ml_rating_summary = (
    ml_ratings_df
    .groupby("movieId")
    .agg(
        avg_rating=("rating", "mean"),
        rating_count=("rating", "count")
    )
    .reset_index()
)

# -----------------------------
# 5. Aggregate MovieLens tags
# -----------------------------
ml_tags_clean = ml_tags_df.dropna(subset=["tag"]).copy()
ml_tags_clean["tag"] = ml_tags_clean["tag"].astype(str).str.strip()

ml_tag_summary = (
    ml_tags_clean
    .groupby("movieId")
    .agg(
        tags=("tag", lambda x: sorted(set(tag for tag in x if tag))),
        tag_count=("tag", lambda x: len(set(tag for tag in x if tag)))
    )
    .reset_index()
)

# -----------------------------
# 6. Merge all movie-level data
# -----------------------------
merged_df = (
    movies_df
    .merge(links_df, on="movieId", how="left")
    .merge(imdb_basics_df, on="tconst", how="left")
    .merge(imdb_ratings_df, on="tconst", how="left")
    .merge(tmdb_df, left_on="tmdbId", right_on="tmdb_id", how="left")
    .merge(ml_rating_summary, on="movieId", how="left")
    .merge(ml_tag_summary, on="movieId", how="left")
)

# -----------------------------
# 7. Fill missing tag fields
# -----------------------------
merged_df["tags"] = merged_df["tags"].apply(
    lambda x: x if isinstance(x, list) else []
)
merged_df["tag_count"] = merged_df["tag_count"].fillna(0).astype(int)

# -----------------------------
# 8. Choose release year
# -----------------------------
# Prefer TMDB release_year if available, otherwise IMDb start_year
merged_df["releaseYear"] = merged_df["release_year"].combine_first(merged_df["start_year"])

merged_df = merged_df.dropna(subset=["releaseYear"])
merged_df = merged_df[
    (merged_df["releaseYear"] >= 2020) & (merged_df["releaseYear"] <= 2025)
]

# -----------------------------
# 9. Compute derived metrics
# -----------------------------
merged_df["alignment"] = merged_df["imdb_avg_rating"] - merged_df["avg_rating"]
merged_df["disagreement"] = merged_df["alignment"].abs()

# -----------------------------
# 10. Build MongoDB documents
# Each document represents one movie and embeds related
# IMDb, TMDB, and MovieLens data to reduce the need for joins.
# -----------------------------
documents = []

for _, row in merged_df.iterrows():
    doc = {
        "movieId": clean_int(row["movieId"]),
        "title": clean_value(row["title"]),
        "releaseYear": clean_int(row["releaseYear"]),
        "genres": split_genres(row["genres"]),

        "external_ids": {
            "tconst": clean_value(row["tconst"]),
            "tmdbId": clean_int(row["tmdbId"])
        },

        "imdb": {
            "avg_rating": clean_float(row["imdb_avg_rating"]),
            "num_votes": clean_int(row["imdb_num_votes"])
        },

        "tmdb": {
            "vote_average": clean_float(row["tmdb_vote_average"]),
            "vote_count": clean_int(row["tmdb_vote_count"])
        },

        "movielens": {
            "avg_rating": clean_float(row["avg_rating"]),
            "rating_count": clean_int(row["rating_count"]),
            "tags": row["tags"],
            "tag_count": clean_int(row["tag_count"])
        },

        "derived_metrics": {
            "alignment": clean_float(row["alignment"]),
            "disagreement": clean_float(row["disagreement"])
        }
    }

    documents.append(doc)

# -----------------------------
# 11. Insert into MongoDB
# -----------------------------
movies_col.delete_many({})

if documents:
    movies_col.insert_many(documents)

# -----------------------------
# 12. Add indexes
# -----------------------------
movies_col.create_index("movieId", unique=True)
movies_col.create_index("external_ids.tconst")
movies_col.create_index("releaseYear")
movies_col.create_index("genres")
movies_col.create_index("derived_metrics.disagreement")

print(f"Inserted {movies_col.count_documents({})} documents into the '{COLLECTION_NAME}' collection.")
print("Sample document:")
print(movies_col.find_one({}, {"_id": 0}))

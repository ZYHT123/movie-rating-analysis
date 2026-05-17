DROP TABLE ML_TAGS PURGE;
DROP TABLE ML_RATINGS PURGE;
DROP TABLE LINKS PURGE;
DROP TABLE IMDB_RATINGS PURGE;
DROP TABLE IMDB_BASICS PURGE;
DROP TABLE TMDB_METADATA PURGE;
DROP TABLE MOVIES PURGE;

CREATE TABLE MOVIES (
    movieId NUMBER PRIMARY KEY,
    title VARCHAR2(300) NOT NULL,
    genres VARCHAR2(300)
);

CREATE TABLE IMDB_BASICS (
    tconst VARCHAR2(20) PRIMARY KEY,
    imdb_title VARCHAR2(300),
    start_year NUMBER,
    imdb_genres VARCHAR2(300)
);

CREATE TABLE IMDB_RATINGS (
    tconst VARCHAR2(20) PRIMARY KEY,
    imdb_avg_rating NUMBER,
    imdb_num_votes NUMBER,
    CONSTRAINT fk_imdb_rating
        FOREIGN KEY (tconst) REFERENCES IMDB_BASICS(tconst)
);

CREATE TABLE TMDB_METADATA (
    tmdb_id NUMBER PRIMARY KEY,
    imdb_id VARCHAR2(20),
    tmdb_title VARCHAR2(300),
    release_year NUMBER,
    tmdb_genres VARCHAR2(300),
    tmdb_vote_average NUMBER,
    tmdb_vote_count NUMBER,
    CONSTRAINT fk_tmdb_imdb
        FOREIGN KEY (imdb_id) REFERENCES IMDB_BASICS(tconst)
);

CREATE TABLE LINKS (
    movieId NUMBER PRIMARY KEY,
    tconst VARCHAR2(20) NOT NULL,
    tmdbId NUMBER,
    CONSTRAINT fk_links_movie
        FOREIGN KEY (movieId) REFERENCES MOVIES(movieId),
    CONSTRAINT fk_links_imdb
        FOREIGN KEY (tconst) REFERENCES IMDB_BASICS(tconst),
    CONSTRAINT fk_links_tmdb
        FOREIGN KEY (tmdbId) REFERENCES TMDB_METADATA(tmdb_id)
);

CREATE TABLE ML_RATINGS (
    movieId NUMBER,
    rating NUMBER,
    CONSTRAINT pk_ml_ratings PRIMARY KEY (movieId, rating),
    CONSTRAINT fk_ml_rating_movie
        FOREIGN KEY (movieId) REFERENCES MOVIES(movieId)
);

CREATE TABLE ML_TAGS (
    movieId NUMBER,
    tag VARCHAR2(300),
    CONSTRAINT pk_ml_tags PRIMARY KEY (movieId, tag),
    CONSTRAINT fk_ml_tag_movie
        FOREIGN KEY (movieId) REFERENCES MOVIES(movieId)
);

COMMIT;
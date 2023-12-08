import os
import psycopg2
import config

connection = None


async def setup_database():
    global connection
    connection = psycopg2.connect(host=config.host, database=os.getenv("db_name"), password=os.getenv("db_pass"),
                                  user=os.getenv("db_user"), port=os.getenv("db_port"))
    connection.autocommit = True

    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        print("Server version:", cursor.fetchone())

    with connection.cursor() as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS users ("
                       "user_id SERIAL PRIMARY KEY, "
                       "username VARCHAR(32) NOT NULL, "
                       "language VARCHAR(5), "
                       " reg_date DATE, "
                       "update_date DATE);")
        print("Table 'users' created successfully")

    with connection.cursor() as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS saved_movies ("
                       "user_id INT, "
                       "movie_id INT, "
                       "PRIMARY KEY (user_id, movie_id));")
        print("Table 'saved_movies' created successfully")

    with connection.cursor() as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS search_movie ("
                       "id SERIAL PRIMARY KEY, "
                       "user_id INT UNIQUE, "
                       "genre_id INT, "
                       "year_range VARCHAR(255) DEFAULT 'any', "
                       "user_rating VARCHAR(255) DEFAULT 'any', "
                       "rating VARCHAR(32) DEFAULT 'any');")
        print("Table 'search_movie' created successfully")


def get_user_language_from_db(user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT language FROM users WHERE user_id = %s;", (user_id,))
        result = cursor.fetchone()
        if result is not None:
            return result[0]
        else:
            return None


def get_saved_movies_from_db(user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM saved_movies WHERE user_id = %s;", (user_id,))
        return cursor.fetchall()


def get_filters_from_db(user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT genre_id, year_range, user_rating, rating FROM search_movie WHERE user_id = %s;", (user_id,))
        result = cursor.fetchone()
        if result is not None:
            return {
                'genre': result[0],
                'release_date': result[1],
                'user_rating': result[2],
                'rating': result[3]
            }
        else:
            return None

def reset_filters_in_db(user_id):
    with connection.cursor() as cursor:
        cursor.execute("UPDATE search_movie SET genre_id = NULL, year_range = NULL, user_rating = NULL, rating = NULL WHERE user_id = %s;", (user_id,))
        connection.commit()


def update_user_language_from_db(user_id, username, language):
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO users (user_id, username, language, reg_date, update_date) "
                       "VALUES (%s, %s, %s, CURRENT_DATE, CURRENT_DATE) "
                       "ON CONFLICT (user_id) DO UPDATE SET language = %s, update_date = CURRENT_DATE;",
                       (user_id, username, language, language))


def save_movie_to_db(user_id, movie_id):
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO saved_movies (user_id, movie_id) "
                       "VALUES (%s, %s) "
                       "ON CONFLICT (user_id, movie_id) DO NOTHING;", (user_id, movie_id))


def save_fields_to_table_search_movie_db(user_id, genre_id=None, year_range=None, user_rating=None, rating=None):
    connection.autocommit = True
    with connection.cursor() as cursor:
        update_fields = []
        update_values = []
        if genre_id is not None:
            update_fields.append("genre_id = %s")
            update_values.append(genre_id)
        if year_range is not None:
            update_fields.append("year_range = %s")
            update_values.append(year_range)
        if user_rating is not None:
            update_fields.append("user_rating = %s")
            update_values.append(user_rating)
        if rating is not None:
            update_fields.append("rating = %s")
            update_values.append(rating)
        update_clause = ", ".join(update_fields)
        cursor.execute(f"INSERT INTO search_movie (user_id, genre_id, year_range, user_rating, rating) "
                       f"VALUES (%s, %s, %s, %s, %s) "
                       f"ON CONFLICT (user_id) DO UPDATE SET {update_clause};",
                       [user_id, genre_id, year_range, user_rating, rating] + update_values)


def delete_movie_from_db(user_id, movie_id):
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM saved_movies WHERE user_id = %s AND movie_id = %s;", (user_id, movie_id))

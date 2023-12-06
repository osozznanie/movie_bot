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


def delete_movie_from_db(user_id, movie_id):
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM saved_movies WHERE user_id = %s AND movie_id = %s;", (user_id, movie_id))

import os
import psycopg2
import config

connection = None


def connect_to_database():
    global connection
    connection = psycopg2.connect(host=config.host, database=config.db_name, password=config.db_password,
                                  user=config.db_user, port=config.db_port)
    connection.autocommit = True

    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        print("Server version:", cursor.fetchone())


def create_users_table():
    with connection.cursor() as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS users ("
                       "user_id SERIAL PRIMARY KEY, "
                       "username VARCHAR(32) NOT NULL, "
                       "language VARCHAR(5), "
                       "reg_date DATE, "
                       "update_date DATE, "
                       "message_id INTEGER);")
        print("Table 'users' created successfully")


def store_message_id_in_db(user_id, message_id):
    with connection.cursor() as cursor:
        cursor.execute("UPDATE users SET message_id = %s WHERE user_id = %s", (message_id, user_id))
        connection.commit()


def get_message_id_from_db(user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT message_id FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None


def create_user_pages_table():
    with connection.cursor() as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS user_pages ("
                       "user_id INT PRIMARY KEY, "
                       "current_popular_page INT DEFAULT 1, "
                       "current_popular_movie INT DEFAULT 0, "
                       "current_rating_page INT DEFAULT 1, "
                       "current_rating_movie INT DEFAULT 0,"
                       "current_random_movie_page INT DEFAULT 1,"
                       "current_random_tv_page INT DEFAULT 1,"
                       'current_filter_movie_page INT DEFAULT 1,'
                       'current_filter_tv_page INT DEFAULT 1,'
                       'current_filter_movie_movie INT DEFAULT 0,'
                       'current_filter_tv_movie INT DEFAULT 0,'
                       "FOREIGN KEY (user_id) REFERENCES users(user_id));")
        print("Table 'user_pages' created successfully")


def create_saved_movies_table():
    with connection.cursor() as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS saved_movies ("
                       "user_id INT, "
                       "movie_id INT, "
                       "PRIMARY KEY (user_id, movie_id));")
        print("Table 'saved_movies' created successfully")


def create_search_movie_table():
    with connection.cursor() as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS search_movie ("
                       "id SERIAL PRIMARY KEY, "
                       "user_id INT UNIQUE, "
                       "genre_id INT, "
                       "year_range VARCHAR(255) DEFAULT 'any', "
                       "user_rating VARCHAR(255) DEFAULT 'any', "
                       "rating VARCHAR(32) DEFAULT 'any');")
        print("Table 'search_movie' created successfully")


def create_search_series_table():
    with connection.cursor() as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS search_series ("
                       "id SERIAL PRIMARY KEY, "
                       "user_id INT UNIQUE, "
                       "genre_id INT, "
                       "year_range VARCHAR(255) DEFAULT 'any', "
                       "user_rating VARCHAR(255) DEFAULT 'any', "
                       "rating VARCHAR(32) DEFAULT 'any');")
        print("Table 'search_series' created successfully")


def create_saved_series_table():
    with connection.cursor() as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS saved_series ("
                       "user_id INT, "
                       "series_id INT, "
                       "PRIMARY KEY (user_id, series_id));")
        print("Table 'saved_series' created successfully")


def save_series_to_db(user_id, series_id):
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO saved_series (user_id, series_id) "
                       "VALUES (%s, %s) "
                       "ON CONFLICT (user_id, series_id) DO NOTHING;", (user_id, series_id))


async def setup_database():
    connect_to_database()
    create_users_table()
    create_user_pages_table()
    create_saved_movies_table()
    create_search_movie_table()
    create_search_series_table()
    create_saved_series_table()


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
        cursor.execute("SELECT movie_id FROM saved_movies WHERE user_id = %s;", (user_id,))
        return cursor.fetchall()


def get_saved_series_from_db(user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT series_id FROM saved_series WHERE user_id = %s;", (user_id,))
        return cursor.fetchall()


def get_filters_movie_from_db(user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT genre_id, year_range, user_rating, rating FROM search_movie WHERE user_id = %s;",
                       (user_id,))
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


def get_filters_series_from_db(user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT genre_id, year_range, user_rating, rating FROM search_series WHERE user_id = %s;",
                       (user_id,))
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


def save_fields_to_table_search_series_db(user_id, genre_id=None, year_range=None, user_rating=None, rating=None):
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
        cursor.execute(f"INSERT INTO search_series (user_id, genre_id, year_range, user_rating, rating) "
                       f"VALUES (%s, %s, %s, %s, %s) "
                       f"ON CONFLICT (user_id) DO UPDATE SET {update_clause};",
                       [user_id, genre_id, year_range, user_rating, rating] + update_values)


def delete_movie_from_db(user_id, movie_id):
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM saved_movies WHERE user_id = %s AND movie_id = %s;", (user_id, movie_id))


def delete_tv_from_db(user_id, tv_id):
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM saved_series WHERE user_id = %s AND series_id = %s;", (user_id, tv_id))


def get_current_popular_by_user_id(user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_popular_page, current_popular_movie "
                       "FROM user_pages WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        return result


def get_filter_pages_and_movies_by_user_id(user_id):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_filter_movie_page, current_filter_tv_page, current_filter_movie_movie, current_filter_tv_movie "
            "FROM user_pages WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        return result


def get_filter_movie_page_movie_by_user_id(user_id):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_filter_movie_page, current_filter_movie_movie "
            "FROM user_pages WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        return result


def get_filter_series_page_movie_by_user_id(user_id):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_filter_tv_page, current_filter_tv_movie "
            "FROM user_pages WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        return result


def set_filter_pages_and_movies_by_user_id(user_id, movie_page, tv_page, movie_movie, tv_movie):
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE user_pages SET current_filter_movie_page = %s, current_filter_tv_page = %s, current_filter_movie_movie = %s, current_filter_tv_movie = %s "
            "WHERE user_id = %s", (movie_page, tv_page, movie_movie, tv_movie, user_id))
        connection.commit()


def set_filter_movie_page_movie_by_user_id(user_id, movie_page, movie_movie):
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE user_pages SET current_filter_movie_page = %s, current_filter_movie_movie = %s "
            "WHERE user_id = %s", (movie_page, movie_movie, user_id))
        connection.commit()


def set_filter_series_page_movie_by_user_id(user_id, movie_page, movie_movie):
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE user_pages SET current_filter_tv_page = %s, current_filter_tv_movie = %s "
            "WHERE user_id = %s", (movie_page, movie_movie, user_id))
        connection.commit()


def save_filter_pages_and_movies_by_user_id(user_id, current_movie, current_page):
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO user_pages (user_id, current_filter_movie_page, current_filter_movie_movie) "
            "VALUES (%s, %s, %s) "
            "ON CONFLICT (user_id) DO UPDATE SET current_filter_movie_page = EXCLUDED.current_filter_movie_page, "
            "current_filter_movie_movie = EXCLUDED.current_filter_movie_movie",
            (user_id, current_page, current_movie))
        connection.commit()


def get_current_rating_by_user_id(user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_rating_page, current_rating_movie "
                       "FROM user_pages WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        return result


def update_current_popular(user_id, current_popular_page, current_popular_movie):
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute("UPDATE user_pages SET current_popular_page = %s, current_popular_movie = %s WHERE user_id = %s",
                       (current_popular_page, current_popular_movie, user_id))


def update_current_rating(user_id, current_rating_page, current_rating_movie):
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute("UPDATE user_pages SET current_popular_page = %s, current_popular_movie = %s WHERE user_id = %s",
                       (current_rating_page, current_rating_movie, user_id))


async def get_current_page_random(user_id, page_type):
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {page_type} FROM user_pages WHERE user_id = %s", (user_id,))
        return cursor.fetchone()[0]


async def update_current_page_random(user_id, page_type):
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute(f"UPDATE user_pages SET {page_type} = {page_type} + 1 WHERE user_id = %s", (user_id,))


def update_user_pages_from_db(user_id):
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO user_pages (user_id) "
            "VALUES (%s) "
            "ON CONFLICT (user_id) DO NOTHING;",
            (user_id,))


def reset_filters_movie(user_id):
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE search_movie SET genre_id = NULL, year_range = NULL, user_rating = NULL, rating = NULL WHERE user_id = %s;",
            (user_id,))


def reset_filters_series(user_id):
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE search_series SET genre_id = NULL, year_range = NULL, user_rating = NULL, rating = NULL WHERE user_id = %s;",
            (user_id,))

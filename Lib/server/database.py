from sqlite3 import connect, Error as db_Error
from typing import Callable, Union


def safe_execution(func: Callable) -> Union[AssertionError, Callable]:
    """Catches the errors, if they occur while interacting with database.
    Use this function as a decorator for class methods."""
    def wrapper(*args, **kwargs):
        sql = args[1]
        try:
            return func(args[0], sql, kwargs)
        except TypeError as error:
            assert False, f"Failed to call {func} with {(args[0], sql, kwargs)}.\n" \
                          f"Function responded with '{error}'.\n" \
                          f"If you encountered this error, please contact us at defender0508@gmeail.com"
        except db_Error as error:
            assert False, f"Failed to call {func} with {(args[0], sql, kwargs)} - Error while interacting with \n" \
                          f"database: {error}. \n" \
                          f"If you encountered this error, please contact us at defender0508@gmeail.com"
    return wrapper


class DataBase:
    """Class for safely interacting with database."""
    def __init__(self) -> None:
        """Establishing database connection and creating a cursor object"""
        self.connection = connect('web_social.db', check_same_thread=False)
        self.cursor = self.connection.cursor()

    @safe_execution
    def get_information(self, sql: str, *args) -> tuple:
        """Returns a tuple containing one element"""
        return self.cursor.execute(sql).fetchone()

    @safe_execution
    def get_many(self, sql: str, *args) -> list:
        """Returns a list containing defined amount of tuples. Default amount= 1."""
        if args:
            size = args[0].get('size')
        else:
            size = 1
        return self.cursor.execute(sql).fetchmany(size)

    @safe_execution
    def get_all(self, sql: str, *args) -> list:
        """Get a list of tuples. Fetches all elements described in sql query."""
        return self.cursor.execute(sql).fetchall()

    @safe_execution
    def get_all_singles(self, sql: str, *args) -> list:
        """Get a list of any elements.
        Unlike get_all() this function returns unpacked values.
        They can still be tuples, if they are stored as tuples in database."""
        return [i[0] for i in self.cursor.execute(sql).fetchall()]

    @safe_execution
    def create(self, sql: str, *args) -> None:
        """Insert something in database"""
        self.cursor.execute(sql, args[0].get('data'))
        self.connection.commit()

    @safe_execution
    def update(self, sql: str, *args) -> None:
        """Update the database.
        You should give new values right in the sql query,
        not as key arguments when calling the function"""
        self.cursor.execute(sql)
        self.connection.commit()

    @safe_execution
    def delete(self, sql: str, *args) -> None:
        """Delete something in database"""
        self.cursor.execute(sql)
        self.connection.commit()
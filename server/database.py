from sqlite3 import connect, Error as db_Error
from enum import Enum
from typing import Callable, Union, Any


class NoPermission(PermissionError):
    def __init__(self, func: Callable, arguments: tuple):
        self.message = f"Failed to call {func} with {arguments} - No permission. \n" \
                       f"If you encountered this error, please contact us at defender0508@gmeail.com."

    def __str__(self):
        return self.message


class InternalError(TypeError):
    def __init__(self, func: Callable, arguments: tuple, error: TypeError):
        self.message = f"Failed to call {func} with {arguments}.\n" \
                       f"Function responded with '{error}'.\n" \
                       f"If you encountered this error, please contact us at defender0508@gmeail.com."

    def __str__(self):
        return self.message


class DataBaseInteractError(db_Error):
    def __init__(self, func: str, arguments: tuple, error: db_Error):
        self.message = f"Failed to call {func} method of {arguments[0]} with parameters {arguments[1:-1]}.\n" \
                       f"Error while interacting with database: {error}. \n" \
                       f"If you encountered this error, please contact us at defender0508@gmeail.com."

    def __str__(self):
        return self.message


class UnknownCommand(db_Error):
    def __init__(self, func: Callable, arguments: tuple):
        self.message = f'Failed to call {func} with request "{arguments}": The command you were trying to ' \
                       f'execute does not exist.\n' \
                       f'If you encountered this error, please contact us at defender0508@gmeail.com.'

    def __str__(self):
        return self.message


class AccessLevel(Enum):
    """Higher levels can also do actions of all the previous levels."""
    Browse = 1
    Create = 2
    Update = 3
    Delete = 4

    def __lt__(self, other):
        return self.value < other.value

    def __le__(self, other):
        return self.value <= other.value


operations_access_required = {'get_information': AccessLevel(1),
                              'get_many': AccessLevel(1),
                              'get_many_singles': AccessLevel(1),
                              'get_all': AccessLevel(1),
                              'get_all_singles': AccessLevel(1),
                              'create': AccessLevel(2),
                              'update': AccessLevel(3),
                              'delete': AccessLevel(4)}

operations_keywords = {AccessLevel(1): ['SELECT', 'COUNT'],
                       AccessLevel(2): ['CREATE'],
                       AccessLevel(3): ['UPDATE'],
                       AccessLevel(4): ['DELETE'],
                       'forbidden': ['DROP']}

operations_rev = {AccessLevel(1): ['CREATE', 'UPDATE', 'DELETE', 'DROP', 'PRAGMA'],
                  AccessLevel(2): ['UPDATE', 'DELETE', 'DROP', 'PRAGMA'],
                  AccessLevel(3): ['DELETE', 'DROP', 'PRAGMA'],
                  AccessLevel(4): ['DROP', 'PRAGMA', '']}

commands_dict = {'SELECT': AccessLevel(1),
                 'COUNT': AccessLevel(1),
                 'INSERT': AccessLevel(2),
                 'UPDATE': AccessLevel(3),
                 'DELETE': AccessLevel(4),
                 'CREATE': False,
                 'DROP': False,
                 'PRAGMA': False}


def safe_execution(func: Callable) -> Union[AssertionError, Callable]:
    """Catches the errors, if they occur while interacting with database.
    Ensures that given DataBase instance has enough rights to execute the sql query.
    Used as a decorator for class methods."""

    def wrapper(*args, **kwargs):
        if (access_level := args[0].get_access_level) >= \
                operations_access_required.get(f'{func}'.split(' ', 2)[1][9:]):
            sql = args[1]
            check_request(func, sql, access_level)
            try:
                return func(args[0], sql, kwargs)
            except TypeError as error:
                raise InternalError(func, (args, kwargs), error)
            except db_Error as error:
                raise DataBaseInteractError(f'{func}'.split(' ', 2)[1][9:], (args, kwargs), error)
        else:
            raise NoPermission(func, (args, kwargs))

    return wrapper


def check_request(func: Callable, request: str, access_level: AccessLevel):
    command = request.split()[0]
    if command in commands_dict:
        if not (op_ac_level := commands_dict.get(command)) or op_ac_level > access_level:
            raise NoPermission(func, (request,))
    else:
        raise UnknownCommand(func, (request, ))


class DataBase:
    """Class for safely interacting with database."""

    def __init__(self, database_name: str = 'web_social_v3.db', access_level: int = 1) -> None:
        """Establishing database connection and creating a cursor object"""
        self.connection = connect(database_name, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.access = AccessLevel(access_level)

    @safe_execution
    def get_information(self, sql: str, *args) -> Union[tuple, Any, None]:
        """Returns a tuple containing one element"""
        if result := self.cursor.execute(sql).fetchone():
            return result
        else:
            return args[0].get('default', None)

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
    def get_many_singles(self, sql: str, *args) -> list:
        """Returns a list containing defined amount of tuples. Default amount= 1."""
        if args:
            size = args[0].get('size')
        else:
            size = 1
        return [i[0] for i in self.cursor.execute(sql).fetchmany(size)]

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

    @property
    def get_access_level(self):
        return self.access

    def __setattr__(self, key, value):
        if hasattr(self, key):
            raise PermissionError('DataBase attributes cannot be changed.')
        else:
            self.__dict__[key] = value

    def __repr__(self):
        return f'{self.__class__.__name__}(access_level={self.access})'

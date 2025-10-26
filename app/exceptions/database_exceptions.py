class DatabaseException(Exception):
    pass


class DatabaseConnectionError(DatabaseException):
    pass


class QueryExecutionError(DatabaseException):
    pass


class RecordNotFoundError(DatabaseException):
    pass
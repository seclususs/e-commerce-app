class FileOperationError(Exception):
    pass


class FileUploadError(FileOperationError):
    pass


class InvalidFileTypeError(FileOperationError):
    pass


class FileNotFoundError(FileOperationError):
    pass
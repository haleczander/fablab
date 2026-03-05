class BackendApplicationError(Exception):
    pass


class PrinterNotRegisteredError(BackendApplicationError):
    pass


class DispatchTargetNotFoundError(BackendApplicationError):
    pass


class DispatchTemporaryError(BackendApplicationError):
    pass

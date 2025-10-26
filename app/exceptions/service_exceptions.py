class ServiceLogicError(Exception):
    pass


class OutOfStockError(ServiceLogicError):
    pass


class PaymentFailedError(ServiceLogicError):
    pass


class UserNotEligibleError(ServiceLogicError):
    pass


class InvalidOperationError(ServiceLogicError):
    pass
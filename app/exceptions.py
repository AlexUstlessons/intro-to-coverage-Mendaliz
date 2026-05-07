class AppError(Exception):
    status_code = 400

    def __init__(self, message):
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404


class InsufficientFundsError(AppError):
    pass


class AccountFrozenError(AppError):
    pass


class AccountClosedError(AppError):
    pass


class AccountNotFrozenError(AppError):
    pass


class AccountNotEmptyError(AppError):
    pass


class CardExpiredError(AppError):
    pass


class CardInactiveError(AppError):
    pass


class CardStolenError(AppError):
    pass


class DailyLimitExceededError(AppError):
    pass


class LoanAlreadyPaidError(AppError):
    pass


class LoanNotApprovedError(AppError):
    pass


class LoanNotPendingError(AppError):
    pass


class InvalidAmountError(AppError):
    pass


class UserHasActiveAccountsError(AppError):
    pass


class EmailAlreadyExistsError(AppError):
    pass


class OverdraftNotAllowedError(AppError):
    pass


class MinimumBalanceError(AppError):
    pass


class AlreadyVerifiedError(AppError):
    pass


class TransactionNotCancelableError(AppError):
    pass


class InvalidAccountTypeError(AppError):
    pass

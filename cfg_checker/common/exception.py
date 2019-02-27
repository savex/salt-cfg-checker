from exceptions import Exception


class CheckerBaseExceptions(Exception):
    pass


class CheckerException(CheckerBaseExceptions):
    def __init__(self, message, *args, **kwargs):
        super(CheckerException, self).__init__(message, *args, **kwargs)
        # get the trace
        # TODO: get and log traceback

        # prettify message
        self.message = "CheckerException: {}".format(message)


class ConfigException(CheckerException):
    def __init__(self, message, *args, **kwargs):
        super(ConfigException, self).__init__(message, *args, **kwargs)
        self.message = "Configuration error: {}".format(message)


class SaltException(CheckerException):
    def __init__(self, message, *args, **kwargs):
        super(SaltException, self).__init__(message, *args, **kwargs)
        self.message = "Salt error: {}".format(message)


class InvalidReturnException(CheckerException):
    def __init__(self, message, *args, **kwargs):
        super(InvalidReturnException, self).__init__(message, *args, **kwargs)
        self.message = "Unexpected return value: {}".format(message)

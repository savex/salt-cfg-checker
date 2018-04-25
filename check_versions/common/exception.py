from exceptions import Exception


class Cee8BaseExceptions(Exception):
    pass


class Cee8Exception(Cee8BaseExceptions):
    def __init__(self, message, *args, **kwargs):
        super(Cee8Exception, self).__init__(message, *args, **kwargs)
        # get the trace
        # TODO: get and log traceback

        # prettify message
        self.message = "CEE8Exception: {}".format(message)


class ConfigException(Cee8Exception):
    def __init__(self, message, *args, **kwargs):
        super(ConfigException, self).__init__(message, *args, **kwargs)
        self.message = "Configuration error: {}".format(message)

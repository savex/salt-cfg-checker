import itertools

from cfg_checker.helpers.errors import ErrorIndex


_c = itertools.count(1)


class NetworkErrors(ErrorIndex):
    # error type codes here
    NET_MTU_MISMATCH = next(_c)
    NET_MTU_EMPTY = next(_c)
    NET_NO_RC_IF_STATUS = next(_c)
    NET_DUPLICATE_IF = next(_c)
    NET_SUBNET_INTERSECT = next(_c)
    NET_MASK_MISMATCH = next(_c)
    NET_NODE_NON_RESPONSIVE = next(_c)
    NET_NODE_UNEXPECTED_IF = next(_c)
    NET_NO_RUNTIME_NETWORK = next(_c)
    NET_UNEXPECTED_GATEWAY = next(_c)
    NET_PING_SUCCESS = next(_c)
    NET_PING_TIMEOUT = next(_c)
    NET_PING_ERROR = next(_c)
    NET_PING_NOT_RESOLVED = next(_c)

    _initialized = False

    def _add_types(self):
        self.add_error_type(
            self.NET_MTU_MISMATCH,
            "MTU mismatch on runtime interface and in reclass"
        )
        self.add_error_type(
            self.NET_MTU_EMPTY,
            "MTU value is not 1500 on runtime and empty in reclass"
        )
        self.add_error_type(
            self.NET_NO_RC_IF_STATUS,
            "Reclass has no IF 'enable' status value"
        )
        self.add_error_type(
            self.NET_DUPLICATE_IF,
            "Duplicate interface specified"
        )
        self.add_error_type(
            self.NET_SUBNET_INTERSECT,
            "Subnets intersection detected"
        )
        self.add_error_type(
            self.NET_MASK_MISMATCH,
            "IFs mask settings for subnet is not the same"
        )
        self.add_error_type(
            self.NET_NODE_NON_RESPONSIVE,
            "Node failed to respond on at least one non-ping salt call"
        )
        self.add_error_type(
            self.NET_NODE_UNEXPECTED_IF,
            "Node has unexpected IF with mapped IP"
        )
        self.add_error_type(
            self.NET_NO_RUNTIME_NETWORK,
            "Reclass network not found in Runtime"
        )
        self.add_error_type(
            self.NET_UNEXPECTED_GATEWAY,
            "Runtime has unexpected gateway set for specific network"
        )
        self.add_error_type(
            self.NET_PING_SUCCESS,
            "Network Ping successfull"
        )
        self.add_error_type(
            self.NET_PING_TIMEOUT,
            "Ping Timeout from source to target"
        )
        self.add_error_type(
            self.NET_PING_ERROR,
            "Error while conducting ping"
        )
        self.add_error_type(
            self.NET_PING_NOT_RESOLVED,
            "Host not resolved while conducting Ping"
        )
        self._initialized = True

    def __init__(self, folder=None):
        super(NetworkErrors, self).__init__("NET", folder=folder)

        if not self._initialized:
            self._add_types()
            self._initialized = True

    def __call__(self):
        if not self._initialized:
            self._add_types()
            self._initialized = True

        return self


del _c

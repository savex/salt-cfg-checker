from cfg_checker.common.salt_utils import SaltRemote
from cfg_checker.common import logger

# instance of the salt client
salt = None


def get_salt_remote(config):
    """Singleton-like creation of instance

    Arguments:
        config {base_config} -- an instance to base_config
            with creds and params

    Returns:
        SaltRemote -- instance of salt client
    """

    global salt
    logger.info("Creating salt remote instance")
    # create it once
    if salt is None:
        salt = SaltRemote(config)
        # do most expensive operation with no strict timeout possible
        # all nodes that answer ping
        salt.nodes_active = salt.get_active_nodes()

    # return once required
    return salt

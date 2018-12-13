import os
import const
import log

from base_settings import PKG_DIR, base_config
from other import Utils


utils = Utils()
const = const

logger, logger_cli = log.setup_loggers(
    'cee8_features',
    log_fname=os.path.join(PKG_DIR, base_config.logfile_name)
)

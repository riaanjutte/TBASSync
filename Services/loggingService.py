import logging
from logging.handlers import RotatingFileHandler

from Services.paths import getUserDataFilePath

log_file_name = 'TBASSync.log'
# The tray app runs for weeks: keep TBASSync.log plus one older TBASSync.log.1, 1 MB each.
LOG_MAX_BYTES = 1_000_000


def getLogFilePath():
    """Absolute path to the log file (inside the user data dir when frozen)."""
    return getUserDataFilePath(log_file_name)


def initialise_logger(debug_mode = False):

    logLevel = logging.INFO
    if debug_mode:
        logLevel = logging.DEBUG

    logging.basicConfig(
        handlers=[RotatingFileHandler(getLogFilePath(), maxBytes=LOG_MAX_BYTES, backupCount=1, encoding="utf-8")],
        level= logLevel,          # Le niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format='%(asctime)s - %(levelname)s - %(message)s',  # Format du message
        datefmt='%Y-%m-%d %H:%M:%S'    # Format de la date
    )

    #Specific conditions to avoid useless logs
    logging.getLogger("PIL").setLevel(logging.INFO)

def info(e):
    logging.info(e)

def warning(e):
    logging.warning(e)

def error(e):
    logging.error(e, exc_info=isinstance(e, BaseException))

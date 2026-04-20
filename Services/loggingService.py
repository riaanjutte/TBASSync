import logging

from Services.paths import getUserDataFilePath

log_file_name = 'TBASSync.log'


def getLogFilePath():
    """Absolute path to the log file (inside the user data dir when frozen)."""
    return getUserDataFilePath(log_file_name)


def initialise_logger(debug_mode = False):

    logLevel = logging.INFO
    if debug_mode:
        logLevel = logging.DEBUG

    logging.basicConfig(
        filename=getLogFilePath(),     # Le fichier de log où les messages seront enregistrés
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
    logging.error(e)

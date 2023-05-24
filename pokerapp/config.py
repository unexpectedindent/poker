import os

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOG_FILENAME = 'logs.log'

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s, %(levelname)s, %(message)s, %(name)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'extended': {
            'format': (
                '%(asctime)s, '
                '%(filename)s, '
                '%(funcName)s, '
                '%(levelname)s, '
                '%(lineno)d, '
                '%(message)s, '
                '%(name)s'
            ),
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'logfile': {
            'formatter': 'extended',
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_FILENAME,
            'backupCount': 2,
            'maxBytes': 2000000,
            'mode': 'a'
        },
        'stream': {
            'formatter': 'default',
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        'homework': {
            'handlers': ['logfile', 'stream'],
            'level': 'INFO',

        }
    },
    'root': {'level': 'DEBUG', 'handlers': ['logfile', 'stream']}
}

TELEGRAM_TOKEN = os.getenv('TOKEN')

RETRY_TIME = 600

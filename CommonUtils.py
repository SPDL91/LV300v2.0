import configparser
import time
import pika
from os import sep, path, makedirs
import logging
import logging.handlers
from pika.exceptions import *


def init_logs(config, name):
    """Given a configparser object and a name for the log, sets up console and file logging, and sets log levels based on config file. Returns the logger object"""
    logger_object = logging.getLogger(name)
    log_size = int(config['SETTINGS']['LOG_SIZE_BYTES'])
    log_number = int(config['SETTINGS']['MAX_LOG_FILES'])
    log_path = str(config['SETTINGS']['LOG_DIR'])
    if not path.isdir(log_path):  # Test if log directory exists, if not, create it
        makedirs(log_path)
    fh = logging.handlers.RotatingFileHandler(log_path + sep + str(name) + '.log', maxBytes=log_size, backupCount=log_number)
    ch = logging.StreamHandler()
    log_level = config['SETTINGS']['LOGGING_LEVEL']
    try:
        logger_object.setLevel(log_level)
        fh.setLevel(log_level)
        ch.setLevel(log_level)
    except ValueError:
        print("LOG - Error with log level value: Setting logs to DEBUG")
        logger_object.setLevel(logging.DEBUG)
        fh.setLevel(logging.DEBUG)
        ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    logger_object.addHandler(ch)
    logger_object.addHandler(fh)
    logger_object.info("Logging initialisation complete")
    return logger_object


def load_main_config():
    """Load the main application .ini config file."""
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config


def connect_rabbitmq(logger, config, process_name):
    rmq_host = str(config['SETTINGS']['RMQ_HOST'])
    rmq_port = int(config['SETTINGS']['RMQ_PORT'])
    rmq_user = str(config['SETTINGS']['RMQ_USER'])
    rmq_password = str(config['SETTINGS']['RMQ_PASSWORD'])
    while True:
        try:
            logger.info(str(process_name) + " connecting to RabbitMQ Server")
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=rmq_host, port=rmq_port, credentials=pika.credentials.PlainCredentials(rmq_user, rmq_password)))
            channel = connection.channel()
            logger.info(str(process_name) + " successfully connected to RabbitMQ Server")
            return channel
        except ProbableAuthenticationError as ex:
            logger.critical("Exception: " + str(ex))
            time.sleep(3)
            raise ValueError("Credential error when connecting to RabbitMQ Server")
        except Exception as ex:
            logger.critical("Error in connection to RabbitMQ Server!")
            logger.critical("Exception: " + str(ex))
            logger.critical("Retrying connection")
            time.sleep(3)


if __name__ == '__main__':
    test_config = load_main_config()
    test_logger = init_logs(test_config, 'UTIL_TEST')
    rmq_channel = connect_rabbitmq(test_logger, test_config, 'UTIL_TEST')
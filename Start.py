from CommonUtils import init_logs, load_main_config
from threading import Thread
from LV300 import *


def start_camera_thread(config, camera_id):
    """Bind socket and start message handler thread for each Camera"""
    logger = init_logs(config, camera_id)
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_address = (config[camera_id]['SERVER_IP'], int(config[camera_id]['PORT']))
            logger.info("Binding socket at: %s port: %s" % client_address)
            sock.bind(client_address)
            logger.info("Socket bound successfully")
            logger.info("Waiting for incoming connection")
            sock.listen(1)
            client_socket = None
            while True:
                try:
                    client_socket, address = sock.accept()
                    logger.info("Successfully connected to %s" % str(address))
                    logger.info("Starting message handler thread for %s" % str(address))
                    Thread(target=message_handler, args=(client_socket, logger, address, config, camera_id)).start()
                except IndexError:
                    client_socket.close()
                    logger.info("Connection lost - Attempting to reconnect")
        except OSError as ex:
            logger.warning("Connection failed - Retrying")
            logger.error("Network error: Check IP/Port details")
            logger.error(ex)
            time.sleep(5)
        except Exception as ex:
            logger.critical('Unhandled exception occurred!')
            logger.critical(ex)
            time.sleep(5)


def start_cameras(config, cam_names):
    """Start a thread for each camera found in the config file"""
    for name in cam_names:
        Thread(target=start_camera_thread, args=(config, name)).start()


def get_number_cameras(config):
    """Checks the config .ini file for camera names and returns them as a list of strings"""
    cameras = []
    x = 1
    while True:
        name = 'CAMERA_' + str(x)
        if config.has_section(name):
            cameras.append(name)
            x += 1
        else:
            return cameras


if __name__ == "__main__":
    main_config = load_main_config()
    logger = init_logs(main_config, 'Main')
    camera_names = get_number_cameras(main_config)
    start_cameras(main_config, camera_names)

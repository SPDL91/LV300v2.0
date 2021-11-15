import queue
import socket
from threading import Thread
import time
from messageLib import *
import pika
from CommonUtils import *

image_name_holder = {}


def message_handler(client_socket, logger, camera_ip, config, camera_id):
    """Set up thread to continually handle new messages"""
    try:
        channel = connect_rabbitmq(logger, config, ('Camera at ' + camera_ip[0]))
        q = queue.Queue(maxsize=10000)
        params_set = False
        output_params = {}
        socket_receive_thread = Thread(target=socket_reader, args=(client_socket, q, logger,))
        socket_receive_thread.start()
        while True:
            if params_set:
                check_output_trigger_queue(client_socket, camera_id, config, output_params, channel, logger)
            try:
                received_message = q.get(block=False)
                if isinstance(received_message, str):
                    raise socket.error('Error in socket receive thread')
                image_data, decoded = received_message[0], received_message[1]
            except queue.Empty:
                decoded = None
                image_data = None
                pass
            if decoded is None:
                pass
            else:
                if params_set:
                    pass
                else:
                    output_params = set_output_params(decoded, config, camera_id)
                    params_set = True
                logger.debug("Received message: " + str(decoded))
                message_code = decoded[3].upper()
                if message_code == "KA":  # Keep Alive
                    KA(client_socket, decoded, logger)
                elif message_code == "EP":
                    XP(client_socket, decoded, config, camera_ip, logger, channel, camera_id)
                elif message_code == "XP":
                    XP(client_socket, decoded, config, camera_ip, logger, channel, camera_id)
                elif message_code == "AI" or message_code == "XI":
                    XI(client_socket, decoded, image_data, config, logger, camera_id)
                else:  # Camera has sent ACK
                    pass
            time.sleep(0.01)
    except ValueError as ex:
        logger.warning("Exception occurred: " + str(ex))
        logger.warning("Closing socket to reconnect")
        client_socket.close()
        logger.warning("Connection to a camera has been lost - Waiting to reconnect")


def socket_reader(client_socket, received_queue, logger):
    while True:
        fragments = []
        while True:
            try:
                chunk = client_socket.recv(1024)
                fragments.append(chunk)
                data = b''.join(fragments)
                len_data = len(data)
                if data[len_data - 1] == 4:
                    break
            except Exception as e:
                received_queue.put(str(e))
                time.sleep(1)
        end_point = 0
        for byte in data:
            if byte == 3:
                end_point = data.index(byte)
                break
        message_data = data[:end_point]
        logger.debug("Received message: " + str(message_data))
        image_data = data[(end_point + 1):]
        decoded = data_to_dict(message_data.decode('utf-8'))
        received_queue.put([image_data, decoded])


def KA(client_socket, decoded, logger):
    logger.info("Received connection Keep alive")
    ack(decoded, client_socket, logger)


def XP(client_socket, decoded, config, camera_ip, logger, channel, camera_id):
    image_one_name, image_two_name = generate_image_names(decoded, camera_id)
    logger.info('Received PlateData message')
    check_allowed_access(decoded[8], datetime.now(), camera_id, channel, image_one_name, image_two_name, logger, config)
    ack(decoded, client_socket, logger)
    if config['LV300']['WRITE_CSV'] == 'True':
        logger.info('writing transit to CSV file')
        write_csv(decoded, config, logger, image_one_name, image_two_name)
    if config['LV300']['SAVE_IMAGES'] == 'True':
        logger.info("Sending request for images")
        image_request(decoded, client_socket, logger)


def XI(client_socket, decoded, image_data, config, logger, camera_id):
    global image_name_holder
    logger.info("Received image data message")
    if int(decoded[6]) == 0:
        logger.warning("Image data message contains no images")
        ack(decoded, client_socket, logger)
    elif int(decoded[6]) == 1:
        image_data = demask_image(image_data)
        write_image(image_data, 1, config, logger, image_name_holder, camera_id)
        del image_name_holder[camera_id + '_1']
        ack(decoded, client_socket, logger)
    elif int(decoded[6]) >= 2:
        image1, image2 = split_image(image_data, 2)
        image1, image2 = demask_image(image1), demask_image(image2)
        try:
            write_image(image1, 1, config, logger, image_name_holder, camera_id)
            write_image(image2, 2, config, logger, image_name_holder, camera_id)
            del image_name_holder[camera_id + '_1']
            del image_name_holder[camera_id + '_2']
        except KeyError:
            logger.critical('KeyError when building image save path - XI/AI message may be received out of order')
        ack(decoded, client_socket, logger)


def DA(client_socket, output, output_params, logger):
    output_time = 1000
    if output == '000':
        output_time = str(output_params['out_0_pulse'])
    elif output == '001':
        output_time = str(output_params['out_1_pulse'])
    reply = "\x02000000035" + output_params['protocol'] + \
            "000DA" + output_params['terminal_id'] + output + 'E' + output_time.rjust(6, '0')[:6] + "\x03\x04"
    client_socket.send(bytes(reply, 'utf-8'))
    logger.debug(reply)
    logger.info('Triggered output ' + output + ' for ' + output_time + 'ms')


def check_allowed_access(rego, passage_datetime, camera_id, channel, image_one_name, image_two_name, logger, config):
    lpr_disable = get_camera_lpr_disable(camera_id, config)
    if lpr_disable:
        logger.info('LPR transit processing disabled for ' + camera_id + ' transit info NOT sent to processing queue')
        pass
    else:
        message = rego + '#$#' + str(passage_datetime) + '#$#' + str(
            camera_id) + '#$#' + image_one_name + '#$#' + image_two_name
        body = json.dumps(message)
        channel.basic_publish(exchange='LV300', routing_key='TRANSIT_QUEUE', body=body)
        logger.info('Successfully sent transit details to processing queue')


def get_camera_type(ip, config, logger):
    """Checks config to determine camera type of given camera_ID"""
    ip = str(ip[0])
    sections = config.sections()
    for section in sections:
        if config.has_option(section, 'CAMERA_IP'):
            if config.get(section, 'CAMERA_IP'):
                if config.get(section, 'CAMERA_IP') == ip:
                    camera_type = str(config.get(section, 'CAMERA_TYPE'))
                    return camera_type
    return False


def get_camera_lpr_disable(camera_id, config):
    """Checks config to determine if lpr is disabled for given camera ID"""
    lpr_disable = config[camera_id]['DISABLE_LPR_TRANSIT']
    if lpr_disable == 'True':
        lpr_disable = True
    elif lpr_disable == 'False':
        lpr_disable = False
    else:
        lpr_disable = False
    return lpr_disable


def generate_image_names(decoded, camera_id):
    global image_name_holder
    date, timestamp, plate = decoded[6], decoded[7], decoded[8]
    image_one_name = str(date) + str(timestamp) + str(plate) + '001' + '.jpg'
    image_two_name = str(date) + str(timestamp) + str(plate) + '002' + '.jpg'
    image_name_holder[camera_id + '_1'] = image_one_name
    image_name_holder[camera_id + '_2'] = image_two_name
    return image_one_name, image_two_name


def set_output_params(decoded, config, camera_id):
    output_params = {'protocol': decoded[1], 'terminal_id': decoded[4],
                     'out_0_pulse': config[camera_id]['OUTPUT_0_PULSE'],
                     'out_1_pulse': config[camera_id]['OUTPUT_1_PULSE']}
    return output_params


def check_output_trigger_queue(client_socket, camera_id, config, output_params, channel, logger):
    method_frame, header_frame, body = channel.basic_get(queue=config[camera_id]['TRIGGER_QUEUE'])
    if method_frame is None:
        pass
    else:
        channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        output = (decode_json_message(body))[0]
        DA(client_socket, output, output_params, logger)

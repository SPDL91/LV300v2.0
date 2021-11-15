from CommonUtils import *


def mock_server():
    while True:
        time.sleep(0.05)
        method_frame, header_frame, body = channel.basic_get(queue='TRANSIT_QUEUE')
        if method_frame is None:
            pass
        else:
            channel.basic_ack(delivery_tag=method_frame.delivery_tag)
            message = decode_json_message(body)
            logger.debug('Received message: ' + str(message))
            if check_message_age(message[1], config, logger):
                pass
            else:
                return_queue = config[message[2]]['TRIGGER_QUEUE']
                output_number = '000'
                message = output_number
                body = json.dumps(message)
                channel.basic_publish(exchange='LV300', routing_key=return_queue, body=body)
                logger.debug('Sent message: ' + str(message) + ' to queue ' + str(return_queue))


config = load_main_config()
logger = init_logs(config, 'MockServer')
channel = connect_rabbitmq(logger, config, 'MockServer')
mock_server()

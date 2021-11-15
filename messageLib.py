import datetime
import csv


def data_to_dict(data):
    data_list = []
    length = str(data[1:10]).lstrip()
    protocol = str(data[10:15])
    counter = str(data[15:18])
    message_code = str(data[18:20])
    terminal_number = str(data[20:23])
    data_list.extend([length, protocol, counter, message_code, terminal_number])
    if message_code in ('KA', 'AA'):
        return data_list
    elif message_code == "XP" or "EP":
        traffic_id = str(data[23:33])
        get_time = datetime.datetime.now().time()
        get_date = datetime.datetime.now()
        date = str(get_date.strftime('%Y%m%d'))
        time = str(get_time.strftime('%H%M%S'))
        plate = str(data[47:67]).rstrip()
        confidence = str(data[107:109])
        data_list.extend([traffic_id, date, time, plate, confidence])
        return data_list
    else:
        traffic_id = str(data[23:33])
        image_count = str(data[33:35])
        image_one_length = str(data[35:45])
        image_one_id = str(data[45:47])
        image_two_length = str(data[47:57])
        image_two_id = str(data[57:59])
        data_list.extend([traffic_id, image_count, image_one_length,
                         image_one_id, image_two_length, image_two_id])
        return data_list


def ack(data, client_socket, logger):
    reply = "\x02000000028" + data[1] + \
        "000AA" + data[4] + data[2] + "\x03\x04"
    client_socket.send(bytes(reply, 'utf-8'))
    logger.info("Sent Acknowledge")


def image_request(data, client_socket, logger):
    reply = "\x02000000037" + data[1] + data[2] + \
        "RI" + data[4] + data[5] + "01" + "02" + "\x03\x04"
    logger.debug('Send image request: ' + str(reply))
    client_socket.send(bytes(reply, 'utf-8'))


def split_image(data, number_images):
    if number_images == 2:
        image_one = bytearray()
        image_two = bytearray()
        for idx, x in enumerate(data):
            if x == 217 and data[idx - 1] == 255:
                image_one.append(217)
                break
            else:
                image_one.append(x)
        for idx, x in enumerate(data[len(image_one):]):
            if x == 217 and (data[len(image_one):])[idx - 1] == 255:
                image_two.append(217)
                break
            else:
                image_two.append(x)
        return image_one, image_two
    elif number_images == 1:
        image_one = bytearray()
        for idx, x in enumerate(data):
            if x == 217 and data[idx - 1] == 255:
                image_one.append(217)
                break
            else:
                image_one.append(x)
        return image_one


def demask_image(data):
    clean_array = bytearray()
    for idx, x in enumerate(data):
        if x == 27:
            if data[idx + 1] == 155:
                clean_array.append(27)
            else:
                pass
        elif x == 130 and data[idx - 1] == 27:
            clean_array.append(2)
        elif x == 131 and data[idx - 1] == 27:
            clean_array.append(3)
        elif x == 132 and data[idx - 1] == 27:
            clean_array.append(4)
        elif x == 155 and data[idx - 1] == 27:
            pass
        else:
            clean_array.append(x)
    return clean_array


def write_image(image_data, image_number, config, logger, name_holder, camera_id):
    ext_path = str(config['LV300']['IMAGE_SAVE_REDIRECT'])
    image_path = config['LV300']['IMAGE_SAVE_PATH']
    image_save_path = ''
    if image_number == 1:
        image_save_path = ext_path + image_path + name_holder[camera_id + '_1']
    elif image_number == 2:
        image_save_path = ext_path + image_path + name_holder[camera_id + '_2']
    logger.info(image_save_path)
    with open(image_save_path, 'w+b') as file:
        file.write(image_data)

def write_csv(decoded, config, logger, image_one_name, image_two_name):
    try:
        date, timestamp, terminal_number, plate, confidence = decoded[6], decoded[7], decoded[4], decoded[8], decoded[9]
        date_formatted = date[0:4] + "-" + date[4:6] + "-" + date[6:8]
        time_formatted = timestamp[0:2] + ":" + timestamp[2:4] + ":" + timestamp[4:6]
        if config['LV300']['USE_BULK_CSV'] == 'True':
            file_name_builder = config['LV300']['CSV_SAVE_PATH'] + str(date) + '.csv'
            with open(str(file_name_builder), mode='a') as csv_write:
                file_writer = csv.writer(csv_write, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
                file_writer.writerow(
                    [date_formatted, time_formatted, terminal_number, plate, confidence, image_one_name, image_two_name])
        elif config['LV300']['USE_BULK_CSV'] == 'False':
            file_name_builder = config['LV300']['CSV_SAVE_PATH'] + str(date) + str(timestamp) + str(plate) + '.csv'
            logger.info(file_name_builder)
            with open(str(file_name_builder), mode='w') as csv_write:
                file_writer = csv.writer(csv_write, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
                file_writer.writerow(
                    [date_formatted, time_formatted, terminal_number, plate, confidence, image_one_name, image_two_name])
    except Exception as e:
        logger.error(e)

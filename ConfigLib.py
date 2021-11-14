import re
import sys
import uuid
import time
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import unpad


def read_encrypted(password, iv, filename, string=True):
    try:
        with open(filename, 'rb') as input_text:
            cipher_text = input_text.read()
            decrypter = AES.new(password, AES.MODE_CBC, iv)
            plaintext = unpad(decrypter.decrypt(cipher_text), 16)
            if string:
                return plaintext.decode('utf8')
            else:
                return plaintext
    except FileNotFoundError:
        print('Unable to read license file! Program will now exit')
        time.sleep(3)
        sys.exit(1)


def get_license_data():
    password = '1eb%0W^lEAbaSb7J^5b84Cg!NedDtH50'
    iv = '2983475623956923'
    filename = 'LV300.License'
    data = read_encrypted(bytes(password, 'utf-8'), bytes(iv, 'utf-8'), filename)
    mac_address, max_cameras = data.split(';')
    return mac_address, max_cameras


def check_license():
    mac_address = (':'.join(re.findall('..', '%012x' % uuid.getnode())))
    licensed_mac, max_cameras = get_license_data()
    if mac_address != licensed_mac:
        print('Invalid License - The servers MAC address does not match the provided License. The program will now '
              'exit.')
        print('Local MAC: ' + str(mac_address))
        time.sleep(3)
        sys.exit(1)
    return max_cameras

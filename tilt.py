import ubluetooth

from time import sleep, time
from struct import unpack
import ubinascii
import _thread
import ubluetooth
from micropython import const
import gc
import ujson
import urequests

DEVICE_COLORS = {
    'RED': 'a495bb10c5b14b44b5121370f02d74de',
    'GREEN': 'a495bb20c5b14b44b5121370f02d74de',
    'BLACK': 'a495bb30c5b14b44b5121370f02d74de',
    'PURPLE': 'a495bb40c5b14b44b5121370f02d74de',
    'ORANGE': 'a495bb50c5b14b44b5121370f02d74de',
    'BLUE': 'a495bb60c5b14b44b5121370f02d74de',
    'YELLOW': 'a495bb70c5b14b44b5121370f02d74de',
    'PINK': 'a495bb80c5b14b44b5121370f02d74de'
}

_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)


#Tilt format based on iBeacon format and filter includes Apple iBeacon identifier portion (4c000215) as well as Tilt specific uuid preamble (a495)
TILT = '4c000215a495'

ble = ubluetooth.BLE()


def get_device_color(uuid):
    return list(DEVICE_COLORS.keys())[list(DEVICE_COLORS.values()).index(uuid)]

def parse_device_uuid(adv_data):
    uuid = ubinascii.hexlify(adv_data)[18:50]
    return uuid.decode('utf-8')


def log_data(addr, payload):
    global temp_f
    global sg_read
    global found_tilt

    #uuid = parse_device_uuid(payload)
    #mac_addr = ubinascii.hexlify(addr).decode('utf-8')
    #device_color = get_device_color(uuid)

    # Get fermentation data
    temp_f = int(ubinascii.hexlify(payload)[50:54].decode('utf-8'), 16)
    sg_read = int(ubinascii.hexlify(payload)[54:58].decode('utf-8'), 16)
    found_tilt = True
    print("Stop scan")
    ble.gap_scan(None) 

def handle_ibeacon(beacon_data):
    addr_type, addr, adv_type, rssi, adv_data = beacon_data
    identifier = ubinascii.hexlify(adv_data)[10:22]
    if identifier.decode("utf-8") == TILT:
        uuid = parse_device_uuid(adv_data)
        if uuid.lower() in DEVICE_COLORS.values():
            log_data(addr, adv_data)
        else:
            print("Device {} found but not match any known Tilt color".format(uuid))

def bt_irq(event, data):
    global scan_done
    if event == _IRQ_SCAN_RESULT:
        # A single scan result.
        handle_ibeacon(data)

    elif event == _IRQ_SCAN_DONE:
        scan_done = True
        print("Scan done")
        pass

def start_scan():
    global scan_done
    global temp_f
    global sg_read
    global found_tilt

    temp_f = None
    sg_read = None
    found_tilt = False
    scan_done = False

    ble.active(True)
    ble.irq(bt_irq)
    ble.gap_scan(0,500000,500000)

def query_tilt():
    global scan_done
    global temp_f
    global sg_read
    global found_tilt
    if scan_done and found_tilt:
        return temp_f, sg_read
    else:
        return None, None

def wait_for_tilt(seconds=15):
    global scan_done
    global temp_f
    global sg_read
    global found_tilt

    scanned = 0
    while not scan_done:
        print("Still scanning")
        sleep(1)
        scanned = scanned + 1
        if scanned > seconds:
            print("Giving up")
            ble.gap_scan(None) 

    ble.active(False)

    if found_tilt:
        return temp_f, sg_read
    else:
        return None, None


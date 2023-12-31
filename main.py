import time
import json
from inkplate2 import Inkplate      
from netutil import do_connect
from tilt import start_scan, wait_for_tilt, query_tilt
import imageutil
import urequests
import sys
import machine
from uio import StringIO
from timeutil import update_time, format_time

from umqtt import MQTTClient

from mysecrets import BREWFATHER_KEY, BROKER_ADDR

DEBUG = False   #prevent deep sleep

SLEEP_MINUTES=2
WAIT_FOR_TILT_SECONDS=15
DEFAULT_FILE="tiltbridge-1.png"
SEND_INTERVAL_HOURS=5 # Interval after which data is resent even if not changed
BREWFATHER_URL=f"http://log.brewfather.net/stream?id={BREWFATHER_KEY}"

needs_display = False
needs_wifi = True
needs_time = False
needs_image = False
needs_update = False
needs_send = False

first_boot = True
needs_mqtt = True

png_file_path = DEFAULT_FILE

current_temp=None
current_gravity=None

last_run = 0
last_update = 0
last_temp=None
last_gravity=None
last_beer_name=""
beer_name=""

rtc = machine.RTC()

def print_display(text, x=0, y=0, color=Inkplate.BLACK, fontSize=1, shadow=False):
    display.setTextSize(fontSize)
    background = Inkplate.BLACK
    if color == Inkplate.BLACK:
        background = Inkplate.WHITE
    line_height = 10 * fontSize
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        y_position = i * line_height + y
        if shadow:
            display.printText(x+1, y_position, line, c=background)
            display.printText(x+1, y_position+1, line, c=background)
            display.printText(x, y_position+1, line, c=background)
        display.printText(x, y_position, line, c=color)    

def display_error(e, line_height=10):
    import sys
    from io import StringIO
    sys.print_exception(e)
    s = StringIO()
    sys.print_exception(e, s)  
    display.clearDisplay()
    print_display(s.getvalue())
    display.display()

# Start scan early because it runs in the background
start_scan()

if machine.wake_reason() == machine.DEEPSLEEP:
    print('Wake from deep sleep')
    first_boot = False
    try:
        data_restored = json.loads(rtc.memory())
        print("Data restored:", data_restored)
        rtcdata = data_restored
        first_boot = False
        png_file_path=rtcdata.get("imgfile", DEFAULT_FILE)
        last_run=rtcdata.get("last_run", 0)
        last_update=rtcdata.get("last_update", 0)
        last_gravity=rtcdata.get("gravity")
        last_temp=rtcdata.get("temp")
        last_beer_name=rtcdata.get("beer_name", "")
    except (ValueError, TypeError):
        print("No data available or data is corrupt")
        first_boot = True

print(f"last_beer_name: {last_beer_name}")
print(f"png_file_path: {png_file_path}")
print(f"last_gravity: {last_gravity}")
print(f"last_temp: {last_temp}")
print(f"last_run: {last_run}")
print(f"last_update: {last_update}")

display = Inkplate()
display.begin()

if first_boot:
    print('First boot')
    needs_time = True
    needs_update = True
    needs_display = True

try:

    if needs_wifi or needs_time or needs_update:
        print("Request wifi")
        do_connect()

    if needs_time:
        print("Update time")
        update_time()
        print('Local time:', rtc.datetime())

    if needs_update:
        try:
            beer_name, img_src = imageutil.get_beer()
            if beer_name != last_beer_name:
                print(f"Found new beer/info {beer_name}")
                needs_image = True
        except Exception as e:
            print("Could not load beer info")
            sys.print_exception(e)
    else:
        beer_name = last_beer_name

    if needs_image:
        print("Load image")
        try:
            png_file_path=imageutil.download_image(img_src)
            needs_display=True
        except Exception as e:
            print("Could not load beer image")
            sys.print_exception(e)


    print("Update display")
    imageutil.display_image(display, png_file_path)

    if first_boot:
        current_temp, current_gravity = query_tilt()
        if current_temp is None:
            print("No tilt data available yet but first boot, draw image immediately instead of waiting for tilt")
            display.display()
            needs_display = False

    needs_reset = not first_boot and last_temp is not None

    print(f"Wait for tilt for {WAIT_FOR_TILT_SECONDS} secs, reboot on failure: {needs_reset}")
    current_temp, current_gravity = wait_for_tilt(seconds=WAIT_FOR_TILT_SECONDS, reboot_on_failure=needs_reset)

    if current_temp is None:
        print("No tilt data found")
        if last_temp is not None:
            print("Last temp was set, refresh")
            needs_display: True
    elif current_temp > 250:
        print("Invalid tilt data")
    else:
        print(f"Temp: {current_temp} Gravity:{current_gravity}")

        if first_boot:
            print(f"Send because first boot")
            needs_send = True
        elif current_temp != last_temp:
            print(f"Send because current_temp {current_temp} != last_temp {last_temp}")
            needs_send = True
        elif current_gravity != last_gravity:
            print(f"Send because current_gravity {current_gravity} != last_gravity {last_gravity}")
            needs_send = True
        elif time.time() - last_update > (SEND_INTERVAL_HOURS * 60 * 60):
            print(f"Send because last_update {last_update} is more than {SEND_INTERVAL_HOURS} hours ago")
            needs_send = True
    
        #212x104
        degc_string = ""
        plato_string = ""
        if current_gravity is not None:
            gravity_float = current_gravity / 1000
            plato = -616.868 + (1111.14 * gravity_float) - (630.272 * gravity_float**2) + (135.997 * gravity_float**3)
            plato_string = f"{plato:.1f} P"
        if current_temp is not None:
            degc = (current_temp - 32) * 5/9
            degc_string = f"{degc:.1f} C"

        print(plato_string) 
        print(degc_string) 
        print_display(plato_string, 10, 85, fontSize=2)
        print_display(degc_string, 120, 85, fontSize=2)
        needs_display = True
        if needs_mqtt:
            mqttc = MQTTClient('tiltplate', BROKER_ADDR, keepalive=60)
            try:
                mqttc.connect()     
                mqttc.publish("tilt/plato", f"{plato:.1f}")   
                mqttc.publish("tilt/temp", f"{degc:.1f}") 
            except Exception as e:
                print("Could update mqtt")
                sys.print_exception(e)
                print_display("Error", 147, 0, Inkplate.RED, fontSize=2, shadow=True)
                print_display(str(e), 0, 0, Inkplate.WHITE, fontSize=1, shadow=True)
                needs_display = True




    if needs_send:
        # https://docs.brewfather.app/integrations/custom-stream
        data = {
            "name": "Tiltplate",  
            "temp": current_temp,
            "temp_unit": "F",
            "gravity": (current_gravity / 1000.0)
        }
        print(data)

        if time.time() - last_update < (14 * 60):
            print("Skip update because of brewfather rate limiting")
        else:
            print("Update brewfather")
            try:
                response = urequests.post(BREWFATHER_URL, json=data)
                print(response.text)
                last_update = time.time()
            except Exception as e:
                print("Could update brewfather")
                sys.print_exception(e)
                print_display("Error", 147, 0, Inkplate.RED, fontSize=2, shadow=True)
                print_display(str(e), 0, 0, Inkplate.WHITE, fontSize=1, shadow=True)
                needs_display = True


    tilt_update = format_time(time.time())
    brewfather_update = format_time(last_update)
    if last_update == 0:
        brewfather_update = "n/a"
    print_display(f"Tilt: {tilt_update} Brewfather: {brewfather_update}", 3, 73, Inkplate.WHITE, fontSize=1, shadow=True)

    if needs_display:
        print("Refresh display")
        display.display()    

    rtcdata = {
        "last_update": last_update,
        "last_run": time.time(),
        "temp": current_temp,
        "gravity": current_gravity,
        "imgfile": png_file_path,
        "beer_name": beer_name
    }
    datastr = json.dumps(rtcdata)
    print(f"Store to rtc: \n{datastr}")
    rtc.memory(datastr)

    if not DEBUG:
        print(f"Going to sleep for {SLEEP_MINUTES} minutes")
        machine.deepsleep(int(SLEEP_MINUTES * 60 * 1000))

except Exception as e:
    print("Error")
    display_error(e) 
    print(f"Going to sleep for {SLEEP_MINUTES} minutes")
    machine.deepsleep(int(SLEEP_MINUTES * 60 * 1000))
    
    
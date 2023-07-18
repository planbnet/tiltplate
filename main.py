import time
import machine 
import json
from inkplate2 import Inkplate      
from netutil import do_connect
from tilt import start_scan, wait_for_tilt, query_tilt
import imageutil
import urequests

from mysecrets import BREWFATHER_KEY

DEBUG = True   #prevent deep sleep

SLEEP_MINUTES=15
WAIT_FOR_TILT_SECONDS = 5
DEFAULT_FILE="tiltbridge-1.png"
SEND_INTERVAL_HOURS=5 # Interval after which data is resent even if not changed
BREWFATHER_URL=f"http://log.brewfather.net/stream?id={BREWFATHER_KEY}"


needs_display = False
needs_wifi = False
needs_time = False
needs_image = False
needs_update = False
needs_send = False

first_boot = True

png_file_path = DEFAULT_FILE

current_temp=None
current_gravity=None

last_run = 0
last_temp=None
last_gravity=None
last_beer_name=""

rtc = machine.RTC()

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
    last_gravity=rtcdata.get("gravity")
    last_temp=rtcdata.get("temp")
    last_beer_name=rtcdata.get("beer_name", "")
    print(f"loaded last_beer_name: {last_beer_name}")
    print(f"loaded png_file_path: {png_file_path}")
    print(f"loaded last_gravity: {last_gravity}")
    print(f"loaded last_temp: {last_temp}")
    print(f"loaded last_run: {last_run}")
except (ValueError, TypeError):
    print("No data available or data is corrupt")
    first_boot = True

if first_boot:
    print('First boot')
    needs_time = True
    needs_update = True
    needs_display = True


if needs_wifi or needs_time or needs_update:
    print("Request wifi")
    do_connect()

if needs_time:
    from timeutil import update_time
    print("Update time")
    update_time()
    print('Local time:', rtc.datetime())

if needs_update:
    beer_name, img_src = imageutil.get_beer()
    if beer_name != last_beer_name:
        print(f"Found new beer/info {beer_name}")
        needs_image = True

if needs_image:
    print("Load image")
    png_file_path=imageutil.download_image(img_src)
    needs_display=True

if needs_display:
    print("Update display")
    display = Inkplate()
    display.begin()
    imageutil.display_image(display, png_file_path)
    if first_boot:
        current_temp, current_gravity = query_tilt()
        if current_temp is None:
            print("No tilt data available yet but first boot, draw image immediately instead of waiting for tilt")
            display.display()
            needs_display = False

print("Wait for tilt")
current_temp, current_gravity = wait_for_tilt(WAIT_FOR_TILT_SECONDS)

if current_temp is None:
    print("No tilt data found")
else:
    print(f"Temp: {current_temp} Gravity:{current_gravity}")
    if first_boot or current_temp != last_temp or current_gravity != last_gravity or time.time() - last_run > (SEND_INTERVAL_HOURS * 60 * 60):
        needs_send = True
  
    #212x104
    display.setTextSize(3)
    degc_string = ""
    plato_string = ""
    if current_gravity is not None:
        gravity_float = current_gravity / 1000
        plato = -616.868 + (1111.14 * gravity_float) - (630.272 * gravity_float**2) + (135.997 * gravity_float**3)
        plato_string = f"{plato:.1f}°P"
    if current_temp is not None:
        degc = (current_temp - 32) * 5/9
        degc_string = f"{degc:.1f}°C"

    print(plato_string) 
    print(degc_string) 
    display.printText(10, 70, plato_string, c=Inkplate.BLACK)
    display.printText(110, 70, degc_string, c=Inkplate.BLACK)
    needs_display = True

if needs_send:
    print("Update brewfather")
    # https://docs.brewfather.app/integrations/custom-stream
    data = {
        "name": "Tiltplate",  
        "temp": current_temp,
        "temp_unit": "F",
        "gravity": (current_gravity / 1000.0)
    }
    print(data)
    response = urequests.post(BREWFATHER_URL, json=data)
    print(response.text)
    #TODO: Handle failure?

if needs_display:
    print("Refresh display")
    display.display()    

rtcdata = {
    "lastupdate": time.time(),
    "temp": current_temp,
    "gravity": current_gravity,
    "imgfile": png_file_path,
    "last_beer": beer_name
}
datastr = json.dumps(rtcdata)
print(f"Store to rtc: \n{datastr}")
rtc.memory(datastr)

if not DEBUG:
    print(f"Going to sleep for {SLEEP_MINUTES} minutes")
    machine.deepsleep(SLEEP_MINUTES * 60 * 1000)
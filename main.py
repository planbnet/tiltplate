import time
import machine 
import json
from inkplate2 import Inkplate      
from netutil import do_connect
from tilt import start_scan, wait_for_tilt
import imageutil
import urequests

from secrets import BREWFATHER_KEY

sleep_minutes = 1
wait_for_tilt_seconds = 30
debug = False   #prevent deep sleep

DEFAULT_FILE="tiltbridge-1.png"
BREWFATHER_URL=f"http://log.brewfather.net/stream?id={secrets.BREWFATHER_KEY}"


needs_display = False
needs_wifi = False
needs_time = False
needs_image = False
needs_send = False

first_boot = True

png_file_path = DEFAULT_FILE
last_run = 0
current_temp=None
current_gravity=None
last_temp=None
last_gravity=None

rtc = machine.RTC()

# Start scan early because it runs in the background
start_scan()

if machine.wake_reason() == machine.DEEPSLEEP:
    print('Wake from deep sleep')
    try:
        data_restored = json.loads(rtc.memory())
        print("Data restored:", data_restored)
        rtcdata = data_restored
        first_boot = False
        png_file_path=rtcdata.get("imgfile", DEFAULT_FILE)
        last_run=rtcdata.get("last_run", 0)
        last_gravity=rtcdata.get("gravity")
        last_temp=rtcdata.get("temp")
    except (ValueError, TypeError):
        print("No data available or data is corrupt")
        first_boot = True



if first_boot:
    print('First boot')
    needs_time = True
    needs_image = True
    needs_display = True


if needs_wifi or needs_time or needs_image:
    print("Request wifi")
    do_connect()

if needs_time:
    from timeutil import update_time
    print("Update time")
    update_time()
    print('Local time:', rtc.datetime())

if needs_image:
    print("Load image")
    beer_name, img_src = imageutil.get_beer()
    png_file_path=imageutil.download_image(img_src)
    needs_display=True

if needs_display:
    print("Update display")
    display = Inkplate()
    display.begin()
    imageutil.display_image(display, png_file_path)

print("Wait for tilt")
current_temp, current_gravity = wait_for_tilt() # wait for tilt for max 15 secs

if current_temp is None:
    print("No tilt data found")
else:
    print(f"Temp: {current_temp} Gravity:{current_gravity}")
    #TODO: Maybe check if transmit is only required on changes or after x amount of minutes
    needs_send = True
    #TODO: Draw last update, gravity and temp to epaper
    needs_display = True

"""
{
  "name": "YourDeviceName", // Required field, this will be the ID in Brewfather
  "temp": 20.32,
  "aux_temp": 15.61, // Fridge Temp
  "ext_temp": 6.51, // Room Temp
  "temp_unit": "C", // C, F, K
  "gravity": 1.042,
  "gravity_unit": "G", // G, P
  "pressure": 10,
  "pressure_unit": "PSI", // PSI, BAR, KPA
  "ph": 4.12,
  "bpm": 123, // Bubbles Per Minute
  "comment": "Hello World",
  "beer": "Pale Ale",
  "battery": 4.98
}
"""

if needs_send:
    print("Update brewfather")
    data = {
        "name": "Red",  
        "temp": current_temp,
        "temp_unit": "F",
        "gravity": (current_gravity / 1000.0)
    }
    print(data)
    response = urequests.post(BREWFATHER_URL, json=data)
    print(response.text)
    #TODO: Handle failure?

if needs_display:
    display.display()    

rtcdata = {
    "lastupdate": time.time(),
    "temp": current_temp,
    "gravity": current_gravity,
    "imgfile": png_file_path
}
rtc.memory(json.dumps(rtcdata))

if not debug:
    machine.deepsleep(sleep_minutes * 60 * 1000)
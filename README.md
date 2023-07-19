# tiltplate
Homebrewing Display (Tilt controller and "Currently On Tap" Display) for Inkplate 2 in micropython

I got an Inkplate 2 on kickstarter and needed to find a use for it.

This micropython code loads a png image from brewbunny.com, converts it to the 3 color titlplate format and displays it. 
If a tilt hydrometer sensor is found (currently only one is supported, because I have only one), the gravity and
temp will be also shown on the eink display and transmitted to brewfather.
Then it sends the ESP32 to deep sleep for a specified time. The image will only be loaded on first run to save battery,
so if the image changes online, a reset must be performed manually. Maybe I'll change this if the battery last long enough.

### TODO:
* Attach a battery so the display does not need a cable
* Print a tap handle enclosure (so the current beer can always be displayed on the tap handle)
* Maybe attach a temperature sensor to measure fridge temp (though this will add a cable again...)
* Check how long it runs on one battery load


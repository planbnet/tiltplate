import ntptime
from machine import RTC
import utime

# Function to check if it is currently in summer time
def is_summer_time(t):
    # Check if it is in the range of possible DST (March to October)
    if 3 <= t[1] <= 10:
        # Get the last Sunday of March and October
        if t[1] == 3: 
            dst_start = utime.mktime((t[0], 3, 31 - (5 + t[0]*5//4)%7, 3, 0, 0, 0, 0))
            return t[7] >= dst_start
        elif t[1] == 10:
            dst_end = utime.mktime((t[0], 10, 31 - (2 + t[0]*5//4)%7, 3, 0, 0, 0, 0))
            return t[7] < dst_end
        # If it's April to September, it's DST
        else:
            return True
    else:
        return False

def update_time():
    # Get UTC time from NTP server
    ntptime.settime()
    rtc = RTC()
    # Get UTC time tuple
    utc_time = rtc.datetime()
    # Calculate timezone offset in seconds (3600 per hour)
    offset = 3600 * (2 if is_summer_time(utc_time) else 1)
    # Convert UTC datetime tuple to seconds since epoch
    utc_seconds = utime.mktime(utc_time)
    # Apply the offset (add for CET/CEST)
    local_seconds = utc_seconds + offset
    # Convert the result back into a time tuple
    local_time = utime.localtime(local_seconds)
    # Set the RTC to the local time
    rtc.datetime(local_time)
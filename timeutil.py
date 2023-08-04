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
    rtc_time = rtc.datetime()
    # Calculate timezone offset in seconds (3600 per hour)
    offset = 3600 * (2 if is_summer_time(rtc_time) else 1)

    # Convert UTC datetime tuple to seconds since epoch
    # work around a bug in rtc, which stores values of time tuple wrong
    utc_seconds = utime.mktime( (rtc_time[0], rtc_time[1], rtc_time[2], rtc_time[4], rtc_time[5], rtc_time[6], 0, 0) )

    # Apply the offset (add for CET/CEST)
    local_seconds = utc_seconds + offset
    # Convert the result back into a time tuple
    local_time = utime.localtime(local_seconds)

    new_time = (local_time[0], local_time[1], local_time[2], local_time[6], local_time[3], local_time[4], local_time[5], local_time[7]) 

    # Set the RTC to the local time, revert the bug
    rtc.datetime(new_time)

def format_time(timestamp):
  local_time = utime.localtime(timestamp)
  hours = local_time[3]
  minutes = local_time[4]
  return "{:02d}:{:02d}".format(hours, minutes)
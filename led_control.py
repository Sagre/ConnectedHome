#!/usr/bin/env python3
# Author: Tony DiCola (tony@tonydicola.com)
# Adapted by: Daniel Habering (daniel@habering.de)
#
# Taken from https://github.com/rpi-ws281x/rpi-ws281x-python/tree/master/examples

import time
from rpi_ws281x import PixelStrip, Color
import argparse
from Communication import Comm

# LED strip configuration:
LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

strip = None

power = "off"
mode = "color"
rgb_values = []


# Define functions which animate LEDs in various ways.
def colorWipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms/1000.0)



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--leds', type=int, default=100,
                        help='Numbers of LEDs in chain')
    parser.add_argument('--freq', type=int, default=10, help='Time in ms between each LED update')
    return parser.parse_args()

def set_led_color(led_color_command):
    global rgb_values

    print(led_color_command)
    # Parse LED Id and required rgb values from recieved command
    if "id" not in led_color_command:
        print("LED \"id\" not found in led_color_command: " + str(led_color_command))
        return
    else:
        led_id = int(led_color_command["id"])

    if led_id >= len(rgb_values):
        print("Id: " + str(led_id) + " is exceeding the configured number of LEDs")
        return

    if "rgb" not in led_color_command or len(led_color_command["rgb"]) != 3:
        print("No valid LED \"rgb\" found in led_color_command: " + str(led_color_command))
        return
    else:
        [r, g, b] = led_color_command["rgb"]
        [r, g, b] = [r * 255, g *255, b * 255]

    rgb_values[led_id] = [r,g,b]

def update_rgb_values():
    global rgb_values,strip,power,mode

    if power == "on" and mode == "sound":
        for i,[r,g,b] in enumerate(rgb_values):
            strip.setPixelColor(i,Color(r,g,b))
        strip.show()

# Callback of led_control commands. Expects a dict of the form:
# {"id": id, "val": val}
# where id denotes the setting and val the required value of that setting
def led_control(led_control_command):
    global power, mode
    # Disabled/Enable LED strip, switch mode
    if led_control_command["id"] == "led_power":
        if led_control_command["val"] == "on":
            power = "on"
            colorWipe(strip, Color(255,255,255), 10)
        if led_control_command["val"] == "off":
            power = "off"
            colorWipe(strip, Color(0,0,0), 10)
    elif led_control_command["id"] == "led_mode":
        mode = led_control_commend["val"]

# Main program logic follows:
if __name__ == '__main__':
    args = parse_args()

    # Create NeoPixel object with appropriate configuration.
    strip = PixelStrip(int(args.leds), LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    # Intialize the library (must be called once before other functions).
    strip.begin()

    for i in range(int(args.leds)):
        rgb_values.append([255,255,255])
    
    comm = Comm("LedControl")
    print("Wait for MQTT to connect to broker...")
    while not comm.is_connected():
        pass
    print("connected")
    comm.subscribe("rgb_values", set_led_color)
    comm.subscribe("led_request", led_control)

    print('Press Ctrl-C to quit.')
    try:
        while True:
            time.sleep(int(args.freq)/1000)
            update_rgb_values()
            pass
    except KeyboardInterrupt:
        colorWipe(strip, Color(0, 0, 0), 10)


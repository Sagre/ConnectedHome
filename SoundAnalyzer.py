#!/usr/bin/env python3
# Author: Daniel Habering (daniel@habering.de)
# Using PyAudio to listen to audio device.
# Apply predefined filters to map audio frequency amplitudes to LED color strip

import argparse
import time
import pyaudio
import struct
import numpy as np
import matplotlib.pyplot as plt
import collections
import threading
from scipy import signal
from Filter import UniformFilter
from Communication import Comm

# Number of LED/RGB Points
LED_count = 100

# Filters used to determine the amount of a specific colour
blueFilter = UniformFilter(center = 50, width = 50, colour = (0, 0, 1))
greenFilter = UniformFilter(center = 350, width = 150, colour = (0, 1, 0))
yellowFilter = UniformFilter(center = 1000, width =500, colour = (1, 1, 0))
redFilter = UniformFilter(center = 3000, width =1000, colour = (1, 0, 0))

filters = [blueFilter, greenFilter, yellowFilter, redFilter]

# Determines how many of the last results are averaged in order to smooth input
input_smooth_window = 3

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', type=int, default=None, dest='device',
                        help='pyaudio (portaudio) device index')
    parser.add_argument('--viz', action='store_true')
    parser.add_argument('--remove_mic_noise', action='store_true')
    return parser.parse_args()

class Vizualizer:
    fig = None
    ax = None
    led = None
    line = None
    ax_background = None
    led_background = None

    def update_viz(self, freq, result, rgb_values):
        self.fig.canvas.restore_region(self.led_background)
        self.fig.canvas.restore_region(self.ax_background)
        if self.line is None:
            self.line, = self.ax.plot(freq, result, 'r-')
        else:
            self.line.set_ydata(result)
            self.line.set_xdata(freq)
            self.ax.draw_artist(self.line)

        self.led.cla()
        for i, rgb in enumerate(rgb_values):
            self.led.scatter(i, 1, color=rgb)

        self.fig.canvas.blit(self.ax.bbox)
        self.fig.canvas.blit(self.led.bbox)

        self.fig.canvas.flush_events()

    def __init__(self, rate):
        plt.ion()
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlim(10, rate)
        self.ax.set_xscale('log')
        self.ax.set_ylim(-50, 100)
        self.ax.set_title("Fast Fourier Transform")

        self.led = self.fig.add_subplot(222)
        self.led.set_xlim(0, LED_count)
        self.led.set_ylim(0, 2)
        self.led.set_title("Led Output")

        self.ax_background = self.fig.canvas.copy_from_bbox(self.ax.bbox)
        self.led_background = self.fig.canvas.copy_from_bbox(self.led.bbox)

class SoundAnalyzer:
    stream = None
    chunk = None

    freq_buffer = None
    window = np.hanning(0)
    fft_freq = []

    filters = []

    mic_noise_fft = None
    mic_noise_count = 0

    comm = None

    def publish_rgb(self, rgb_values):
        for i,rgb in enumerate(rgb_values):
            self.comm.publish("rgb_values", {"id": i, "rgb": rgb})

    def colorVectorToRgbValues(self, colorVector):
        result = []
        # Check if colorVector is unitsized, which is needed to match it to the LED chain
        # Deal with floating point errors by checking against threshold
        if abs(sum(colorVector) - 1.0) > 0.00001:
            raise ValueError("Sum of filter responses needs to be == 1: " + str(colorVector) + " -> " + str(sum(colorVector)))

        for i in range(LED_count):
            j = 0
            # Search for Color range this LED belongs to
            while (i / LED_count) > sum(colorVector[:(j+1)]):
                j = j+1
                if j >= len(filters):
                    raise ValueError("For LED " + str(i/LED_count) + " no filter response " + str(colorVector))
            result.append(filters[j].colour)

        return result

    # Reads sound data from input stream, calculates frequencies and amplitudes
    # Discards a subset of frequencies (e.g. every second), in order to reduce
    # complexity
    def collect_values(self):
        data = self.stream.read(self.CHUNK, exception_on_overflow=False)

        data = np.frombuffer(data, np.int16)

        if self.CHANNELS == 2:
            # data has 2 bytes per channel
            # pull out the even values, just using left channel
            data = np.array(data[::2])

        # if you take an FFT of a chunk of audio, the edges will look like
        # super high frequency cutoffs. Applying a window tapers the edges
        # of each end of the chunk down to zero.
        if len(data) != len(self.window):
            self.window = np.hanning(len(data)).astype(np.float32)

        data = data * self.window
        fft_result = np.fft.rfft(data)

        # If len of amplitudes does not match the stored frequency list, recalculate frequencies
        if len(fft_result) != len(self.fft_freq):
            self.fft_freq = np.fft.rfftfreq(self.CHUNK, 1 / self.RATE)

        # Scale the magnitude of FFT by window and factor of 2,
        # because we are using half of FFT spectrum.
        fft_result = np.abs(fft_result) * 2 / np.sum(self.window)
        # Convert to dBFS
        fft_result = 20 * np.log10(fft_result / 32768)

        # Smooth result by averaging over last x results
        self.freq_buffer.append(fft_result)
        fft_result = np.average(self.freq_buffer, axis=0)

        return fft_result, self.fft_freq

    def calc_mic_noise(self):
        fft_result, _ = self.collect_values()
        if self.mic_noise_count == 0:
            # First spectrum to calculate mic noise
            self.mic_noise_fft = fft_result
            self.mic_noise_count += 1
        else:
            # Iterative averaging
            self.mic_noise_count += 1
            tmp = np.subtract(fft_result, self.mic_noise_fft)
            tmp = tmp / self.mic_noise_count
            self.mic_noise_fft = np.add(self.mic_noise_fft, tmp)

    def run(self):
        fft_result, fft_freq = self.collect_values()
        # Remove previous calculated mic noise (is 0, if feature is disabled)
        fft_result = fft_result - self.mic_noise_fft

        # Move amplitudes relative to smalles amplitude (so every amplitude >= 0)
        fft_result = fft_result - min(fft_result)

        colorVector = []
        # Calculate response of each filter
        for f in filters:
            colorVector.append(f.get_filtered_result(fft_result, fft_freq))
        # Resize color vector to unit size -> Sum should be one, in order to match LED colors
        colorVectorLength = sum(colorVector)
        colorVector_normed = colorVector / colorVectorLength

        rgb_values = self.colorVectorToRgbValues(colorVector_normed)

        self.publish_rgb(rgb_values)

        if self.viz != None:
            self.viz.update_viz(fft_freq, fft_result, rgb_values)

    # Initialize audio stream. If no device argument is passed, grab all audio devices and let the user select
    # If visualization is activated, create the empty graph windows
    def __init__(self, viz):
        self.comm = Comm("SoundAnalyzer")
        while not self.comm.is_connected():
            pass

        mic = pyaudio.PyAudio()

        if args.device == None:
            # Print all available sound devices
            numdevices = mic.get_host_api_info_by_index(0).get('deviceCount')
            for i in range(0, numdevices):
                if (mic.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                    print(
                        "Input Device id ",
                        i,
                        " - ",
                        mic.get_device_info_by_host_api_device_index(0, i))
            # Ask for user input to select an audio device
            device_id = int(input("Please select microphone device: "))
        else:
            device_id = int(args.device)

        device_info = mic.get_device_info_by_index(device_id)

        FORMAT = pyaudio.paInt16
        self.CHANNELS = device_info["maxInputChannels"] if (
            device_info["maxOutputChannels"] < device_info["maxInputChannels"]) else device_info["maxOutputChannels"]
        self.RATE = int(device_info["defaultSampleRate"])
        self.CHUNK = 1024

        # Open audio stream with default settings
        self.stream = mic.open(format=FORMAT,
                               channels=self.CHANNELS,
                               rate=self.RATE,
                               input=True,
                               frames_per_buffer=self.CHUNK,
                               input_device_index=device_id)

        self.freq_buffer = collections.deque(maxlen = input_smooth_window)

        # Create visualization window, if activated
        if viz == True:
            self.viz = Vizualizer(self.RATE)
        else:
            self.viz = None


if __name__ == "__main__":
    args = parse_args()
    sa = SoundAnalyzer(args.viz)
    if args.remove_mic_noise:
        try:
            while True:
                print("Start collecting microphone noise. There should be no sound playing during this.")
                print("Stop using Strg + C")
                sa.calc_mic_noise()
        except KeyboardInterrupt:
            print("Stopping collecting mic noise")
    else:
        sa.mic_noise_fft = 0

    while True:
        sa.run()

import numpy as np

# Abstract class, defining a filter to be used on frequency spectrum


class Filter:
    center = 0
    width = 0
    constant = 0

    result_buffer = []
    freq_buffer = []

    colour = (0,0,0)

    # actual filter method, returning a weight for a given frequency
    def filter_mask(self, x):
        pass

    # Called once when Filter object is created. Used to precalculate any
    # filter mask constants
    def init_filter(self):
        pass

    # Calculates the filter applied to a given set of amplitudes/frequencies
    # amplitudes - amplitudes of the frequencies
    # freq - list of frequencies. Has to have the same size as amplitudes
    def get_filtered_result(self, amplitudes, freq):
        # Ensure that frequency and amplitude list has the same size
        if len(amplitudes) != len(freq):
            raise ValueError(
                str("List of frequencies does not have the same length as list of amplitudes: {} != {} ").format(
                    len(amplitudes), len(freq)))
        # Check if frequency list matches previous lists. If yes, filter mask can be reused
        if not np.array_equal(freq, self.freq_buffer):
            self.freq_buffer = freq
            for f in freq:
                self.result_buffer.append(self.filter_mask(f))

        # Apply filter mask to amplitudes, by summing up the product of amplitude and mask value
        result = 0

        for i, v in enumerate(amplitudes):
            # Assuming that the filter mask has a single area, we can terminate early if we have moved over the filter area
            if result > 0 and self.result_buffer[i] < 0.0000001:
                break
            if v < 0:
                raise ValueError("Negative amplitude " + str(v) + " for frequency " + str(freq[i]) + " is not allowed")
            result += self.result_buffer[i] * v
        return result

    def __init__(self, center, width, colour):
        self.center = center
        self.width = width
        self.result_buffer = []
        self.freq_buffer = []

        self.colour = colour

        self.init_filter()

# Gaussian filter mask, with center = mean, width = sigma/std dev
class GaussianFilter(Filter):
    def filter_mask(self, x):
        value = self.constant * \
            np.exp(-np.power((x - self.center) / self.width, 2.) / 2)
        return value

    def init_filter(self):
        self.constant = 1. / (np.sqrt(2. * np.pi) * self.width)

# Uniform filter, returning the average amplitude in the window [center - width, center + width]
class UniformFilter(Filter):
    def filter_mask(self, x):
        if x > self.center - self.width and x < self.center + self.width:
            value = 1/ (2*self.width)
        else:
            value = 0
        return value

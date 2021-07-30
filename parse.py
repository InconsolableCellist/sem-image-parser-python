from enum import Enum
import RigolWFM.wfm as rigol
from PIL import Image
import numpy as np

from RingBuffer import RingBuffer

# filename = 'waveforms/newfile16 ch0 video-ch1 xy sync-trigger ext y-zoomed in high emission.wfm'
# filename = 'waveforms/newfile14 ch0 video-ch1 xy sync-trigger ext y-zoomed in high emission.wfm'
filename = 'waveforms/newfile23 ch0 tp0-ch1 xy sync-trigger ext y-half speed.wfm'
scope = 'DS1000E'

class State(Enum):
    UNKNOWN = 0
    DATA = 1
    BLANK = 2

w = rigol.Wfm.from_file(filename, scope)

blank_width_x_seconds = 0.0000688
blank_width_y_seconds = 0.0284

# logical 1
signal_threshold = 32768

seconds_per_point = w.channels[1].seconds_per_point
min = w.channels[1].volts.min()
max = w.channels[1].volts.max()
sync_bias = 0
if min < 0:
    sync_bias = -1 * min
    max += sync_bias
    min += sync_bias
state = State.UNKNOWN

video_min = w.channels[0].volts.min()
video_max = w.channels[0].volts.max()
video_bias = 0
if video_min < 0:
    video_bias = -1 * video_min
    video_max += video_bias
    video_min += video_bias

blank_duration = 0
data_duration = 0

n = 4
last_n_values = RingBuffer(n)

data_counter = 0
img_data = np.zeros((2600, 26000, 3), dtype=np.uint8)
row_number = 0

for value in w.channels[1].volts:
    data_counter += 1
    normalized_value = (value - min) / (max - min)
    normalized_value *= 65536
    last_n_values.append(normalized_value)

    if state == State.UNKNOWN:
        if normalized_value >= signal_threshold:
            state = State.DATA
        else:
            state = State.BLANK

    if state == State.BLANK:
        blank_duration += 1
        if last_n_values.average() >= signal_threshold:
            row_number += 1
            state = State.DATA
            print("blank -> data. duration {} ({}s)".format(blank_duration, blank_duration*seconds_per_point))
            blank_duration = 0
    elif state == State.DATA:
        image_value = w.channels[0].volts[data_counter - 1] + video_bias
        image_value = (image_value - video_min) / (video_max - video_min)
        image_value *= 65536
        new_value = np.uint8(image_value / 255)
        img_data[row_number, data_duration] = [new_value, new_value, new_value]
        data_duration += 1

        if last_n_values.average() < signal_threshold:
            state = State.BLANK
            print("data -> blank. duration {} ({}s)".format(data_duration, data_duration * seconds_per_point))
            data_duration = 0

img = Image.fromarray(img_data)
# img.show()
img.save("img1.png")
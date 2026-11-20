"""Every pin, channel, geometry and tuning constant in one place.

Distances are metres, frequencies hertz. The coordinate frame is the staff's:
x points to your RIGHT as you hold it (board face toward you), y points UP,
and the origin is the bottom tip of the board. A buried line therefore sits
at negative y. The line runs along z, straight away from you, and z position
doesn't matter for a long straight line, which is why the vertical coils can
sit on the back face of the board, a couple of centimetres behind the
horizontal ones.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ------------------------------------------------------------------ audio --
SAMPLE_RATE = 96000          # Hz; 33 kHz needs at least 66 kHz (Nyquist)
BLOCK = 4800                 # samples per channel per block: 50 ms
CHANNELS = 4
# The UMC404HD shows up in ALSA as a card whose id contains one of these.
AUDIO_CARD_HINTS = ("U192k", "UMC404", "UMC")
# Set to a full ALSA name, e.g. "plughw:CARD=U192k,DEV=0", to skip the search.
AUDIO_DEVICE = None
CLIP_LEVEL = 0.95            # fraction of full scale that counts as overload

# ------------------------------------------------------------------ coils --
# Interface input (1 to 4) minus one = index here. Positions are the centres
# of each coil's winding, measured from the board's bottom tip.
COILS = [
    {"ch": 0, "name": "bottom H", "x": 0.0, "y": 0.10, "axis": "x"},
    {"ch": 1, "name": "bottom V", "x": 0.0, "y": 0.10, "axis": "y"},
    {"ch": 2, "name": "top H", "x": 0.0, "y": 0.60, "axis": "x"},
    {"ch": 3, "name": "top V", "x": 0.0, "y": 0.60, "axis": "y"},
]
# A 100 mm rod collects flux over roughly its middle 70 mm. The model averages
# the field over this span so shallow lines aren't misjudged.
ROD_EFFECTIVE_HALF = 0.035
ROD_SAMPLES = 5
TIP_HEIGHT = 0.0             # tip held on the ground; raise if you hover it

# ------------------------------------------------------------------ modes --
# cal_key: which calibration in cal.json the mode uses. Power mode borrows the
# 90 Hz calibration: a 60 Hz test tone would be swamped by the hum from every
# wire in the neighbourhood, while 90 Hz sits halfway between the hum's 60 and
# 120 Hz. Down here every coil's output is simply proportional to frequency,
# so the coils' gains RELATIVE to each other are the same at 60 and 90 Hz.
MODES = [
    {"key": "8k", "label": "8 kHz", "freq": 8192.0, "search": 60.0, "cal_key": "8192"},
    {"key": "33k", "label": "33 kHz", "freq": 32768.0, "search": 60.0, "cal_key": "32768"},
    {"key": "power", "label": "60 Hz POWER", "freq": 60.0, "search": 0.0, "cal_key": "90"},
]
CAL_FREQS = {"8192": 8192.0, "32768": 32768.0, "90": 90.0}
# Noise is measured this far above the signal. 40 Hz is exactly two bins of
# a 50 ms block, so the signal itself contributes nothing there. If that lands
# within 15 Hz of a mains harmonic, NOISE_OFFSET_ALT_HZ (3 bins) is used.
NOISE_OFFSET_HZ = 40.0
NOISE_OFFSET_ALT_HZ = 60.0

# ------------------------------------------------------------- processing --
TAU = 0.4                    # s, smoothing time constant
UPDATE_HZ = 4                # screen and depth updates per second
MIN_SNR_DB = 20.0            # below this, show signal strength but no depth
MODEL_FLOOR = 0.002          # no channel is trusted beyond 0.2 % of the strongest
DISTORT_REL = 0.08           # misfit above 8 % of the signal = distorted
DISTORT_CHI2 = 9.0           # ...and well above what noise alone explains
SEARCH_X = (-3.0, 3.0)       # m, where the solver looks for the line
SEARCH_DEPTH = (0.0, 4.0)    # m below the tip (0 = a wire lying on the ground)
UNITS = "imperial"           # or "metric"

# ------------------------------------------------------------------ Pi pins --
SPI_BUS, SPI_DEV = 0, 1      # SPI0; CE1 (pin 26) toggles but goes nowhere
SPI_HZ = 1_000_000
DISPLAY_CS_GPIO = 25         # pin 22 -> display CS (active HIGH)
BUZZER_GPIO = 18             # pin 12 -> 100 ohm -> piezo +
BTN_MODE_GPIO = 5            # pin 29 -> MODE button -> GND
BTN_SOUND_GPIO = 6           # pin 31 -> SOUND button -> GND
DISPLAY_W, DISPLAY_H = 400, 240
DISPLAY_MIRROR = False       # set True if text shows up mirrored
DISPLAY_INVERT = False       # set True if the screen shows white on black

# ----------------------------------------------------------- calibration --
CAL_FILE = os.path.join(REPO, "cal.json")
# Where the calibration wire sits relative to the tip, metres: negative = the
# wire is to your LEFT. Kept at 0.5 m or more so the coils' length hardly
# matters and the field is close to that of an ideal line.
CAL_POSITIONS = [-0.8, -0.5, 0.5, 0.8]
CAL_WIRE_Y = -0.003          # wire lying on the ground, tip on the ground
CAL_SETTLE_S = 1.0
CAL_AVERAGE_S = 3.0
CAL_MIN_SNR_DB = 30.0
CAL_MAX_FIT_ERR = 0.03       # per-channel fit error above 3 % is a warning

"""Two buttons and a piezo buzzer.

The buzzer chirps five times a second. Its pitch climbs with signal strength,
so you can keep your eyes on the ground and sweep by ear, the way pros do.
Directly over the line (within 5 cm) it double-chirps; in power mode it
double-chirps AT PEAK. Hold SOUND for a second to reset power mode's peak.
"""
from . import config


class Controls:
    def __init__(self, enabled=True):
        self.mode_presses = 0
        self.sound_presses = 0
        self.resets = 0
        self._held = False
        self.buzzer = None
        self.ok = False
        if not enabled:
            return
        try:
            from gpiozero import Button, PWMOutputDevice
            self._mode = Button(config.BTN_MODE_GPIO, pull_up=True, bounce_time=0.05)
            self._sound = Button(config.BTN_SOUND_GPIO, pull_up=True, bounce_time=0.05,
                                 hold_time=1.0)
            self._mode.when_pressed = self._on_mode
            # a tap toggles the sound; holding it for a second resets the peak
            self._sound.when_held = self._on_sound_held
            self._sound.when_released = self._on_sound_released
            self.buzzer = PWMOutputDevice(config.BUZZER_GPIO, frequency=1000, initial_value=0)
            self.ok = True
        except Exception as e:  # no GPIO (not a Pi, or gpiozero missing)
            self.error = str(e)

    def _on_mode(self):
        self.mode_presses += 1

    def _on_sound_held(self):
        self._held = True
        self.resets += 1

    def _on_sound_released(self):
        if not self._held:
            self.sound_presses += 1
        self._held = False

    def take_reset(self):
        n, self.resets = self.resets, 0
        return n

    def take_mode(self):
        n, self.mode_presses = self.mode_presses, 0
        return n

    def take_sound(self):
        n, self.sound_presses = self.sound_presses, 0
        return n

    def tone(self, freq_hz):
        """Start a tone (or stop it with 0). Call every block to make chirps."""
        if not self.buzzer:
            return
        if freq_hz <= 0:
            self.buzzer.value = 0
        else:
            self.buzzer.frequency = freq_hz
            self.buzzer.value = 0.5

    def close(self):
        if self.buzzer:
            self.buzzer.value = 0


def pitch_for(snr_db):
    """400 Hz at the noise floor up to 3.2 kHz at 60 dB above it."""
    snr = max(0.0, min(60.0, snr_db))
    return 400.0 * (2.0 ** (3.0 * snr / 60.0))

"""PowerlineLocator transmitter firmware (MicroPython on a Raspberry Pi Pico).

Copy this file to the Pico as main.py (Thonny: File > Save as > Raspberry Pi
Pico). It starts by itself at power-on.

What it does: drives a DRV8871 H-bridge so the output terminals swing
+V, 0, -V, 0, +V ... at 8192 Hz, 32768 Hz or 90 Hz. The timing comes from one
of the Pico's PIO state machines, so it's rock steady whatever Python is doing.

    FREQ button  (GP14): 8 kHz -> 33 kHz -> 90 Hz CAL -> 8 kHz ...
    LEVEL button (GP15): HIGH -> MED -> LOW -> HIGH ...
    LEDs: green GP2 = 8 kHz, yellow GP3 = 33 kHz, red GP4 = 90 Hz CAL
          steady = HIGH, slow blink = MED, fast blink = LOW

The waveform: each half cycle is "drive" for a fraction alpha of the time,
then "zero" (both low-side switches on). Its fundamental, the only part the
receiver listens to, has amplitude

    A1 = (4 V / pi) * sin(pi * alpha / 2)

so alpha = 1, 0.5, 0.25 give 100 %, 71 % and 38 % of full output.
"""
try:
    import rp2
    from machine import Pin
    import time
    ON_PICO = True
except ImportError:          # imported by selftest.py on a normal computer
    ON_PICO = False

SM_FREQ = 8_388_608          # 2**23 Hz: 8192 and 32768 come out exact
FREQS = (8192, 32768, 90)   # 90 Hz (+0.001 Hz) is only for calibrating power mode
LEVELS = (1.0, 0.5, 0.25)    # alpha for HIGH, MED, LOW
OVERHEAD = 3                 # PIO cycles each phase spends on set + mov + exit


def phase_counts(freq, alpha, sm_freq=SM_FREQ):
    """Loop counts (drive, zero) for the PIO program, and the exact frequency.

    One half cycle is (drive + 3) + (zero + 3) PIO cycles.
    """
    half = int(round(sm_freq / (2 * freq)))
    drive_cycles = int(round(alpha * half))
    drive_cycles = max(OVERHEAD + 1, min(half - OVERHEAD, drive_cycles))
    zero_cycles = half - drive_cycles
    return drive_cycles - OVERHEAD, zero_cycles - OVERHEAD, sm_freq / (2.0 * half)


if ON_PICO:
    @rp2.asm_pio(set_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW))
    def tri_level():
        pull(block)             # first word: zero count
        mov(isr, osr)
        pull(block)             # second word: drive count, stays in OSR
        wrap_target()
        set(pins, 1)            # IN1 high, IN2 low: output +V
        mov(x, osr)
        label("pos")
        jmp(x_dec, "pos")
        set(pins, 3)            # both high: both low-side on, output 0 V
        mov(y, isr)
        label("z1")
        jmp(y_dec, "z1")
        set(pins, 2)            # IN1 low, IN2 high: output -V
        mov(x, osr)
        label("neg")
        jmp(x_dec, "neg")
        set(pins, 3)
        mov(y, isr)
        label("z2")
        jmp(y_dec, "z2")
        wrap()

    class Transmitter:
        def __init__(self):
            self.leds = [Pin(n, Pin.OUT, value=0) for n in (2, 3, 4)]
            self.btn_freq = Pin(14, Pin.IN, Pin.PULL_UP)
            self.btn_level = Pin(15, Pin.IN, Pin.PULL_UP)
            self.heartbeat = Pin(25, Pin.OUT, value=0)
            self.sm = rp2.StateMachine(0)
            self.fi, self.li = 0, 0
            self.apply()

        def stop(self):
            # both inputs low puts the DRV8871 to sleep: outputs open
            self.sm.exec("set(pins, 0)")
            self.sm.active(0)

        def apply(self):
            self.sm.active(0)
            drive, zero, f = phase_counts(FREQS[self.fi], LEVELS[self.li])
            # re-init loads the program (once) and hands GP0/GP1 to the PIO
            self.sm.init(tri_level, freq=SM_FREQ, set_base=Pin(0))
            self.sm.restart()
            self.sm.put(zero)
            self.sm.put(drive)
            self.sm.active(1)
            print("output %.2f Hz, level %s" % (f, ("HIGH", "MED", "LOW")[self.li]))

        def pressed(self, pin):
            if pin.value() == 0:
                time.sleep_ms(30)
                if pin.value() == 0:
                    while pin.value() == 0:
                        time.sleep_ms(10)
                    return True
            return False

        def run(self):
            t = 0
            while True:
                if self.pressed(self.btn_freq):
                    self.fi = (self.fi + 1) % len(FREQS)
                    self.apply()
                if self.pressed(self.btn_level):
                    self.li = (self.li + 1) % len(LEVELS)
                    self.apply()
                # steady for HIGH, 1 Hz blink for MED, 4 Hz blink for LOW
                period = (0, 1000, 250)[self.li]
                lit = True if period == 0 else (t % period) < period // 2
                for i, led in enumerate(self.leds):
                    led.value(1 if (i == self.fi and lit) else 0)
                self.heartbeat.value(1 if (t % 2000) < 100 else 0)
                time.sleep_ms(20)
                t += 20

    try:
        Transmitter().run()
    except KeyboardInterrupt:
        Pin(0, Pin.OUT, value=0)
        Pin(1, Pin.OUT, value=0)

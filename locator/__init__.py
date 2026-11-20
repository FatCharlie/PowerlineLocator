"""PowerlineLocator: a Raspberry Pi buried cable locator.

config     every pin, channel, geometry and tuning constant
lockin     software lock-in amplifier and frequency finder
geometry   line field model, depth solver, calibration fit
pipeline   blocks in, Estimate out; calibration file; unit formatting
audio      4-channel capture from the USB interface (ALSA)
display    Sharp Memory LCD driver and screen layout
controls   buttons and buzzer
sim        fake coil signals for running with no hardware
"""

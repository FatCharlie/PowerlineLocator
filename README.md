# PowerlineLocator

### Current stage: 0. Design done, simulation passes, nothing bought yet

**A Raspberry Pi buried cable locator you can build and lend out.** It finds buried power cables (and any other metal line you can put a signal on) down to 4 to 6 ft, shows how deep they are and which way to step, and warns you when the reading can't be trusted. It's meant for places where calling a locating contractor out for every post hole isn't realistic, and where one good tool can go round a whole neighbourhood.

It works the way commercial locators do: a **transmitter** puts a signal on the line, and a **receiver** staff with four pickup coils listens for it. A **power mode** needs no transmitter at all and listens for the 60 Hz a live, loaded cable already carries.

> **It does not replace 811.** In New Mexico, call 811 (or [nm811.org](https://www.nm811.org)) at least two working days before you dig; the utilities mark their own lines for free. This tool is for what they don't mark: the private lines from your meter to the well, the shop, the neighbour's barn. And whatever any locator says, the law here is to dig by hand within 18 in either side of a mark.

---

## Here's the whole build

```text
   TRANSMITTER (battery box)                       RECEIVER (a 4 ft staff)

   Raspberry Pi Pico                               ┌───────────────────────────┐
     │ makes 8 kHz / 33 kHz / 90 Hz                │ head box: Pi 4, Sharp     │
     ▼                                             │ screen, 2 buttons, buzzer │
   DRV8871 H-bridge ◄── 12 V LiFePO4               └────────────▲──────────────┘
     │ ±13 V square-ish wave                                    │ USB
     ▼                                             ┌────────────┴──────────────┐
   TVS clamp → 22 Ω → 1 A fuse                     │ Behringer UMC404HD        │
     │                                             │ 4 mic preamps + ADC       │
     ├── RED ──► dead line (direct)  ─┐            └──▲─────▲─────▲─────▲──────┘
     │      or ► clamp round a live   │               │ XLR │     │     │
     └── BLACK ► ground stake         │              top H  top V │     │   600 mm up
                                      │                           │     │
                                      ▼                        bottom H  bottom V   100 mm up
   ══════════════════════════ buried cable ══════════════════════════════════════
           signal current out along the cable, back through the earth
```

Pictures: [SCHEMATICS.md](SCHEMATICS.md). Parts with search phrases and links: [PARTS.md](PARTS.md). Step-by-step build for someone who has never wired anything: [for_dummies.md](for_dummies.md).

---

## How it works

### The field

A long straight wire carrying current I has a magnetic field that circles it:

**B = μ₀ I / (2π r)**

* **B:** magnetic flux density, in tesla.
* **μ₀ = 4π × 10⁻⁷ T·m/A:** the permeability of free space. Soil isn't magnetic, so it barely changes this; that's why locating works straight through dirt.
* **I:** the current on the line. Typically 20 to 200 mA from the transmitter.
* **r:** distance from the wire to the sensor.

The field points around the wire, not away from it. So a coil a horizontal distance x to the side and a height h above the wire sees two parts:

**Bx = k h / (x² + h²)    By = k x / (x² + h²)    with k = μ₀ I / (2π)**

Directly over the wire (x = 0) the vertical part By is zero and the horizontal part Bx is at its peak. Step off to one side and By grows, with a sign that says which side.

### Depth from a ratio

The staff has two horizontal coils, one d = 0.5 m above the other. Over the wire, the bottom one is at height h and the top one at h + d, so

**Bx(bottom) / Bx(top) = (h + d) / h  ⇒  h = d · Bx(top) / (Bx(bottom) − Bx(top))**

The current I is inside k, and it cancels. You never need to know how much current is on the line, which is the whole reason this works: the earth return path, the line's resistance and the ground stake are all unknowns, and none of them matter. (It's the same move as SlightlyCutGem's contrast measurement and a Bell test's correlation: divide one reading by another to cancel what you can't calibrate.)

The price is sensitivity. At 6 ft the two readings differ by only about 20 %, so a 1 % error in their ratio becomes about a 5 % error in depth. That's why the coils must be **calibrated** against each other to well under 1 % (`calibrate.py`), and why calibration is the hardest part of the build, not the electronics.

### Four coils, three unknowns, one spare

The software doesn't actually assume you're standing over the line. It has four readings (two horizontal, two vertical coils) and fits three unknowns: the line's sideways position x, its depth, and its strength k. That gives depth even when you're off to one side, and the left/right arrow.

The fourth reading is spare, and it's the most useful feature for a tool you lend out. A single straight line makes a field with a very particular shape; if the four readings don't fit that shape, something is bending the field: a second line, a fence, a tee, a bend, or signal coming back along a shallow wire. When the misfit is more than 8 % of the signal (and clearly more than noise), the screen says **DISTORTED, depth unreliable** and puts the depth in brackets.

**Known limit:** two parallel lines close together (closer than about half their depth) make a field that really does look like one line between them, and no four-coil locator can tell. The distortion check catches a line well off to the side or much shallower; it can't catch a pair in one trench.

### Hearing one frequency: the lock-in

Each coil's voltage, from Faraday's law, is

**V = N A μ_eff ω B**

* **N ≈ 1000:** turns of wire.
* **A ≈ 7.9 × 10⁻⁵ m²:** the rod's cross-section (10 mm diameter).
* **μ_eff ≈ 60:** how much the ferrite rod concentrates the field. It's set mostly by the rod's length-to-diameter ratio, not the ferrite's own permeability.
* **ω = 2πf:** the signal's angular frequency. Voltage grows with frequency, which is why locators use kilohertz, and why a coil can't see DC at all (ω = 0 gives V = 0).
* **B:** the field from above.

At 6 ft with 100 mA at 8 kHz that's a few millivolts, which is plenty. The receiver multiplies each channel by a sine and cosine at exactly the transmitter's frequency and averages (a software lock-in amplifier), which rejects everything else: 60 Hz hum, radio noise, the Pi's own switching. All four channels come from one ADC clock, so their relative phases are real: in phase means the line is on one side, opposite phase means the other.

### Power mode

A live cable carries hot and neutral side by side, with equal and opposite currents. Their fields mostly cancel, leaving a weaker **dipole** field that falls as 1/r² instead of 1/r (the next term of the same multipole pattern as a charge versus a dipole). What's left over, plus any current returning through the earth instead of the neutral, is enough to find a loaded line at 60 Hz. **The line has to be carrying current:** turn on a big load (well pump, heater, welder) at the far end.

Power mode borrows the coils' calibration from a 90 Hz tone, because a 60 Hz test tone would be drowned by the hum from every wire around. Down at 60 to 90 Hz each coil's output is simply proportional to frequency, so the gains *relative to each other*, which is all calibration measures, are the same.

### What it can't do

* **Plastic pipe** without a tracer wire is invisible to it. (Lay tracer wire over every new pipe you bury; it turns this from impossible into easy.)
* **DC** lines can't be found by their own current (see ω = 0 above). De-energise them and use the transmitter: then they're just wire.
* **Steel conduit** shields the clamp; use direct connection on the dead line instead.

---

## Hardware

Full list with search phrases, links and prices: [PARTS.md](PARTS.md). Every drawing and wiring table: [SCHEMATICS.md](SCHEMATICS.md).

| Block | Parts | Why this part |
|---|---|---|
| Coils | 4 × hand-wound ferrite rods, 1000 turns of 30 AWG, copper-foil shields | Cheap, sensitive, and you can wind them in an afternoon |
| Preamps + ADC | Behringer UMC404HD USB audio interface | Four low-noise mic preamps on one 24-bit, 96 kHz clock; replaces a custom analogue board |
| Brain | Raspberry Pi 4 | numpy lock-in and depth fit, 4 updates a second |
| Screen | Adafruit Sharp Memory LCD 2.7" (4694) | Reflective: readable in full sun |
| Controls | MODE and SOUND buttons, passive piezo buzzer | The buzzer's pitch rises with signal, so you can sweep by ear |
| Transmitter | Pi Pico + DRV8871 H-bridge, 12.8 V LiFePO4 | PIO-timed three-level wave at 8192 Hz, 32768 Hz or 90 Hz; three power levels |
| Protection | 22 Ω 25 W, 1 A fast fuse, 1.5KE20CA TVS, 3 A battery fuse | Survives RED touching a live 240 V wire |
| Clamp | 2 × Fair-Rite 0431177081 split cores, 10 turns | Signal onto a live cable with no contact |

---

## Software

```
RPI_SETUP.sh     one-time Pi setup: SPI, packages, groups, boot service (run with sudo)
lockdown.sh      make the SD card read-only for lending (on/off/status)
locate.py        the locator; the boot service runs it
calibrate.py     measures the four coils' gains against a wire on the ground
check_hw.py      hardware check: tests every part and says what's ready
selftest.py      checks the software with no hardware attached
locator/
  config.py      every pin, coil position and threshold, in one place
  lockin.py      lock-in amplifier, frequency finder, coherent averaging
  geometry.py    line field model, depth fit, distortion test, calibration fit
  pipeline.py    blocks in, depth out; calibration file; feet-and-inches
  audio.py       4-channel capture from the interface (ALSA)
  display.py     Sharp Memory LCD driver and the screen layout
  controls.py    buttons and buzzer
  sim.py         simulated coils, so everything runs without hardware
transmitter/
  main.py        MicroPython firmware for the Pico
docs/schematics/
  make_schematics.py   draws every SVG in SCHEMATICS.md
```

No test framework: everything is a plain `python3 <script>.py`. Dependencies are all apt packages (numpy, alsaaudio, spidev, gpiozero, Pillow).

### Try it with no hardware

On any computer with Python 3, numpy and Pillow:

```bash
python3 selftest.py                                   # 50 checks, about a second
python3 locate.py --sim                               # a line 5 ft down, staff sweeping across it
python3 locate.py --sim --sim-depth 1.2 --sim-second 0.8   # add a shallow return line: DISTORTED
python3 locate.py --sim --mode power
python3 calibrate.py --sim                            # rehearse calibration
```

### Setup on the Pi (Raspberry Pi OS Bookworm)

```bash
git clone https://github.com/FatCharlie/PowerlineLocator
cd PowerlineLocator
sudo ./RPI_SETUP.sh
sudo reboot
```

Then:

```bash
python3 selftest.py
sudo systemctl stop powerline-locator     # the boot service holds the interface; free it for the checks
python3 check_hw.py --interactive         # every part, with you watching the screen and pressing buttons
python3 check_hw.py --live                # coil test: wave each coil near a lamp cord
python3 calibrate.py                      # once, on a calibration wire (for_dummies.md, Part 9)
./lockdown.sh on && sudo reboot           # read-only SD card for lending
```

### The screen

| Shows | Means |
|---|---|
| `4' 7"` and `< 7 in` | Line is 4 ft 7 in below the tip, 7 in to your left. Step left. |
| `ON LINE` | You're within 2 in of directly over it. The buzzer double-chirps. |
| `(4' 7")` and **DISTORTED** | The field doesn't look like one straight line. Don't trust the depth; see for_dummies.md, "Reading DISTORTED". |
| **WEAK SIGNAL** | Less than 20 dB above the noise. Move closer, turn the transmitter to HIGH, check the stake. |
| **OVERLOAD** | Something is close to clipping the inputs: usually overhead lines or house wiring. Move away. |
| **NOT CALIBRATED** | No calibration for this mode yet: run calibrate.py. Signal strength still works. |

The bar is signal above noise, 0 to 60 dB. MODE cycles 8 kHz → 33 kHz → 60 Hz power. SOUND turns the buzzer on and off.

### Which frequency

* **8 kHz:** the default for direct connection. Travels far along the line and bleeds onto neighbouring lines least.
* **33 kHz:** for the clamp (couples much better), and for lines with poor connections or no good ground at the far end.
* **60 Hz power:** no transmitter; the line must be live and loaded.
* **90 Hz CAL:** only for calibrating power mode.

The Pico's crystal puts the transmitter a few hertz off nominal; the receiver finds the exact frequency each time you change mode. A commercial receiver may or may not lock onto it.

---

## Safety

* **Never clip either lead, RED or BLACK, to a line that might be live.** The fuse only protects the transmitter: with one lead on a live wire, the other lead's clip is live too. Live or unsure: clamp or power mode only. Direct connection is for lines you've switched off **and** proved dead with a meter.
* The clamp goes round **insulated** cable or conduit only, never bare conductors.
* The transmitter puts out up to ±14 V. That's not dangerous to touch, but the far end of whatever it's connected to might be.
* A blown 1 A output fuse means the transmitter was connected to something live. Find out what before you replace it.
* Locators give an approximate position. **Hand dig** within 18 in either side of any mark (New Mexico's tolerance zone) until you see the line.
* LiFePO4 is the safe lithium chemistry, but charge it with its own charger, and not inside the closed box.

---

## License

MIT. See [LICENSE](LICENSE).

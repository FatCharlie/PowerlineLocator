# Parts and buy order

Prices are rough, in US dollars, and drift. Where a part has a manufacturer number, buy that exact part; where it doesn't, the **search phrase** finds equivalents on Amazon, eBay, AliExpress or Mouser. Status: **Needed** = still to buy, **Have** = in hand.

**Rough total:** receiver about $340, transmitter and clamp about $180, so about **$520**. The two big items are the UMC404HD interface (~$100) and the 12 V battery (~$40). Ways to spend less are at the [end](#spending-less).

Order in this order so nothing waits on shipping: the slow, specific parts first (display, split cores, Pico, DRV8871), then everything generic.

---

## A. Receiver: electronics

| # | Item | Qty | Search phrase or link | ~$ | Notes | Status |
|---|---|---|---|---|---|---|
| A1 | Raspberry Pi 4 Model B, 2 GB or more | 1 | [raspberrypi.com: Pi 4](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/) | 45 | A dedicated one: it lives in the tool. A Pi 5 also works. | Needed |
| A2 | microSD card, 32 GB, A1 or A2 rated | 1 | "SanDisk 32GB microSD A1" | 8 | | Needed |
| A3 | Behringer **UMC404HD** USB audio interface | 1 | "Behringer UMC404HD" ([Thomann](https://www.thomannmusic.com/behringer_umc404hd.htm), Sweetwater, Amazon) | 100 | Four mic preamps and a 24-bit, 192 kHz converter in one box. Must be the **404** (four inputs); the 204HD and 202HD only have two. Works on Linux with no driver. | Needed |
| A4 | Adafruit SHARP Memory Display, 2.7" 400×240 (**product 4694**) | 1 | [adafruit.com/product/4694](https://www.adafruit.com/product/4694) (also Digi-Key, Mouser, PiShop) | 45 | Reflective: readable in full sun, unlike backlit screens. Often out of stock: order early. | Needed |
| A5 | USB-C power bank, 20,000 mAh, with a **5 V 3 A** USB-C output | 1 | "power bank 20000mAh USB-C PD 5V 3A" | 30 | About 8 to 10 hours of locating. | Needed |
| A6 | Short USB-C to USB-C (or USB-A to USB-C) cable, 1 ft | 1 | "short USB C cable 1ft" | 6 | Power bank to Pi. | Needed |
| A7 | Momentary push buttons, 16 mm panel mount, normally open, one red and one blue | 2 (+2 for the transmitter) | "16mm momentary push button waterproof red blue" | 10 | Buy a mixed pack: the transmitter needs two more. | Needed |
| A8 | **Passive** piezo buzzer, 12 mm, through-hole | 1 | "passive buzzer 12mm 3.3V" | 5 | **Passive**, not "active": an active one only makes one fixed note. | Needed |
| A9 | Resistor 100 Ω, ¼ W | 1 | in any resistor kit | | Buzzer. | Needed |
| A10 | Dupont jumper wires, F-F, 20 cm | 10 | "Dupont jumper wire kit" | | Pi to display and panel parts. | Have? |
| A11 | Nylon standoffs, M2.5, kit | 1 | "M2.5 nylon standoff kit" | 8 | Pi and display in the head box. | Needed |
| A12 | Project box, ABS, about 6 × 4 × 2.5 in (150 × 100 × 70 mm) | 1 | "ABS project box 150x100x70mm" | 12 | The head box. Cut a 60 × 36 mm window for the screen. | Needed |
| A13 | Clear acrylic sheet, small, 2 to 3 mm | 1 | "clear acrylic sheet 3mm 4x6" | 6 | Window over the screen. | Needed |

## B. Receiver: coils and staff

| # | Item | Qty | Search phrase or link | ~$ | Notes | Status |
|---|---|---|---|---|---|---|
| B1 | Ferrite rods, **10 mm × 100 mm**, black/grey (MnZn, "AM radio antenna rod") | 5 | "ferrite rod 10mm x 100mm" | 12 | Four coils and one spare. All from the **same pack** so they match. Not yellow/white "iron powder" rods. | Needed |
| B2 | Magnet wire, **30 AWG**, enamelled copper, ½ lb | 1 | "30 AWG magnet wire 1/2 lb" (e.g. Remington Industries 30SNSP.5) | 25 | ½ lb is about 500 m; each coil takes about 40 m. | Needed |
| B3 | Copper foil tape, ½ in or 1 in, **conductive adhesive** | 1 roll | "copper foil tape conductive adhesive 1/2 inch" | 10 | The coil shields. | Needed |
| B4 | XLR microphone cables, 3 ft (1 m) | 4 (a 4-pack) | "XLR microphone cable 3ft 4 pack" | 20 | Cut the **female** ends off; the male ends plug into the interface. | Needed |
| B5 | Electrical tape (black vinyl) and masking tape | 1 each | | 6 | | Have? |
| B6 | Printer paper | a sheet | | | Coil formers. | Have |
| B7 | Heat-shrink tubing kit | 1 | "heat shrink tubing kit" | 8 | | Have? |
| B8 | 1 × 4 board, 4 ft (actual 3/4 × 3-1/2 in), pine or poplar, straight and knot-free | 1 | lumber yard: "1x4x4 select pine" | 8 | The staff. A 6 or 8 ft board cut to 4 ft is fine. | Needed |
| B9 | Exterior paint or spar varnish | small can | | 8 | Keeps the board straight in wet weather. | Have? |
| B10 | Nylon zip ties, UV-resistant black, 8 in | 100 | "UV resistant zip ties 8 inch black" | 7 | Nothing metal below 750 mm on the staff. | Needed |
| B11 | Hook-and-loop straps, 1 in × 12 in | 2 | "velcro straps 12 inch" | 6 | Hold the interface on. | Needed |
| B12 | A handle (any drawer/door pull) | 1 | | 5 | Screws are fine up here. | Have? |
| B13 | Hand-crank ("egg-beater") hand drill | 1 | "hand crank drill egg beater" | 18 | For winding. A cordless drill on its slowest setting works too. | Needed |
| B14 | Hand tally counter (clicker) | 1 | "hand tally counter" | 5 | Counting crank turns. | Needed |

## C. Transmitter

| # | Item | Qty | Search phrase or link | ~$ | Notes | Status |
|---|---|---|---|---|---|---|
| C1 | Raspberry Pi **Pico** (Pico H if you'd rather not solder its header) | 1 | [raspberrypi.com: Pico](https://www.raspberrypi.com/products/raspberry-pi-pico/) | 5 | Pico 2 also works. | Needed |
| C2 | Adafruit **DRV8871** motor driver breakout (**product 3190**) | 1 | [adafruit.com/product/3190](https://www.adafruit.com/product/3190) | 8 | The H-bridge: 6.5 to 45 V, 3.6 A peak, PWM up to 200 kHz. | Needed |
| C3 | Pololu **D24V10F5** 5 V 1 A step-down regulator | 1 | "Pololu D24V10F5" | 10 | Battery to 5 V for the Pico. Any 5 V buck module with a 15 V+ input works. | Needed |
| C4 | 12.8 V **LiFePO4** battery, 6 Ah, with its charger | 1 | "12V 6Ah LiFePO4 battery with charger" | 40 | LiFePO4: safe chemistry, built-in protection board. | Needed |
| C4a | Insulated female spade crimp connectors, 0.250 in (6.3 mm), for 16 to 14 AWG, and a crimper | 2 + spares | "0.250 female spade connector insulated" | 8 | Battery terminals (most small LiFePO4s have F2 = 0.250 in tabs; check yours). | Needed |
| C5 | In-line blade (ATO) fuse holder, 16 AWG, and **3 A** blade fuses | 1 + spares | "inline ATO fuse holder 16 AWG" | 6 | F1, right at the battery. | Needed |
| C6 | Toggle switch, SPST, 12 V 10 A, panel mount | 1 | "SPST toggle switch 12V 10A" | 5 | SW1. | Needed |
| C7 | Electrolytic capacitor, **470 µF 35 V** | 1 | in a cap kit, or "470uF 35V capacitor" | 1 | C1, next to the DRV8871. | Needed |
| C8 | Power resistor, **22 Ω 25 W**, aluminium housed | 1 | "22 ohm 25W aluminum resistor" | 4 | R1. Screw it to the box wall or a scrap of aluminium: it gets warm into a short. | Needed |
| C9 | Panel-mount fuse holder, 5 × 20 mm, and **1 A fast-blow** 5 × 20 mm fuses | 1 + 10 spares | "panel mount fuse holder 5x20mm" and "F1A 250V fuse 5x20" | 8 | F2, on the output. | Needed |
| C10 | TVS diode **1.5KE20CA** (bidirectional, through-hole) | 1 (pack) | "1.5KE20CA" | 4 | D1. The **CA** suffix means bidirectional: required. | Needed |
| C11 | Binding posts, red and black, 4 mm banana compatible | 1 pair | "binding post red black 4mm banana" | 6 | The output terminals. | Needed |
| C12 | 5 mm LEDs green, yellow, red, and 330 Ω resistors | 3 + 3 | LED and resistor kits | | | Have? |
| C12a | Schottky diode **1N5819** | 1 | "1N5819" | 1 | D2, between the 5 V regulator and the Pico's VSYS. | Needed |
| C13 | Momentary buttons | 2 | see A7 | | FREQ and LEVEL. | (A7) |
| C14 | Perma-proto / solderable breadboard, half size | 1 | "Adafruit Perma-Proto half size" or "solderable breadboard" | 5 | The Pico, DRV8871 and buck converter live here. | Needed |
| C15 | Hook-up wire: 18 AWG stranded red and black; 22 AWG solid assorted | | "18 AWG stranded wire red black" | 10 | 18 AWG for the battery and output paths. | Have? |
| C16 | Enclosure, ABS, about 10 × 6 × 4 in (250 × 150 × 100 mm), big enough for the battery | 1 | "ABS junction box 250x150x100mm" | 20 | Battery and electronics in one box: nothing to forget when lending. | Needed |
| C17 | Banana-to-alligator test leads, 1 m, red and black | 1 set | "banana plug to alligator clip test leads" | 8 | The RED lead and a short BLACK lead. | Needed |
| C18 | Wire for the long ground lead: 50 ft of 16 AWG stranded, plus one banana plug and one big alligator clip | 1 | "16 AWG stranded wire 50 ft" | 12 | Reaches a stake well off to the side. | Needed |
| C19 | Ground stakes: 18 in steel tent stakes or short rebar | 2 | "18 inch steel tent stake" | 8 | Two are needed for calibration. | Needed |

## D. Clamp

| # | Item | Qty | Search phrase or link | ~$ | Notes | Status |
|---|---|---|---|---|---|---|
| D1 | Fair-Rite **0431177081** snap-on split ferrite core (31 material, 25.65 mm hole) | 2 | "Fair-Rite 0431177081" (Mouser, Digi-Key) | 20 | 31 material is the one that works well down at 8 to 33 kHz. Cheap unbranded clip-on ferrites are usually made for MHz and won't. | Needed |
| D2 | 20 AWG stranded hook-up wire, 2 m, and 2 banana plugs | | | 5 | 10-turn winding and leads. | Needed |

## E. Calibration and testing

| # | Item | Qty | Search phrase or link | ~$ | Notes | Status |
|---|---|---|---|---|---|---|
| E1 | 100 ft spool of 18 AWG stranded wire (single conductor) | 1 | "18 AWG stranded wire 100 ft" | 15 | The calibration wire: needs at least 65 ft (20 m) laid straight. Also the test-range wire. | Needed |
| E2 | Tape measure and 4 marking flags (or tent pegs) | | | 5 | Calibration positions. | Have? |

## F. Tools

You likely have most of these.

* Multimeter with continuity, resistance and DC volts
* Soldering iron, solder, flux; helping hands
* Wire strippers, flush cutters, craft knife
* Drill with bits and a **step bit** (for 16 mm button holes and the binding posts)
* Hot-glue gun
* Optional, nice to have: a handheld **LCR meter** (~$30) to check the four coils match before you mount them

---

## Spending less

* **Reuse a Pi** you already have (A1, A2): saves $55. The Pi can still run other things when not in the locator.
* **Skip the screen** (A4, A12's window, A13): the software falls back to printing on a terminal, and the buzzer still guides you. Saves about $50, but makes it much worse as a loaner.
* **Use any 12 V battery** you have (C4): a small lead-acid or a tool-battery adapter both work. The DRV8871 takes anything from 6.5 to 45 V. Saves $40.
* **Skip the clamp** (D1, D2): direct connection and power mode still work. Saves $25, but the clamp is the only safe way to put a signal on a live line.

What not to skimp on: the UMC404HD (four matched preamps on one clock is what makes the depth maths work), and the transmitter's protection parts (C5, C8, C9, C10), which are what make it safe to lend.

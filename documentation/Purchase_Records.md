<!--
SPDX-License-Identifier: CC-BY-4.0
Copyright (c) 2026 Dan MacLean
-->
<!-- markdownlint-disable MD060 -->

# Purchase Records — Automator

What was actually bought for the Automator through TSL purchasing, extracted from the NBI purchase-requisition system on 18 November 2026. This complements [`Bill_of_Materials.md`](Bill_of_Materials.md), which describes the as-designed parts list; this file records the as-purchased one. The two differ, and the differences matter for the 2026 rebuild (see [`document_brief.md`](document_brief.md)).

## How this was compiled

- Source: the "Requests by my Colleagues" view of the NBI purchase-requisition system (intranet, `infoserv/cgi-bin/orders/MyRequests.asp?ccl=1`), as visible to the cost-centre authoriser. The view reports 42 records with no pagination, covering 2021 to 2026.
- Every request raised by the original builder (login `wot25kir`, Rohan R) was downloaded and its item lines parsed. The system's own item-description search was also run for *pump, vacuum, suction, servo, MG99, relay, mosfet, switch, RC* to catch anything on requests outside that view. It found nothing further.
- Requests raised by other members of the group in the same period were checked and contain no Automator parts.
- Prices are unit prices ex VAT as entered on the request. Amazon catalogue numbers are ASINs; the product page is `https://www.amazon.co.uk/dp/<ASIN>`.

## Requests raised by wot25kir

| Request | Date | Supplier | Total (ex VAT) | Rows in the colleague view |
|---|---|---|---|---|
| 363146 | 04 Aug 2025 | Amazon | £249.75 | 4 |
| 364066 | 27 Aug 2025 | Amazon | £29.79 | 1 |
| 364613 | 09 Sep 2025 | Amazon | £140.32 | 4 |
| 364617 | 09 Sep 2025 | Amazon | £43.08 | 2 |
| 365096 | 23 Sep 2025 | Amazon | £70.70 | 1 |
| 367087 | 12 Nov 2025 | Amazon | £181.27 | 1 |
| 368393 | 12 Dec 2025 | Amazon | £166.82 | 3 |
| 370323 | 19 Jan 2026 | Surface Scan (3D printing) | £43.10 | 1 |
| 375276 | 18 May 2026 | Amazon | £58.57 | 2 |
| 376629 | 22 Jun 2026 | Amazon | £40.65 | 1 |

Ten requests, 90 order lines. A request appears once per delivery in the colleague view, which is why 14 rows reduce to 10 request IDs.

## Components queried during the 2026 rebuild

| Component | Found in orders? | Detail |
|---|---|---|
| Solenoid valve | Yes | Request 368393, 12 Dec 2025, ASIN B07VLW5FTD: sourcing map Miniature Solenoid Valve, 2-way normally closed, DC 5 V, 0.26 A, £7.99 |
| Relay module | Yes | Request 363146, 4 Aug 2025, ASIN B07DJ4NRC1: DollaTek 5 V 1-channel relay module with optocoupler, high/low trigger, £3.19 (documented as the LED relay on Pi GPIO 23) |
| Vacuum pump | No | Not in any request; description searches for pump, vacuum, suction return nothing |
| Servo | No | Not in any request; searches for servo and MG99 return nothing |
| RC / solid-state switch modules | No | Not in any request; searches for RC, mosfet, switch find only the E-stop and push button |

## Bill of Materials items with no matching purchase request

- MKS Robin Nano V3.1 (BOM item 2)
- DC-DC buck-boost converter (item 45)
- 1000 µF 10 V capacitor (item 46)
- 15 A ideal diode (item 47)
- Second IP65 project box (item 48; only one was ordered)
- Dedicated 5 V PSU for the Pi (only the PSU bundled in the Pi starter kit was ordered)

Together with the pump, servo and switch modules, this means the whole MKS / power-conditioning / pneumatic-actuator sub-assembly was sourced outside the purchasing system.

## Ordered but not in the Bill of Materials

- Waveshare HRB8825 stepper motor HAT for Raspberry Pi (363146, £17.59) — superseded prototype motion controller
- Stepper control expansion board for A4988/DRV8825 (365096, £2.92)
- Waveshare TCS34725 colour sensor (364066, £6.60)
- Coral USB Edge TPU (367087, £63.44)
- Raspberry Pi Camera Module 3 NoIR Wide (368393, £30.39)
- Zomei 52 mm IR 950 filter (368393, £20.20)
- Neewer NS007 ring light diffuser (367087, £5.99)
- Preciva crimping tool set with JST connectors (368393, £21.59)
- Two drag-chain kits (368393)
- Gantry frame: 2020/2040 extrusions, brackets, V-wheels, gantry plate, fasteners (364613, 364617, 365096, 367087)

## All order lines by request


### Request 363146 — 04 Aug 2025 — AMAZON — PO TSL0124704A TSL0124705A

| Qty | Pack | Cat. no. | Unit £ ex VAT | Description |
|---|---|---|---|---|
| 1 | 1 | B08YCYW623 | £10.39 | USB C to Ethernet Adapter, WALNEW Gigabit Cat Cable Converter to Type-C, USBC Thunderbolt 3 Lan Network Adaptor for Mac,MacBook,iPad Pro/Air,Dell XPS,Surface,Chromebook Laptop,Galaxy S23 S22 Tab S8 S7 |
| 1 | 1 | B0DSFT7567 | £95.99 | Starter Kit For Raspberry Pi 4B Model B 8GB RAM DIY/ With Case / Pi Cooling Fan / San disk 64G SD Card Micro-SD / Micro HDMI Cable / Sufficient 5V 3A Power Supply (8G Module 8 In 1 Kit) |
| 1 | 1 | B09H2ZB17H | £11.12 | 12V 5A Power Adapter Supply - LeTaoXing AC 100-240V 50/60Hz to DC 60W 12 Volt 5amp LED Driver Transformers Universal Switching 12V/5A UK Cord for LED Strip Light CCTV Cameras LCD Monitors |
| 1 | 1 | B00IJZOT5A | £2.32 | sb Components Raspberry Pi Camera Case Transparent Protective Case Cover For Raspberry Pi Camera / Compatible With Camera Module 1, 2 and 3 (Black) |
| 1 | 1 | B07DK52YK5 | £3.99 | DollaTek 2PCS (9 x 15cm) PCB Board Universal Double Sided Prototyping Breadboard Panel Circuit Board for DIY Soldering |
| 1 | 1 | B07DJ4NRC1 | £3.19 | DollaTek 5V 1-Channel Relay Module Board Shield with optocoupler Support High and Low Level Trigger |
| 1 | 1 | B09H2VYPFN | £11.64 | Breadboard Jumper Wires 20AWG, Female to Male Jumper Cables Wires 15CM M/F Bestlus Exclusives 10 Colors Pack of 120 Square Head 0.1'' (6'', M/F) |
| 1 | 1 | B075PH4MWG | £4.79 | AZDelivery Flex Ribbon Cable 50cm (20 inches) FFC Ribbon Extension Cable compatible with Raspberry Pi Camera Module/Display Including E-Book! (Pack of 3) |
| 1 | 1 | B0CSN6PPVZ | £7.19 | Treedix RPi GPIO Terminal Block Breakout Board Module Expansion Board Compatible with Raspberry Pi 4B/3B+/3B/2B/Zero/Zero W |
| 1 | 1 | B0BRY757NX | £36.79 | Raspberry Pi Camera Module 3 Wide ---SCO874 |
| 1 | 1 | B0D9XH7XQ6 | £6.39 | Aclorol USB COB LED Strip Light 1M Dimmable LED TV Backlight High Density Cold White Flexible Rope Light with 1.5M USB Powered for Under Cabinet Wardrobe Bed Lighting 320LEDs/M CRI85+ 6000K [Energy Class D] |
| 1 | 1 | B0F2YCLT3V | £5.59 | FunnAura 3 Pcs Glasses Cleaner Anti Fog Spray for Swimming Goggles Glass and Anti Fog Car |
| 1 | 1 | B096PBMDKX | £3.19 | 700 Assorted 5mm Sticky Coloured Dots Easy Peel Self Adhesive Colour Coding Sticky Dots Round Labels Circle Stickers |
| 1 | 1 | B0DQW2B7TF | £9.59 | 30 Packets 10 Gram Silica Gel Desiccant Absorber Dehumidifiers |
| 1 | 1 | B097JJZF46 | £19.99 | 3pcs iMetrx Nema 17 Stepper Motor 42x38mm 17HS4401 1.5A-3.8V 2 phase 4 wires 1.8 degrees with 1Meter cable for 3D Printer Motors--NEMA 4238 |
| 1 | 1 | B0B4MV9BCN | £17.59 | Waveshare HRB8825 Stepper Motor HAT Compatible with Raspberry Pi Drives Two Stepper Motors Up To 1/32 Microstepping For 3D Printer Sculpturing Machine and Mechanical Arm |

### Request 364066 — 27 Aug 2025 — AMAZON — PO TSL0124779A

| Qty | Pack | Cat. no. | Unit £ ex VAT | Description |
|---|---|---|---|---|
| 1 | 1 | B07PKP3KMX | £6.60 | Waveshare TCS34725 Color Sensor Onboard TCS34725FN Embedded ADC High Sensitivity I2C Interface 4-ch RGBC 16-bit Per CH Integrates IR Blocking Filter 3.3V/5V |
| 1 | 1 | B09F8WLMFR | £7.19 | DC 5V 8010 Fan Dual Ball Bearings 80mm 10mm Fan 3D Printer 80x80x10 Brushless Cooling Fan for Makerbot for 3D Printer PC CPU Computer Case Fan Cooler and Other Small Heat Dissipation Equipment |
| 1 | 1 | B0C9HZXFMZ | £16.00 | nnoMaker Aluminum Alloy Case for Raspberry Pi 4 - Compatible with DAC/DAC PRO/AMP/AMP PRO/RS485&CAN HAT, 3510 PWM Fan & Passive Heatsink Cooling for Expanded Boards |

### Request 364613 — 09 Sep 2025 — AMAZON — PO TSL0124833A TSL0124838A

| Qty | Pack | Cat. no. | Unit £ ex VAT | Description |
|---|---|---|---|---|
| 2 | 2 | B07R55DGGC | £15.23 | Iverntech 2pcs 350mm 2040 V Type European Standard Anodized Black Aluminum Profile Extrusion Linear Rail for 3D Printer and CNC DIY Laser Engraving Machine |
| 1 | 20 | B0DGQ9RHYN | £2.39 | SHUNCHG 20 Pcs Black M5 x 12mm Self Tapping Wood Screws Carbon Steel Mushroom Round Flanged Head Fasteners Drilling Screw |
| 1 | 20 | B0CQXRBZ1Y | £3.99 | sourcing map 20pcs Aluminum Spacer 5mm Bore 10mm OD, 6mm Length Screw Standoff Bushing Plain Finish Round Spacer for M5 Screws Bolts and Rods |
| 1 | 25 | B0BJZM3B5R | £3.91 | 25Pcs M5 Nuts Nylock, Leryati Lock Nuts M5 Stainless Steel Hex A2 V2A Self Locking Nut, DIN985 Nylon Insert Kits Thread Nut Nyloc Hexagon nutstones |
| 1 | 20 | B0FC6NH359 | £4.15 | Valorada 20Pcs M5 Bolts, M5 x 15mm Flat Head Hex Socket Screws, 304 Stainless Steel Furniture Bolts, Full Thread Machine Screws with Hex Key |
| 1 | 20 | B0C4MSSWT8 | £3.67 | AMLOOPH M3 Bolts, M3 x 10mm Hex Socket Button Head Machine Bolts/Screws -3mm Fully Threaded A2 304 Stainless Steel Hex Socket Screws (Pack Of 20) |
| 1 | 20 | B0FC6M83PT | £3.91 | Valorada 20Pcs M5 Bolts, M5 x 10mm Flat Head Hex Socket Screws, 304 Stainless Steel Furniture Bolts, Full Thread Machine Screws |
| 1 | 20 | B0FC6KC3SM | £5.27 | Valorada 20Pcs M5 Bolts, M5 x 40mm Flat Head Hex Socket Screws, 304 Stainless Steel Furniture Bolts, Full Thread Machine Screws |
| 1 | 10 | B0DCJD69QK | £3.27 | sourcing map 10 pcs M5-0.8x30 Machine Screws Phillips Pan Cross Head Screws Fasteners Bolts 304 Stainless Steel Silver |
| 1 | 25 | B0D6NGDXQN | £3.03 | Nyloc Nuts, A2 Stainless Steel Hex Nylon Insert Lock Nuts (M5 x 25 Pack) |
| 1 | 1 | B0C7KTN42J | £5.19 | SHCEEC GT2 Timing Pulleys 16 Teeth 5mm Bore 6mm Width for 3D Printer 2mm Pitch Aluminum Timing Belt Pulley Wheel with Allen Wrench |
| 1 | 1 | B0DT7CC6PZ | £3.96 | 5 meter 4 Pin RGB Strip Light Extension Cable Wire |
| 1 | 1 | B0FGJCGYWN | £3.91 | sourcing map 2 Set 4 Pin 5mm 0.2 Inch Pitch PCB Mount Screw Terminal Block Connectors Male Female, Green |
| 1 | 2 | B0DXPWR3NF | £10.39 | sourcing map 2 Pcs t Slot 2020 Aluminum Extrusion Profile 350mm 14 inch, European Standard Anodized Black Linear Rail Extrusion Frame |
| 1 | 1 | B0DRVJW6RZ | £12.79 | iMetrx 2040 Aluminum Profile Pulley V Slot Gantry Plate |
| 1 | 20 | B0FP4F8V1M | £7.92 | 20PCS/Lot M5 T-Nut Nickel Plated Double T-nut for 2020 T-Slot Aluminum Profile Linear Rails |
| 1 | 20 | B08DMX6QJJ | £3.99 | Thick Shim Washers Plain Steel DIN 988 (Pack of 20) (1mm Thickness, 5mm x 10mm) C01-C04BC |
| 1 | 13 | B0D5LLG99N | £11.99 | Lsgoodcare 13Pcs 3D Printer Rollers wheels POM Big Pulley with 13Pcs Eccentric Column and 20Pcs Aluminium Spacer Isolation Column |
| 1 | 1 | B083DQLDC4 | £10.54 | NEMA 17 Motor Mount Plate for NEMA 17 Stepper Motors |
| 1 | 1 | B07M7VLSYW | £5.59 | CSI or DSI Cable Extender Thingy for Raspberry Pi to Extend Cable Length |

### Request 364617 — 09 Sep 2025 — AMAZON — PO TSL0124839A

| Qty | Pack | Cat. no. | Unit £ ex VAT | Description |
|---|---|---|---|---|
| 1 | 3 | B075JPGYCF | £5.99 | AZDelivery 3 x Flex Ribbon Cable 200 cm (80 inches) compatible with Raspberry Pi Camera |
| 2 | 1 | B0F4825VZT | £3.99 | Open Synchronous Belt,2mm Pitch 6mm Width Rubber Fiberglass GT2 Open Timing Belt,3D Printer Accessories - 6mm x 5M |
| 1 | 1 pck | B0839VSHSD | £0.79 | Pro Power 150X2.5 mmNAT Cable Ties, Natural, 150 x 2.5 mm |
| 1 | 24 | B0D5SW6C7T | £3.99 | sourcing map 24Pcs M5 T Nut Tee Sliding Slot Nuts (M5-0.8x11x10.2x5mm) |
| 1 | 1 pck | B0B2QVDGHZ | £11.99 | EYPINS 10-Pack 2020 Series Black Aluminum Corner Brackets - 90-Degree L-Shape Extrusion Connectors with M5x10 Hex Bolts & T-Nuts for 2020 Profiles (6mm Slots) |
| 1 | 1 | B0DZNYQGKX | £3.19 | IR Infrared Obstacle Avoidance Sensor Module |
| 1 | 1 | B0C7KTN42J | £5.19 | SHCEEC GT2 Timing Pulleys 16 Teeth 5mm Bore 6mm Width for 3D Printer 2mm Pitch Aluminum Timing Belt Pulley Wheel with Allen Wrench |
| 1 | 1 | B0DT7CC6PZ | £3.96 | 5 meter 4 Pin RGB Strip Light Extension Cable Wire |

### Request 365096 — 23 Sep 2025 — AMAZON — PO TSL0124893A

| Qty | Pack | Cat. no. | Unit £ ex VAT | Description |
|---|---|---|---|---|
| 2 | 2 | B086GZDJJV | £16.79 | (Replacement) Iverntech 2pcs 400mm 2040 V Type European Standard Anodized Black Aluminum Profile Extrusion (please note 400mm length) |
| 1 | 1 | B0D7YTM651 | £2.92 | Stepper Motor Control Expansion Board, Stepper Motor Control Expansion Board - for A4988 DRV8825 |
| 1 | 1 | B0F5RDXPJM | £3.00 | StepStick Stepper Motor Driver Module DRV8825 |
| 1 | 1 | B0DV4JZPCQ | £26.25 | 200mm Stroke T6x1 Screw NEMA11 Stepper |
| 1 | 2 | B0DCJQTD8R | £4.95 | Silicone Mat for Worktops |

### Request 367087 — 12 Nov 2025 — AMAZON — PO TSL0125051A

| Qty | Pack | Cat. no. | Unit £ ex VAT | Description |
|---|---|---|---|---|
| 1 | 1 | B0BL77FXPV | £25.99 | USB Camera Module |
| 1 | 10 | B0CNST5KDR | £23.19 | 10 Piece 350 mm 2020 V Type Black European Standard Anodized Linear Rail Aluminum Profile Extrusion |
| 1 | 1 | B0D7CFYYVJ | £12.79 | 12 pcs Black 3 Way End Corner Angle Connector |
| 1 | 1 | B0D3QKYYKK | £10.71 | 2020A Aluminum Extrusion Profile Corner Bracket (black) |
| 1 | 10 | B0C5J5764S | £13.59 | L-Shaped Corner Bracket Connection |
| 1 | 26 | B0CQXKLTJC | £10.39 | 2020 Extrusion Connector Bracket Joint |
| 1 | 1 | B0B92LPPCP | £11.99 | Neewer 52mm Polarizing Filter 30 Layer Multi Resistant Nano Coatings Circular Polarising Filter(CPL) |
| 1 | 1 | B07R53D12W | £63.44 | USB Edge TPU for Raspberry Pi and Other Embedded Single Board Computers |
| 1 | 1 | B0CT31283X | £5.99 | NEEWER NS007 Ring Light Diffuser Only |
| 1 | 1 | B0F9WNXSFW | £3.19 | 16cm/6inch Mini LED Ring Light Fill-in Lamp USB Powered |

### Request 368393 — 12 Dec 2025 — AMAZON — PO TSL0125188A

| Qty | Pack | Cat. no. | Unit £ ex VAT | Description |
|---|---|---|---|---|
| 1 | 1 | B0FF4NVX38 | £16.79 | 220V Single Phase On/Off Switch: 16A Emergency Stop Push Button Switch, |
| 1 | 1 | B0BRY6VLR6 | £30.39 | Raspberry Pi Camera Module 3 NoIR Wide |
| 1 | 1 | B0C3GQPXMR | £28.79 | CNC Metal Tripod Mount Ring for Lens |
| 2 | 1 | B07TGBD2GT | £7.19 | R18 Internal Size 7X7mm 1Meter Length Black Plastic Flexible Drag Chain Cable Wire |
| 1 | 1 | B0FRFB7KQG | £12.79 | Drag Chain Kit for BambuLab P1P: 16.9in Openning Type Wire Carrier Flexible Nested Drag Chain Cable Track Black |
| 1 | 1 | B07R4XGG6Z | £20.20 | Zomei 52MM IR 950 GLASS Infrared Filter |
| 1 | 1 | B0CH37171Q | £21.59 | Preciva Crimping Tool Set with JST connectors |
| 1 | 1 | B07VLW5FTD | £7.99 | sourcing map Miniature Solenoid Valve 2 Way Normally Closed DC5V 0.26A Air Solenoid Valve |
| 1 | 12 | B0D3QKYYKK | £10.71 | sourcing map 2020A Aluminum Extrusion Profile Corner Bracket Black |
| 1 | 1 | B085FRWH6Y | £3.19 | Dot Stickers Coloured,16mm Coding Sticky Dots |

### Request 370323 — 19 Jan 2026 — Surface Scan Unit 4 Little Cliffsend Far — PO none

| Qty | Pack | Cat. no. | Unit £ ex VAT | Description |
|---|---|---|---|---|
| 1 | 1 | N/A | £2.47 | LED_and_cam_case.stl, 52.1mm x 52.1mm x 15.0mm |
| 1 | 1 | N/A | £7.98 | Cover_80mm_Two_Fans.st l, 182.0mm x 134.0mm x 9.7mm |
| 1 | 1 | N/A | £22.46 | Base_PIMKS.stl, 182.0mm x 134.0mm x 35.0mm |
| 1 | 1 | N/A | £4.20 | Base_LED_and_cam_case. stl, 52.0mm x 16.7mm x 61.8mm |
| 1 | 1 | N/A | £5.99 | Delivery Charge |

### Request 375276 — 18 May 2026 — AMAZON — PO TSL0125797A

| Qty | Pack | Cat. no. | Unit £ ex VAT | Description |
|---|---|---|---|---|
| 1 | 1 | B0DBQ4ZSK6 | £7.15 | 10 Pin Rainbow Flat Ribbon Cable, 5M/16.4ft, IDC Wire, PVC & Copper, Compatible with 2.54mm Connectors |
| 1 | 1 | B08R74212Q | £7.47 | ARISKEEN Cat 8 Ethernet Cable 5M, High-Speed 40Gbps 2000MHz Ethernet Cable Braided Flat Gigabit Rj45 STP Shielded Internet Network Lan Cable Cord for Modem Router PC |
| 2 | 1 | B095PB91KL | £8.79 | Iverntech 6pcs 2M XH2.54 4 pin to 6 pin Terminal Stepper Motor Cables for 3D Printer Nema 17 Stepper Motor |
| 1 | 1 | B07FW5ZTVH | £16.79 | Alex Tech 25ft - 3/4 inch Cord Protector Wire Loom Tubing Cable Sleeve Split Sleeving For USB Cable Power Cord Audio Video Cable – Protect Cat From Chewing Cords - Black |
| 1 | 1 | B0FNM9TDZ5 | £3.99 | RAVIAD USB 3.0 Extension Cable 2M, USBA Male to A Female Cable USB Extension Lead |
| 1 | 1 | B07M7VLSYW | £5.59 | Adafruit CSI or DSI Cable Extender Thingy for Raspberry Pi to Extend Cable Length |

### Request 376629 — 22 Jun 2026 — AMAZON — PO TSL0125971A

| Qty | Pack | Cat. no. | Unit £ ex VAT | Description |
|---|---|---|---|---|
| 1 | 2 | B0CNYXPQW8 | £3.99 | GRIFEMA Heavy Duty Double Sided Tape - 3m x 2 Rolls |
| 1 | 1 | B0GRTRVHD9 | £6.39 | Electrical Tape, 18mm x 10m Insulation Tape Electrical |
| 1 | 1 | B07L32B9C2 | £5.99 | Anker 4-Port USB 3.0 Hub with 2 ft Extended Cable [USB-A] |
| 1 | 1 | B00I1IFE40 | £7.99 | PRO ELEC PELB1755 6 Gang Extension Lead with Surge Protection |
| 1 | 1 | B08H4KWJ14 | £4.15 | Electronic Buzzer Alarm, 3-24V Active Piezo Buzzer |
| 1 | 1 | B0CFXSG3RL | £4.15 | Waterproof momentary push button switch, 2pin ON/OFF small round pushbutton switch with wires |
| 1 | 1 | B0BWLW941S | £7.99 | Black Waterproof Plastic Project Box ABS IP65 Electronic Junction box |

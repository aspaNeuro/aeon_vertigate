# Release Notes

> **📝 Template Instructions:** Replace all bracketed placeholders `[like this]` with your project-specific information. Remove sections that don't apply to your project. Delete this instruction block when you're done.

**PCB-1 Version:** [version]  
**PCB-2 Version:** [version]  
**Add/remove version for additional PCBs as needed**  
**Firmware Version:** [version] _(if applicable)_

## 🔧 Key Changes

- [Change 1 - describe key update]
- [Change 2 - describe key update]
- [Change 3 - describe key update]
- [Add/remove changes as needed]

## 🛠️ Assembly Instructions

### BOM list

| Part Number | Description     | Quantity | Supplier     |
| ----------- | --------------- | -------- | ------------ |
| [Part 1]    | [Description 1] | [Qty 1]  | [Supplier 1] |
| [Part 2]    | [Description 2] | [Qty 2]  | [Supplier 2] |
| [Part 3]    | [Description 3] | [Qty 3]  | [Supplier 3] |

### Get the PCBA and 3D Prints

> [Instructions for users without in-house fabrication capabilities]

- **PCBA**: Order from [JLCPCB](https://jlcpcb.com/) (includes assembly service). Refer to the [Bill of Materials (BOM)](eCAD/Assembly/BOM.xlsx) for manual assembly.
- **3D Prints**: Print the mechanical components using any 3D printing service or in-house printer.

See the [JLCPCB Assembly Tutorial]([https://github.com/SainsburyWellcomeCentre/fablabs-documentation/blob/master/jlcpcb_ordering.md]) for step-by-step instructions.

### PCB Fabrication parameters

| Parameter                  | Value                            |
| -------------------------- | -------------------------------- |
| Layer Count                | [2/4/6/8]                        |
| Dimensions                 | [width x height]                 |
| Delivery Format            | [Single/Panel by JLCPCB]         |
| PCB Thickness              | [0.6~2.0mm]                      |
| Material Type              | FR4 TG135                        |
| Surface Finish             | ENIG                             |
| Gold Thickness             | 2U"                              |
| Outer Copper Weight        | 1oz                              |
| Inner Copper Weight        | [1oz (if applicable)]            |
| Specify Stackup            | [JLC04161H-7628 (if applicable)] |
| Impedance Control          | [±10% (if applicable)]           |
| Via Covering               | [Tented/Epoxy Filled & Capped]   |
| Min via hole size/diameter | [0.15-0.3mm]                     |
| Board Outline Tolerance    | ±0.2mm                           |
| Mark on PCB                | Remove Mark                      |

### Assembly & Installation

1. [First assembly step - be specific about order and technique]
2. [Second assembly step]
3. [Third assembly step]
4. [Installation/connection instructions]
5. [Connection/wiring instructions]
6. [Any drilling, laser cutting, modification, or mounting instructions]

   [If applicable] Use `drill-template].dxf` or refer to the manual dimensions below:

   <p align="center">
       <img src="./img/[assembly-diagram].png" alt="[Assembly Description]" height="500"/>
   </p>

7. [Final assembly steps and testing]

## ⚙️ Configuration & Tuning _(if applicable)_

[If your project requires calibration or fine-tuning, describe the process here]

## 🔧 [Configuration/Calibration] Guidelines

- [Step 1 - describe calibration procedure]
- [Step 2 - describe parameter adjustment]
- [Operating ranges and recommended settings]
  > [Important notes or warnings about configuration]

<div align="center">
  <img src=".img/[configuration-image].png" alt="[Configuration Description]" width="600"/>
</div>

## 💻 Firmware Upload _(if applicable)_

[Instructions for uploading firmware to the device]

1. [Step 1 - preparation]
2. [Step 2 - connection]
3. [Step 3 - upload process]

## 📁 Attachement

```bash
├── PCB-1.zip                    # Electronic CAD files
│   ├── Assembly/
│   │   ├── BOM.xlsx         # Bill of Materials
│   │   └── pick and place.csv
│   ├── Drawing/
│   │   ├── 2d.dxf          # 2D technical drawings
│   │   └── 3d.step         # 3D models
│   ├── Fabrication/
│   │   ├── Gerber/         # PCB fabrication files
│   │   └── NC Drill/       # Drill files
├── PCB-2.zip                    # Electronic CAD files
│   ├── Assembly/
│   │   ├── BOM.xlsx         # Bill of Materials
│   │   └── pick and place.csv
│   ├── Drawing/
│   │   ├── 2d.dxf          # 2D technical drawings
│   │   └── 3d.step         # 3D models
│   ├── Fabrication/
│   │   ├── Gerber/         # PCB fabrication files
│   │   └── NC Drill/       # Drill files
├── 3DP.zip                  # Mechanical CAD files
│   ├── [part1].stl          # 3D printable parts
│   ├── [part2].stl
│   └── [part3].stl
├── Schematic-1.pdf       # Circuit schematic
├── Schematic-2.pdf       # Circuit schematic
├── firmware.[uf2/bin/hex]          # [If applicable] Microcontroller firmware
└── source_code.zip                 # Source design files
```

### `Schematic.pdf`

Contains the complete PCB schematic, drawings, and layer stackup.

### `PCB.zip`

Contains PCB drawings, fabrication outputs, and assembly documentation.

### `3DP.zip`

Contains printable STL models.

### `firmware.[extension]` _(if applicable)_

Contains microcontroller firmware in the appropriate format (.uf2, .bin, .hex, etc.).

### `source_code.zip`

Contains [CAD Software] source files, 3D mechanical designs ([CAD Software]), and firmware source code (C++/MicroPython/Arduino).

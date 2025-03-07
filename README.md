# Diggles/Wiggles 3D Model Converter

> This is a fork of [djunkles/Diggles3db](https://github.com/djunkles/Diggles3db) with significant enhancements to the conversion process, including texture support, material mapping, and Unity integration.

A utility for converting Diggles/Wiggles .3db models to FBX format, making them usable in modern 3D software and game engines.

## Overview

This project allows you to convert original .3db model files from the game "Diggles" (also known as "Wiggles" in some regions) to the widely supported FBX format. The converter preserves:

- All original model geometry
- Animations
- Materials and textures
- Hierarchy structure

## Requirements

- Python 3.6+
- Blender (recommended for proper FBX export)
- Original Diggles/Wiggles game installation
  - Model files (.3db format) located in `/data/3db/` folder of the game
  - Texture files (.tga format) located in `/data/Texture/` folder of the game

## Installation

1. Clone this repository:
```bash
git clone https://github.com/username/Diggles3db.git
cd Diggles3db
```

2. Install the required Python dependencies:
```bash
pip install -r python3/requirements.txt
```

3. Copy the required files from your Diggles/Wiggles game installation:
   - Copy `.3db` files from the game's `/data/3db/` folder to the `assets/models/` folder
   - Copy texture files from the game's `/data/Texture/` folder to the appropriate subfolders in `assets/textures/`
     (Gray, ClassIcons, etc.)

4. Configure the Blender path in `config.json`:
```json
{
    "blender_path": "C:\\Program Files\\Blender Foundation\\Blender 4.3\\blender.exe",
    "settings": {
        "blender_timeout": 600
    }
}
```

## Basic Usage

### Converting a Model

To convert a model with full texture mapping:

```bash
python python3/run_with_mapping.py assets/models/baby.3db
```

This will:
1. Parse the .3db file to extract meshes, materials, and animations
2. Create a material mapping with proper texture assignments
3. Generate an FBX file with correct structure and textures

The output will be stored in the `exports/fbx` directory:
- The FBX model file: `exports/fbx/modelname.fbx`
- A folder with textures: `exports/fbx/modelname.fbm/`

### Analyzing a Model

To analyze a model's structure without converting it:

```bash
python python3/analyze_model.py assets/models/baby.3db
```

### Checking Model Animations

To list and verify animations in a model:

```bash
python python3/check_animations.py assets/models/baby.3db
```

or 

```bash
python python3/run.py assets/models/baby.3db --list-animations
```

## Understanding Model Structure

Diggles/Wiggles models have a specific hierarchy structure that's preserved in the FBX output:

```
ModelName/                  # Root level (e.g. "baby")
  ├── AnimationName1/       # Animation container (e.g. "walk")
  │     ├── frame_000/      # Animation frame
  │     │     ├── link_00   # Mesh part
  │     │     ├── link_01   # Mesh part
  │     │     └── ...
  │     ├── frame_001/
  │     │     ├── link_00
  │     │     └── ...
  │     └── ...
  ├── AnimationName2/
  │     └── ...
  └── ...
```

**Important Notes About the Structure:**
- Unlike conventional animation systems, all frames and meshes are present in the hierarchy at once
- Animations work by toggling visibility of different frame objects
- Each frame contains multiple mesh parts called "links"
- Our Unity tool (see below) helps set up proper animation controllers for this structure

## Advanced Usage

### Command-Line Options

The main converter (`run_with_mapping.py`) supports these options:

- `--mapping-only`: Only create texture mappings without converting
- `--textures-only`: Only extract and prepare textures without converting
- `--no-fix-materials`: Skip the automatic fixing of duplicate materials

### Using with Blender

The converter works best with Blender for optimal FBX export. You can specify your Blender path in `config.json`. If Blender isn't found, the converter will fall back to ASCII FBX export with limited compatibility.

### Using with Unity

This repository includes a Unity Editor tool to help set up animations after importing the converted models. See the [Unity README](Unity/README.md) for instructions.

## Project Structure

- `python3/` - Main converter code
  - `lib/` - Core libraries for parsing and export
  - `blender_modules/` - Modules for Blender integration
- `assets/` - Original models and textures
  - `models/` - .3db model files
  - `textures/` - Texture files (copied from the game)
- `Unity/` - Unity animation setup tool
- `config.json` - Configuration file with Blender path

## Troubleshooting

### Missing Textures in Exported Model

If textures aren't visible after importing the model:

1. Make sure the `.fbm` folder with textures is in the same directory as the FBX
2. Check if your 3D software supports the texture format (TGA)
3. Verify texture paths are relative to the FBX file
4. Ensure you have copied all required textures from the original game

### Distorted Animations

If animations look wrong when imported:

1. Check for duplicate animation names in your model
2. Try exporting with a single animation: `python python3/run.py model.3db --animation 0`
3. Adjust the framerate in your 3D software (default is 6 FPS)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Credits

This project is based on tools originally shared on the [Wiggles forum](https://wiggles.ruka.at/forum/viewtopic.php?f=10&t=105&start=10#p1389) and enhanced with additional features for modern usage.

## License

This software is provided as-is, for non-commercial purposes related to the Diggles/Wiggles game community.
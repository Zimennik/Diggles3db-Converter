# 3DB to FBX/glTF Converter

This Python-based converter transforms .3db model files to FBX and glTF formats.

## Features

- Parse .3db files including meshes, materials, textures, and frame-based animations
- Export to glTF format with geometry and textures
- Export to binary FBX format via Blender with:
  - Proper mesh hierarchy (Root/AnimationName/Frame_XX/Meshes)
  - Animation support using visibility keyframes
  - Material and texture assignment
- Configurable animation parameters
- Detailed error handling and logging

## Requirements

- Python 3.6+
- Blender (optional, for binary FBX export)
- Required Python packages (install with `pip install -r requirements.txt`)

## Usage

Basic usage:

```bash
python run.py path/to/model.3db
```

This will export the model to both glTF and FBX formats in the `exports/` directory.

### Command-line Options

```bash
python run.py [options] [model_path]
```

Options:
- `--fps <value>`: Set animation frames per second (default: 24)
- `--frame-duration <value>`: Set Blender frames per animation frame (default: 5)
- `--list-animations`: List animations in the model without exporting
- `--animation <index>`: Export only the specified animation index (useful for large models)
- `--timeout <value>`: Maximum time in seconds to wait for Blender processing (default: 120)
- `--ascii-only`: Force ASCII FBX export without trying Blender

Examples:

```bash
# Export with custom animation settings
python run.py assets/models/baby.3db --fps 30 --frame-duration 3

# Just list animations without exporting
python run.py assets/models/drache.3db --list-animations

# Set a shorter timeout for Blender processing (1 minute)
python run.py assets/models/baby.3db --timeout 60

# Export only a specific animation (e.g., animation index 0)
python run.py assets/models/baby.3db --animation 0

# Force ASCII FBX export (faster but less compatible)
python run.py assets/models/baby.3db --ascii-only
```

## Configuration

Animation and export settings can be configured in `lib/export_config.py`:

- `ANIMATION_FPS`: Frames per second for animations (default: 24)
- `ANIMATION_FRAME_DURATION`: Blender frames per animation frame (default: 5)
- `MATERIAL_SPECULAR`: Specular intensity (0.0 - 1.0)
- `MATERIAL_ROUGHNESS`: Surface roughness (0.0 - 1.0)
- `EMBED_TEXTURES`: Whether to embed textures in the FBX file

## Export Process

1. The model is first exported to glTF format
2. Textures are copied to the export directory
3. If Blender is available, the glTF file is converted to binary FBX with:
   - Proper hierarchy structure
   - Animation using visibility keyframes
   - Material and texture assignment
4. If Blender is not available or an error occurs, falls back to ASCII FBX export

## Hierarchy Structure

The exported FBX files have the following hierarchy:

```
Root
├── AnimationName1 (e.g., "walk")
│   ├── Frame_00
│   │   ├── Mesh1
│   │   ├── Mesh2
│   │   └── ...
│   ├── Frame_01
│   │   ├── Mesh1
│   │   ├── Mesh2
│   │   └── ...
│   └── ...
├── AnimationName2 (e.g., "run")
│   └── ...
└── ...
```

## Animation System

Animations are implemented using visibility keyframes in Blender's NLA (Non-Linear Animation) system:

- Each frame is a complete set of meshes
- Frames are shown/hidden at the appropriate time using keyframes
- Each animation has its own NLA track and strip

## Troubleshooting

If the export fails, check:

1. Blender installation - the converter will try to find Blender in common locations
2. Texture paths - ensure textures are in the expected locations
3. Error logs - check the `blender_log.txt` file in the export directory

### Handling Long Export Times

For complex models with many animations and frames, the Blender export process can take a long time. The converter now includes:

- Detailed logging of each step in the Blender process
- A timeout option to limit how long to wait for Blender (default: 2 minutes)
- Graceful fallback to ASCII FBX export if the timeout is reached
- Progress indicators showing elapsed time
- Early detection of FBX file creation to avoid unnecessary waiting
- Option to export only a specific animation with `--animation <index>`

If the export is taking too long, you can:
- Increase the timeout with `--timeout <seconds>`
- Use `--ascii-only` to skip the Blender export entirely (faster but less compatible)
- Process a smaller model or fewer animations for testing
- Export only a specific animation with `--animation <index>` (recommended for complex models)

### Debugging Features

The converter now includes enhanced debugging features:

- Comprehensive logging of the Blender process in `blender_log.txt`
- Additional debug information in `blender_debug.log`
- Saving of intermediate Blender files as `debug_import.blend` for inspection
- Detailed error reporting with specific failure points
- Early detection of FBX file creation to identify when the process is working
- Progress reporting with elapsed time

These features help identify exactly where in the process any failures occur, making it easier to diagnose and fix issues.

### Important Note About ASCII FBX

If Blender is not available or if you use the `--ascii-only` option, the converter will use ASCII FBX export. However, **ASCII FBX files are not supported by many applications, including Blender itself**. You will see an error like:

```
ASCII FBX files are not supported 'C:\path\to\your\file.fbx'
```

To ensure full compatibility, please install Blender, which will enable binary FBX export. The converter will automatically detect Blender and use it for the export process.

## Limitations

- The .3db format uses frame-based animation, not skeletal animation
- Each frame is a complete set of meshes, which can result in large file sizes
- Animation playback may not be smooth in all 3D software
- ASCII FBX export (fallback when Blender is not available) has limited compatibility

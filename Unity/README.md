# Diggles Animation Setup Tool for Unity

This Unity Editor tool helps set up proper animations for converted Diggles/Wiggles models. It automatically creates animation clips and configures an Animator Controller for frame-by-frame animations.

## Features

- Automatically detects animation frames in imported FBX models
- Creates separate animation clips for each animation
- Sets up frame-by-frame visibility animation
- Configures a proper Animator Controller
- Allows customizing frame rate and transition durations
- Standardizes frame naming for consistency

## Installation

1. Import the converted Diggles FBX model into your Unity project
2. Copy the `Unity` folder from this repository into your project's `Assets` folder
3. The tool will appear in Unity's menu under `Tools > Setup Animator`

## Usage

### Basic Setup

1. Import your converted Diggles model into Unity
2. Go to `Tools > Setup Animator` in the top menu bar
3. Drag your model GameObject into the "Model" field
4. Click "Setup Animator"

The tool will:
- Create a new Animator Controller for your model
- Generate animation clips for each animation in the model
- Configure frame-by-frame visibility animations
- Add the Animator component to your model

### Configuration Options

- **Frame Rate**: Set the playback speed for animations (default: 12)
- **Transition Duration**: Frames to transition between animations (default: 1)
- **Standardize Frame Names**: Rename frames to consistent format (recommended)

### Animation Structure

The tool expects the following model structure (which is exactly how converted Diggles models are organized):
```
ModelRoot
  ├── AnimationA              # e.g. "walk"
  │     ├── frame_000
  │     │     ├── link_00     # Mesh part
  │     │     ├── link_01     # Mesh part
  │     │     └── ...
  │     ├── frame_001
  │     │     └── ...
  │     └── ...
  ├── AnimationB
  │     ├── frame_000
  │     │     └── ...
  │     └── ...
  └── ...
```

Note: Diggles models don't use conventional animation systems. Each animation is a sequence of static frames, and each frame contains multiple mesh parts. The Unity tool properly handles this unique structure.

### Using the Animations in Scripts

After setting up the animations, you can control them from your scripts:

```csharp
// Get the Animator component
Animator animator = GetComponent<Animator>();

// Play a specific animation by index (0 = first animation, 1 = second, etc.)
animator.SetInteger("AnimationIndex", 1);
```

## Troubleshooting

### Animations Not Playing

- Make sure the model has the expected hierarchy structure
- Check that frame objects follow the naming convention "frame_XXX"
- Verify the Animator component is added to the root GameObject

### Incorrect Frame Order

- Use the "Standardize Frame Names" option to ensure consistent ordering
- Check that frame names are properly formatted as "frame_XXX"

### Missing or Broken Animations

- Re-import the model and run the setup tool again
- Ensure your model has proper animations in the .3db source file
- Check if the converter preserved all animations during FBX export

## Technical Details

The tool works by:
1. Analyzing the hierarchy of the imported model
2. Identifying animation containers and their frames
3. Creating visibility animations for each frame
4. Setting up an Animator Controller with states for each animation
5. Configuring transitions between animations using the "AnimationIndex" parameter

The resulting animation system is optimized for performance and compatibility with Unity's animation system.

## Credits

This animation setup tool is part of the Diggles/Wiggles 3D Model Converter project.
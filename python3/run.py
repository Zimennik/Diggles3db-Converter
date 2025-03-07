import os
import sys
import argparse
from lib.parse_3db import parse_3db_file, Model
from lib.export import export_to_gltf
from lib.export_fbx_binary import export_to_fbx_binary
import lib.export_config as export_config

def main():
    # Set up command-line argument parser
    parser = argparse.ArgumentParser(description='Convert .3db model files to FBX/glTF formats')
    parser.add_argument('model_path', nargs='?', help='Path to the .3db model file')
    parser.add_argument('--list-animations', action='store_true', help='List animations in the model without exporting')
    parser.add_argument('--animation', type=int, help='Export only the specified animation index')
    parser.add_argument('--timeout', type=int, default=export_config.BLENDER_TIMEOUT, help=f'Maximum time in seconds to wait for Blender processing (default: {export_config.BLENDER_TIMEOUT})')
    parser.add_argument('--ascii-only', action='store_true', help='Force ASCII FBX export without trying Blender')
    
    args = parser.parse_args()
    
    # Update configuration if provided
    if args.timeout:
        export_config.BLENDER_TIMEOUT = args.timeout
        print(f"Blender timeout set to {args.timeout} seconds")
    
    # Check if a model path was provided
    if args.model_path:
        model_path = args.model_path
    else:
        # Use default model path - look in different locations
        possible_paths = [
            os.path.join('assets', 'models', 'baby.3db'),
            os.path.join('..', 'assets', 'models', 'baby.3db'),
            os.path.join('..', 'assets', 'baby.3db'),
            os.path.join('..', 'c-sharp', 'baby.3db')
        ]
        
        model_path = None
        for path in possible_paths:
            if os.path.exists(path):
                model_path = path
                break
        
        if model_path is None:
            print("Error: Could not find baby.3db in any of the expected locations.")
            return
    
    # Ensure the model file exists
    if not os.path.exists(model_path):
        print(f"Error: Model file not found at {model_path}")
        return
    
    # Get the model name without extension for use in output paths
    model_name = os.path.splitext(os.path.basename(model_path))[0]
    
    # Define output paths
    gltf_output_path = os.path.join('exports', 'gltf', f'{model_name}.gltf')
    fbx_output_path = os.path.join('exports', 'fbx', f'{model_name}.fbx')
    
    # Create output directories if they don't exist
    os.makedirs(os.path.dirname(gltf_output_path), exist_ok=True)
    os.makedirs(os.path.dirname(fbx_output_path), exist_ok=True)
    
    print(f'Loading model from {model_path}')
    with open(model_path, 'rb') as f:
        file_data = f.read()
        model = parse_3db_file(file_data)
        
        # Print summary of the model
        print(f"\nModel Summary:")
        print(f"  Name: {model.name}")
        print(f"  Materials: {len(model.materials)}")
        print(f"  Meshes: {len(model.meshes)}")
        print(f"  Animations: {len(model.animations)}")
        for i, anim in enumerate(model.animations):
            print(f"    Animation {i}: {anim.name} - {len(anim.meshes)} frames")
        
        # If --list-animations is specified, don't export
        if args.list_animations:
            return
        
        # If a specific animation is requested, create a new model with only that animation
        if args.animation is not None:
            if args.animation < 0 or args.animation >= len(model.animations):
                print(f"Error: Animation index {args.animation} is out of range (0-{len(model.animations)-1})")
                return
            
            print(f"Exporting only animation {args.animation}: {model.animations[args.animation].name}")
            
            # Create a modified model with only the specified animation
            selected_animation = model.animations[args.animation]
            
            # Make a shallow copy of the model and replace the animations list
            # with a list containing only the selected animation
            model.animations = [selected_animation]
            
            # Use the modified model for export
            export_model = model
        else:
            export_model = model
        
        # Export to both formats
        export_to_gltf(export_model, gltf_output_path)
        
        if args.ascii_only:
            print("Forcing ASCII FBX export as requested")
            from lib.export_fbx import export_to_fbx
            export_to_fbx(export_model, fbx_output_path)
        else:
            export_to_fbx_binary(export_model, fbx_output_path)

if __name__ == "__main__":
    main()

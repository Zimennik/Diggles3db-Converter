#!/usr/bin/env python3
"""
Enhanced Diggles 3DB Converter with Material Mapping
----------------------------------------------------
Converts a 3DB model to FBX format with proper texture mapping.
This script creates a material mapping file and ensures correct textures are used.
"""

import os
import sys
import argparse
import subprocess
import importlib.util
import shutil
from typing import Dict, List, Optional

def print_header(title, char="="):
    """Print a header with decoration."""
    width = 80
    print(f"\n{char * width}")
    print(f"{title:^{width}}")
    print(f"{char * width}\n")

def create_material_mapping(model_path):
    """Create a material mapping file for the model."""
    # Import material_mapper module
    spec = importlib.util.spec_from_file_location(
        "material_mapper", 
        os.path.join("python3", "material_mapper.py")
    )
    
    if not spec:
        print("Error: Material mapper module not found")
        return False
    
    mapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mapper)
    
    # Get model name from path
    model_name = os.path.splitext(os.path.basename(model_path))[0]
    
    # Create output directory
    output_dir = os.path.join("exports", "fbx")
    os.makedirs(output_dir, exist_ok=True)
    
    # Parse the model
    print(f"Loading model for mapping: {model_path}")
    with open(model_path, 'rb') as f:
        file_data = f.read()
        # Import the parse_3db function
        sys.path.append("python3")
        from lib.parse_3db import parse_3db_file
        model = parse_3db_file(file_data)
    
    # Create material mapping
    mapping = mapper.create_material_mapping(model, output_dir, model_name)
    return mapping is not None

def run_conversion(model_path):
    """Run the model conversion script to create FBX file."""
    run_script = os.path.join("python3", "run.py")
    
    if not os.path.exists(run_script):
        print(f"Error: Conversion script not found: {run_script}")
        return False
    
    print(f"Converting model: {model_path}")
    cmd = [sys.executable, run_script, model_path]
    
    try:
        subprocess.run(cmd, check=True)
        print("Conversion completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Conversion failed with error code {e.returncode}")
        return False

def copy_textures_to_fbm(model_path):
    """Copy textures based on the material mapping to the FBM directory."""
    # Import material_mapper module
    spec = importlib.util.spec_from_file_location(
        "material_mapper", 
        os.path.join("python3", "material_mapper.py")
    )
    
    if not spec:
        print("Error: Material mapper module not found")
        return False
    
    mapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mapper)
    
    # Get model name from path
    model_name = os.path.splitext(os.path.basename(model_path))[0]
    
    # Load the mapping file
    mapping_file = os.path.join("exports", "fbx", f"materials_{model_name}.json")
    if not os.path.exists(mapping_file):
        print(f"Error: Mapping file not found: {mapping_file}")
        return False
    
    import json
    with open(mapping_file, 'r') as f:
        mapping = json.load(f)
    
    # Copy textures
    copied_textures = mapper.copy_mapped_textures(mapping, model_name)
    return len(copied_textures) > 0

def check_fbm_directory(model_name):
    """Check the FBM directory to see what textures are present."""
    fbm_dir = os.path.join("exports", "fbx", f"{model_name}.fbm")
    if not os.path.exists(fbm_dir):
        print(f"FBM directory not found: {fbm_dir}")
        return []
    
    textures = os.listdir(fbm_dir)
    print(f"Found {len(textures)} textures in FBM directory:")
    for texture in textures:
        print(f"  - {texture}")
    
    return textures

def safely_remove_directory(dir_path):
    """Safely remove a directory by first removing all files inside it."""
    if not os.path.exists(dir_path):
        return True
    
    try:
        # First remove all files in the directory
        for root, dirs, files in os.walk(dir_path, topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.chmod(file_path, 0o777)  # Try to change file permissions
                    os.remove(file_path)
                except Exception as e:
                    print(f"Could not remove file {file_path}: {e}")
            
            # Remove empty subdirectories
            for directory in dirs:
                dir_to_remove = os.path.join(root, directory)
                try:
                    os.rmdir(dir_to_remove)
                except Exception as e:
                    print(f"Could not remove subdirectory {dir_to_remove}: {e}")
        
        # Now try to remove the directory itself
        try:
            os.rmdir(dir_path)
            print(f"Safely removed directory: {dir_path}")
            return True
        except Exception as e:
            print(f"Could not remove directory {dir_path}: {e}")
            return False
    
    except Exception as e:
        print(f"Error while cleaning directory {dir_path}: {e}")
        return False

def main():
    """Main entry point."""
    print_header("DIGGLES MODEL CONVERTER WITH MATERIAL MAPPING", "#")
    
    # Set up arguments
    parser = argparse.ArgumentParser(
        description="Convert a 3DB model to FBX format with proper texture mapping",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_with_mapping.py assets/models/odin.3db
  python run_with_mapping.py assets/models/troll.3db
  python run_with_mapping.py assets/models/hamster.3db
        """
    )
    parser.add_argument('model_path', help='Path to the .3db model file')
    parser.add_argument('--mapping-only', action='store_true', help='Only create mapping, do not convert')
    parser.add_argument('--textures-only', action='store_true', help='Only copy textures, do not convert')
    parser.add_argument('--no-fix-materials', action='store_true', help='Skip automatic fixing of duplicate materials (enabled by default)')
    
    args = parser.parse_args()
    
    # Check if the model file exists
    if not os.path.exists(args.model_path):
        # Try with assets/models/ prefix
        alternative_path = os.path.join("assets", "models", args.model_path)
        if os.path.exists(alternative_path):
            args.model_path = alternative_path
        else:
            print(f"Error: Model file not found: {args.model_path}")
            return
    
    # Get model name
    model_name = os.path.splitext(os.path.basename(args.model_path))[0]
    
    # Clean texture directories
    texture_dirs = [
        os.path.join("exports", "fbx", "textures"),
        os.path.join("exports", "gltf", "textures"),
        os.path.join("textures")
    ]
    for dir_path in texture_dirs:
        if os.path.exists(dir_path):
            print(f"Removing texture directory: {dir_path}")
            safely_remove_directory(dir_path)
    
    # Create material mapping
    print_header(f"Creating Material Mapping for {model_name}")
    mapping_success = create_material_mapping(args.model_path)
    
    if not mapping_success:
        print("Error: Failed to create material mapping")
        return
    
    if args.mapping_only:
        print("Mapping complete. Skipping conversion as requested.")
        return
    
    # Copy textures to FBM directory BEFORE conversion
    print_header(f"Copying Textures for {model_name}")
    textures_success = copy_textures_to_fbm(args.model_path)
    
    if not textures_success:
        print("Error: Failed to copy textures")
        return
    
    # Check FBM directory before conversion
    fbm_textures = check_fbm_directory(model_name)
    if not fbm_textures:
        print("Error: No textures found in FBM directory")
        return
    
    # Make sure no textures directory exists before conversion
    for dir_path in texture_dirs:
        if os.path.exists(dir_path):
            print(f"Removing texture directory again: {dir_path}")
            safely_remove_directory(dir_path)
    
    # Run conversion AFTER textures are copied
    if not args.textures_only:
        print_header(f"Converting {model_name}")
        conversion_success = run_conversion(args.model_path)
        
        if not conversion_success:
            print("Error: Conversion failed")
            return
    else:
        print("Skipping conversion as requested.")
    
    # Check FBM directory
    fbm_textures = check_fbm_directory(model_name)
    
    # Apply material fixing automatically for all conversions
    # (skip only if explicitly requested with --mapping-only, --textures-only, or --no-fix-materials)
    if not args.textures_only and not args.mapping_only and not args.no_fix_materials:
        print_header(f"Fixing Duplicate Materials for {model_name}")
        
        # Get the FBX path
        fbx_path = os.path.join("exports", "fbx", f"{model_name}.fbx")
        
        if os.path.exists(fbx_path):
            # Import the material fixer module
            spec = importlib.util.spec_from_file_location(
                "fix_duplicate_materials", 
                os.path.join("python3", "fix_duplicate_materials.py")
            )
            
            if spec:
                fixer = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(fixer)
                
                # Create the Blender script
                script_path = fixer.create_blender_fixer_script()
                
                # Run Blender with the script
                fix_success = fixer.run_blender_with_script(fbx_path, script_path)
                
                # Clean up
                if os.path.exists(script_path):
                    os.remove(script_path)
                
                if fix_success:
                    print("Material fixing completed successfully")
                else:
                    print("Material fixing failed")
            else:
                print("Error: Material fixer module not found")
        else:
            print(f"Error: FBX file not found: {fbx_path}")
    
    # Cleanup temporary files - remove duplicate texture folders and mapping files
    print_header("Cleaning up temporary files", "-")
    
    # Files to clean up
    files_to_cleanup = [
        os.path.join("exports", "fbx", f"direct_materials_{model_name}.json"),
        os.path.join("exports", "fbx", f"materials_{model_name}.json")
    ]
    
    # Directories to clean up - DO NOT delete gltf!
    dirs_to_cleanup = [
        os.path.join("exports", "fbx", f"{model_name}_textures"),
        os.path.join("exports", "fbx", "textures"),  # Texture folder in fbx
        os.path.join("textures")  # Root texture directory, if created
    ]
    
    # Additionally find all directories with 'textures' in the name in the fbx directory
    # DO NOT touch the gltf directory!
    for root, dirs, files in os.walk(os.path.join("exports", "fbx")):
        for dirname in dirs:
            if "textures" in dirname.lower() and os.path.join(root, dirname) not in dirs_to_cleanup:
                # Exclude only .fbm directories that need to be preserved
                if not dirname.endswith(".fbm"):
                    dirs_to_cleanup.append(os.path.join(root, dirname))
    
    # Remove temporary files
    for file_path in files_to_cleanup:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Removed temporary file: {file_path}")
            except Exception as e:
                print(f"Error removing file {file_path}: {e}")
    
    # Remove temporary directories
    for dir_path in dirs_to_cleanup:
        if os.path.exists(dir_path):
            safely_remove_directory(dir_path)
    
    # Final status
    print_header("SUMMARY", "#")
    fbx_path = os.path.join("exports", "fbx", f"{model_name}.fbx")
    fbm_dir = os.path.join("exports", "fbx", f"{model_name}.fbm")
    
    print(f"Model: {model_name}")
    print(f"Mapping: {'Success' if mapping_success else 'Failed'}")
    if not args.textures_only:
        print(f"Conversion: {'Success' if os.path.exists(fbx_path) else 'Failed'}")
    print(f"Textures: {'Success' if len(fbm_textures) > 0 else 'Failed'}")
    if not args.textures_only and not args.mapping_only and not args.no_fix_materials:
        print(f"Material Fixing: {'Applied' if 'fix_success' in locals() and fix_success else 'Failed'}")
    
    if os.path.exists(fbx_path):
        print(f"FBX File: {fbx_path} ({os.path.getsize(fbx_path) / 1024:.1f} KB)")
    else:
        print("FBX File: Not found")
    
    if os.path.exists(fbm_dir):
        print(f"Textures: {len(fbm_textures)} files in {fbm_dir}")
    else:
        print("Textures: No .fbm directory found")
    
    print("\nSUGGESTION: To validate this model, import it into Blender or Unity")
    print("and check that all materials have the correct textures applied.")

if __name__ == "__main__":
    main()
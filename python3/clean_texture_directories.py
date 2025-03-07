#!/usr/bin/env python3
"""
Texture Directory Cleanup Script for Diggles 3DB Converter

This script cleans up all conflicting texture directories that might interfere
with proper texture assignment during model conversion.

Usage:
    python python3/clean_texture_directories.py
"""

import os
import sys
import shutil
import glob

def print_header(message):
    """Print a formatted header message."""
    print("\n" + "="*80)
    print(" " + message)
    print("="*80)

def clean_texture_directories():
    """Remove all texture directories that might cause conflicts."""
    print_header("CLEANING TEXTURE DIRECTORIES")
    
    # List of directories to remove
    directories_to_remove = [
        "exports/fbx/textures",
        "exports/gltf/textures",
        "textures",
        "exports/textures"
    ]
    
    # Find any .fbm directories with problematic names (e.g., .fbm.1234)
    for pattern in ["exports/fbx/*.fbm.*", "*.fbm.*"]:
        fbm_dirs = glob.glob(pattern)
        directories_to_remove.extend(fbm_dirs)
    
    # Track overall success
    overall_success = True
    
    # Remove each directory
    for directory in directories_to_remove:
        if os.path.exists(directory):
            try:
                shutil.rmtree(directory)
                print(f"✓ Removed: {directory}")
            except Exception as e:
                print(f"✗ Failed to remove {directory}: {e}")
                overall_success = False
                
                # Try to remove files individually
                try:
                    files = os.listdir(directory)
                    for file in files:
                        file_path = os.path.join(directory, file)
                        if os.path.isfile(file_path):
                            try:
                                os.remove(file_path)
                                print(f"  ✓ Removed file: {file_path}")
                            except Exception as e2:
                                print(f"  ✗ Failed to remove file {file_path}: {e2}")
                                overall_success = False
                    
                    # Try to remove the empty directory
                    try:
                        os.rmdir(directory)
                        print(f"  ✓ Removed empty directory: {directory}")
                    except Exception as e3:
                        print(f"  ✗ Failed to remove directory {directory}: {e3}")
                        overall_success = False
                except Exception as e4:
                    print(f"  ✗ Failed to process {directory}: {e4}")
                    overall_success = False
        else:
            print(f"✓ Directory does not exist: {directory}")
    
    # Check for .fbm directories inside exports/fbx
    fbm_dirs = []
    if os.path.exists("exports/fbx"):
        fbm_dirs = [d for d in os.listdir("exports/fbx") if d.endswith(".fbm")]
    
    if fbm_dirs:
        print(f"\nFound {len(fbm_dirs)} .fbm directories:")
        for fbm_dir in fbm_dirs:
            print(f"  - exports/fbx/{fbm_dir}")
        print("These directories are used for texture storage and are expected.")
    else:
        print("\nNo .fbm directories found. These will be created during conversion.")
    
    # Return final status
    if overall_success:
        print_header("CLEANUP SUCCESSFUL")
        print("All conflicting texture directories have been removed.")
        print("You can now run conversion with:")
        print("  python python3/run_with_mapping.py assets/models/your_model.3db")
        return 0
    else:
        print_header("CLEANUP PARTIALLY SUCCESSFUL")
        print("Some directories or files could not be removed.")
        print("You may need to manually delete them, or run this script with administrator privileges.")
        return 1

if __name__ == "__main__":
    sys.exit(clean_texture_directories())
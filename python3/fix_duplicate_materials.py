#!/usr/bin/env python3
"""
Fix duplicate materials in Blender exports

This script helps solve two critical issues with the 3DB to FBX conversion process:
1. Duplicate meshes with suffixes (.001, .002, etc.) causing material duplication
2. Incorrect texture assignment due to material name mismatches

How to use this script:
1. Run it directly: python fix_duplicate_materials.py path/to/model.3db
2. Or use it with the conversion process: python run_with_mapping.py path/to/model.3db --fix-materials
"""

import os
import sys
import argparse
import json
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

def create_blender_fixer_script():
    """Create a temporary Blender script that consolidates materials."""
    script_path = os.path.join("exports", "fix_materials_script.py")
    
    # Using single quotes for outer multi-line string to avoid syntax issues
    script_content = '''
import bpy
import os
import json
import sys

def log(message):
    # Log a message to the console
    print(f"[FIXER] {message}")

def get_base_name(name):
    # Extracts base name by removing Blender's numeric suffix.
    # For example: "mesh.001" -> "mesh"
    if '.' in name:
        parts = name.split('.')
        if parts[-1].isdigit() and len(parts[-1]) == 3:
            return '.'.join(parts[:-1])
    return name

def clean_hierarchy():
    # Clean up the scene hierarchy by removing any extra objects
    # and ensuring the proper structure: model_name/animation_name/frame_xx/...
    log("Cleaning hierarchy structure...")
    
    # First identify the root object of our model
    model_roots = []
    for obj in bpy.context.scene.objects:
        if obj.type == 'EMPTY' and not obj.parent:
            # This is potentially a root object
            model_roots.append(obj)
    
    # If we have exactly one root, it's likely the model name
    if len(model_roots) == 1:
        log(f"Found single model root: {model_roots[0].name}")
        root = model_roots[0]
    else:
        # We might have a duplicate hierarchy or extra objects
        log(f"Found {len(model_roots)} root objects, looking for the model root...")
        
        # Try to find the true model root by looking for animation children
        true_root = None
        for root in model_roots:
            has_animations = False
            for child in root.children:
                # Check if child has "frame_" children, which would indicate it's an animation
                for grandchild in child.children:
                    if grandchild.name.startswith("frame_"):
                        has_animations = True
                        break
                if has_animations:
                    true_root = root
                    break
        
        if true_root:
            log(f"Found true model root: {true_root.name}")
            root = true_root
        else:
            # No clear model root, just use the first one
            log(f"No clear model root found, using first root: {model_roots[0].name}")
            root = model_roots[0]
    
    # Fix any duplicate hierarchy issues
    fixed = 0
    
    # Check for a structure like model_name/model_name/animation_name/...
    if root.children and len(root.children) == 1 and root.children[0].name == root.name:
        duplicate_root = root.children[0]
        log(f"Found duplicate root: {duplicate_root.name}")
        
        # Move all children of the duplicate root to the real root
        for child in list(duplicate_root.children):
            log(f"Moving {child.name} to the true root")
            child.parent = root
            fixed += 1
        
        # Delete the empty duplicate root
        bpy.data.objects.remove(duplicate_root)
        log("Removed duplicate root object")
        fixed += 1
    
    # Remove any standalone cubes in the root of the scene
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and obj.name.lower() == 'cube' and not obj.parent:
            log(f"Removing standalone cube: {obj.name}")
            bpy.data.objects.remove(obj)
            fixed += 1
    
    log(f"Fixed {fixed} hierarchy issues")
    return fixed

def consolidate_materials():
    # Helps reduce the number of duplicate materials by consolidating ones with the same base name
    log("Analyzing materials for consolidation...")
    
    # Group materials by their base name (without .001, .002 etc. suffixes)
    material_groups = {}
    consolidated = 0
    
    for mat in bpy.data.materials:
        # Skip materials without a valid name
        if not mat.name:
            continue
            
        # Extract base name by removing Blender's numeric suffix if present
        base_name = get_base_name(mat.name)
            
        # Group materials by their base name
        if base_name not in material_groups:
            material_groups[base_name] = []
        material_groups[base_name].append(mat)
    
    # For each group of materials with the same base name
    for base_name, materials in material_groups.items():
        if len(materials) > 1:
            # Sort materials so that ones without suffix come first
            materials.sort(key=lambda m: m.name)
            
            # Use the first material as the primary one
            primary_mat = materials[0]
            
            # Replace all other materials with the primary
            for duplicate in materials[1:]:
                # Find all objects using this duplicate material
                for obj in bpy.context.scene.objects:
                    if obj.type == 'MESH':
                        for slot in obj.material_slots:
                            if slot.material == duplicate:
                                log(f"Replacing material {duplicate.name} with {primary_mat.name} on {obj.name}")
                                slot.material = primary_mat
                                consolidated += 1
    
    log(f"Consolidated {consolidated} material references")
    return consolidated

def main():
    # Check arguments
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        log("No FBX file specified")
        return
        
    fbx_path = args[0]
    
    # Import the FBX file
    log(f"Importing FBX file: {fbx_path}")
    try:
        bpy.ops.import_scene.fbx(filepath=fbx_path)
    except Exception as e:
        log(f"Error importing FBX: {e}")
        return
    
    # Fix duplicate materials
    log("Fixing duplicate materials...")
    consolidated = consolidate_materials()
    
    # Clean up hierarchy issues
    log("Cleaning hierarchy structure...")
    fixed_hierarchy = clean_hierarchy()
    
    # Export the fixed FBX
    log(f"Exporting fixed FBX file: {fbx_path}")
    try:
        bpy.ops.export_scene.fbx(
            filepath=fbx_path,
            use_selection=False,
            object_types={'ARMATURE', 'MESH', 'EMPTY'},
            use_mesh_modifiers=True,
            mesh_smooth_type='FACE',
            use_tspace=True,
            use_custom_props=True,
            path_mode='ABSOLUTE',
            embed_textures=False,
            bake_anim=False,
            axis_forward='-Z',
            axis_up='Y'
        )
        log(f"Successfully exported fixed FBX file")
    except Exception as e:
        log(f"Error exporting FBX: {e}")
        return

if __name__ == "__main__":
    main()
'''
    
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(script_path), exist_ok=True)
    
    # Write the script
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    return script_path

def run_blender_with_script(fbx_path, script_path):
    """Run Blender with the fixer script."""
    
    # Search for Blender executable
    blender_path = None
    possible_blender_paths = [
        r'C:\Program Files\Blender Foundation\Blender 4.3\blender.exe',
        r'C:\Program Files\Blender Foundation\Blender\blender.exe',
        r'C:\Program Files\Blender Foundation\Blender 3.6\blender.exe',
        r'C:\Program Files\Blender Foundation\Blender 3.5\blender.exe',
        r'C:\Program Files\Blender Foundation\Blender 3.4\blender.exe',
        r'C:\Program Files\Blender Foundation\Blender 3.3\blender.exe',
        r'C:\Program Files\Blender Foundation\Blender 3.2\blender.exe',
        r'C:\Program Files\Blender Foundation\Blender 3.1\blender.exe',
        r'C:\Program Files\Blender Foundation\Blender 3.0\blender.exe',
        r'C:\Program Files\Blender Foundation\Blender 2.9\blender.exe',
        r'C:\Program Files\Blender Foundation\Blender 2.8\blender.exe',
        '/Applications/Blender.app/Contents/MacOS/Blender',
        'blender'  # Try system PATH
    ]
    
    print("\nSearching for Blender...")
    for path in possible_blender_paths:
        try:
            # Check if Blender exists at this path
            if os.path.exists(path):
                print(f"Found Blender at: {path}")
                blender_path = path
                break
            elif shutil.which(path):
                resolved_path = shutil.which(path)
                print(f"Found Blender in PATH at: {resolved_path}")
                blender_path = resolved_path
                break
        except Exception as e:
            print(f"Error checking path {path}: {str(e)}")
            continue
    
    if not blender_path:
        print("Error: Blender not found. Cannot fix materials.")
        return False
    
    # Run Blender with the script
    cmd = [
        blender_path,
        '--background',
        '--python', script_path,
        '--',  # Separator for script arguments
        fbx_path
    ]
    
    print(f"Running Blender to fix materials in FBX file: {fbx_path}")
    try:
        subprocess.run(cmd, check=True)
        print("Material fixing completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running Blender: {e}")
        return False

def main():
    """Main entry point."""
    print_header("DIGGLES MODEL DUPLICATE MATERIAL FIXER", "#")
    
    # Set up arguments
    parser = argparse.ArgumentParser(
        description="Fix duplicate materials in FBX models exported from 3DB files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fix_duplicate_materials.py exports/fbx/odin.fbx
  python fix_duplicate_materials.py --model assets/models/troll.3db
        """
    )
    parser.add_argument('fbx_path', nargs='?', help='Path to the .fbx file to fix')
    parser.add_argument('--model', help='Path to the .3db model (will fix its corresponding FBX file)')
    
    args = parser.parse_args()
    
    # Determine the FBX path
    fbx_path = args.fbx_path
    
    # If --model is provided, find the corresponding FBX file
    if args.model:
        model_path = args.model
        
        # Check if the model file exists
        if not os.path.exists(model_path):
            # Try with assets/models/ prefix
            alternative_path = os.path.join("assets", "models", model_path)
            if os.path.exists(alternative_path):
                model_path = alternative_path
            else:
                print(f"Error: Model file not found: {model_path}")
                return
        
        # Get model name from path and construct FBX path
        model_name = os.path.splitext(os.path.basename(model_path))[0]
        fbx_path = os.path.join("exports", "fbx", f"{model_name}.fbx")
    
    # Ensure we have an FBX path
    if not fbx_path:
        print("Error: No FBX file specified")
        return
    
    # Check if the FBX file exists
    if not os.path.exists(fbx_path):
        print(f"Error: FBX file not found: {fbx_path}")
        return
    
    # Create the Blender script
    script_path = create_blender_fixer_script()
    
    # Run Blender with the script
    success = run_blender_with_script(fbx_path, script_path)
    
    # Clean up
    if os.path.exists(script_path):
        os.remove(script_path)
    
    if success:
        print_header("MATERIAL FIXING COMPLETED SUCCESSFULLY", "#")
        print(f"FBX file fixed: {fbx_path}")
    else:
        print_header("MATERIAL FIXING FAILED", "#")

if __name__ == "__main__":
    main()
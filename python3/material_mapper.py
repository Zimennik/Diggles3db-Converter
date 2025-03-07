#!/usr/bin/env python3
"""
Material Mapper for Diggles 3DB Models
--------------------------------------
Creates and manages material-to-texture mappings for Diggles models.
"""

import os
import json
import shutil
import sys
from collections import defaultdict
from typing import Dict, List, Tuple, Any, Optional

def decode_bytes(value):
    """Safely decode bytes to string."""
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8', errors='ignore')
        except Exception:
            return str(value)
    return str(value)

def clean_name(name):
    """Clean material or texture name for use in filenames."""
    if isinstance(name, bytes):
        name = decode_bytes(name)
    return name.replace("b'", "").replace("'", "").replace('"', '').strip()

def find_highest_res_texture(texture_name: str) -> Optional[str]:
    """Find the highest resolution version of a texture."""
    # Search directories in order of resolution preference
    texture_dirs = [
        os.path.join("assets", "textures", "m256"),
        os.path.join("assets", "textures", "m128"),
        os.path.join("assets", "textures", "m064"),
        os.path.join("assets", "textures", "Gray"),
        os.path.join("assets", "textures", "ClassIcons"),
        os.path.join("assets", "textures", "Misc"),
        os.path.join("assets", "textures")
    ]
    
    # Try exact match with different extensions
    for texture_dir in texture_dirs:
        if not os.path.exists(texture_dir):
            continue
            
        # Try exact filename match
        texture_path = os.path.join(texture_dir, texture_name)
        if os.path.exists(texture_path):
            return texture_path
            
        # Try with different extensions
        for ext in ['.tga', '.png', '.jpg', '.jpeg']:
            base_name = os.path.splitext(texture_name)[0]
            texture_path = os.path.join(texture_dir, base_name + ext)
            if os.path.exists(texture_path):
                return texture_path
    
    # If exact match fails, try case-insensitive match
    texture_name_lower = texture_name.lower()
    for texture_dir in texture_dirs:
        if not os.path.exists(texture_dir):
            continue
            
        for file in os.listdir(texture_dir):
            if file.lower() == texture_name_lower:
                return os.path.join(texture_dir, file)
                
            # Try with different extensions
            base_name = os.path.splitext(texture_name)[0].lower()
            file_base = os.path.splitext(file)[0].lower()
            if file_base == base_name:
                return os.path.join(texture_dir, file)
    
    return None

def create_material_mapping(model, output_dir: str, model_name: str) -> Dict:
    """Create a mapping from material names to texture paths."""
    # Create mapping dictionary
    mapping = {
        "model_name": model_name,
        "materials": {},
        "link_materials": {}
    }
    
    # First, extract material names and their textures from the model
    for i, material in enumerate(model.materials):
        mat_name = clean_name(material.name)
        
        # Get texture name from material path
        if isinstance(material.path, bytes):
            texture_path_parts = material.path.split(b'\\')
            texture_name = texture_path_parts[-1].decode('utf-8', errors='ignore') if texture_path_parts else ""
        else:
            texture_name = os.path.basename(material.path)
        
        # Find the best texture file
        texture_file = find_highest_res_texture(texture_name)
        
        mapping["materials"][mat_name] = {
            "index": i,
            "texture_name": texture_name,
            "texture_path": texture_file if texture_file else "",
            "links": []
        }
    
    # Analyze link mappings
    for mesh_idx, mesh in enumerate(model.meshes):
        for link_idx, link in enumerate(mesh.links):
            material_idx = link.material
            if material_idx < len(model.materials):
                material = model.materials[material_idx]
                mat_name = clean_name(material.name)
                
                # Add link position to material
                if link_idx not in mapping["materials"][mat_name]["links"]:
                    mapping["materials"][mat_name]["links"].append(link_idx)
                
                # Create link mapping
                link_key = f"link{link_idx}"
                if link_key not in mapping["link_materials"]:
                    mapping["link_materials"][link_key] = []
                
                if mat_name not in mapping["link_materials"][link_key]:
                    mapping["link_materials"][link_key].append(mat_name)
    
    # Special case handling for known models
    if "odin" in model_name.lower():
        # Check if Fifi03 material exists and ensure it has a texture
        fifi_found = False
        for mat_name in mapping["materials"]:
            if "fifi" in mat_name.lower():
                fifi_found = True
                fifi_texture = find_highest_res_texture("Fifi03.tga")
                if fifi_texture:
                    mapping["materials"][mat_name]["texture_path"] = fifi_texture
                    mapping["materials"][mat_name]["texture_name"] = "Fifi03.tga"
                    print(f"Special case: Mapped Fifi03 texture to {mat_name}")
        
        # Special case for Odin's primary texture
        odin_texture = find_highest_res_texture("Character_Odin_a.tga")
        if odin_texture:
            for mat_name in mapping["materials"]:
                if "odin" in mat_name.lower() and not mapping["materials"][mat_name]["texture_path"]:
                    mapping["materials"][mat_name]["texture_path"] = odin_texture
                    mapping["materials"][mat_name]["texture_name"] = "Character_Odin_a.tga"
                    print(f"Special case: Mapped Character_Odin_a.tga to {mat_name}")
    
    # Write the mapping to a JSON file
    mapping_file = os.path.join(output_dir, f"materials_{model_name}.json")
    with open(mapping_file, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"Created material mapping file: {mapping_file}")
    return mapping

def copy_mapped_textures(mapping: Dict, model_name: str) -> List[str]:
    """Copy all mapped textures to the model's fbm directory and create a direct mapping."""
    print(f"\n===== Creating direct texture mapping for model: {model_name} =====")
    
    # IMPORTANT - First, remove ALL texture directories to avoid wrong texture assignments
    texture_dirs_to_clear = [
        os.path.join("exports", "fbx", "textures"),       # FBX textures dir (deprecated)
        os.path.join("exports", "gltf", "textures"),      # GLTF textures dir (may contain wrong duplicates)
        os.path.join("textures"),                         # Root textures dir (if exists)
        os.path.join("exports", "fbx", f"{model_name}.fbm"),  # Old FBM directory to clean
        os.path.join("exports", "fbx", f"{model_name}_textures")  # Remove duplicate textures directory
    ]
    
    for textures_dir in texture_dirs_to_clear:
        if os.path.exists(textures_dir):
            print(f"Removing old textures directory: {textures_dir}")
            try:
                shutil.rmtree(textures_dir)
            except Exception as e:
                print(f"Error removing textures directory: {e}")
                # If we can't remove the directory, clear its contents
                if os.path.exists(textures_dir):
                    for file in os.listdir(textures_dir):
                        file_path = os.path.join(textures_dir, file)
                        if os.path.isfile(file_path):
                            try:
                                os.remove(file_path)
                            except Exception as e:
                                print(f"Error removing texture {file}: {e}")
    
    # Create only the .fbm directory - this is the standard format for FBX textures
    fbm_dir = os.path.join("exports", "fbx", f"{model_name}.fbm")
    os.makedirs(fbm_dir, exist_ok=True)
    
    # Create a direct material to texture path mapping
    direct_mapping = {}
    
    # Copy mapped textures to fbm directory
    copied_textures = []
    for mat_name, mat_info in mapping["materials"].items():
        if mat_info["texture_path"] and os.path.exists(mat_info["texture_path"]):
            # Clean material name for consistent keys
            material_clean = mat_name.replace("b'", "").replace("'", "").strip()
            
            # Copy to .fbm directory
            fbm_target_path = os.path.join(fbm_dir, mat_info["texture_name"])
            
            try:
                # Copy texture to fbm directory
                shutil.copy2(mat_info["texture_path"], fbm_target_path)
                
                # Add to direct mapping - use absolute paths for Blender
                direct_mapping[material_clean] = os.path.abspath(fbm_target_path)
                
                copied_textures.append(mat_info["texture_name"])
                print(f"Mapped material '{material_clean}' -> '{fbm_target_path}'")
            except Exception as e:
                print(f"Error copying texture {mat_info['texture_path']}: {e}")
    
    # Create a more efficient mapping that supports materials with suffixes
    # Instead of generating all possible suffixes (which would be too many),
    # we'll create a lookup map that maps base material names to their textures
    base_material_mapping = {}
    
    # Create a mapping of base material names (without suffixes) to texture paths
    for mat_name in list(mapping["materials"].keys()):
        material_clean = mat_name.replace("b'", "").replace("'", "").strip()
        
        # Store mapping from material name to texture path
        if material_clean in direct_mapping:
            base_material_mapping[material_clean] = direct_mapping[material_clean]
    
    # Create a separate 'suffixed_materials' section in our JSON mapping
    # This will be a lookup for blender_script.py to use when it encounters material names with suffixes
    print(f"Added base material mappings for {len(base_material_mapping)} materials")
    
    # Save the mappings to a temporary JSON file that will be used during conversion
    # but will be removed afterward
    direct_mapping_path = os.path.join("exports", "fbx", f"direct_materials_{model_name}.json")
    with open(direct_mapping_path, 'w') as f:
        json.dump({
            "model_name": model_name,
            "direct_mappings": direct_mapping,
            "base_material_mappings": base_material_mapping,
            "textures_dir": os.path.abspath(fbm_dir)  # Point directly to FBM dir
        }, f, indent=2)
    
    print(f"Created direct material->texture mapping at: {direct_mapping_path}")
    print(f"IMPORTANT: Using explicit texture mapping for precise material-texture assignment!")
    print(f"Copied {len(copied_textures)} textures to {fbm_dir}")
    print(f"Found {len(copied_textures)} textures in FBM directory:")
    for texture in sorted(copied_textures):
        print(f"  - {texture}")
    
    # Double check no other conflicting texture directories exist
    for textures_dir in texture_dirs_to_clear[:3]:  # Only check the first three (original unwanted dirs)
        if os.path.exists(textures_dir):
            print(f"WARNING: Texture directory still exists after deletion: {textures_dir}")
            print(f"Attempting to remove directory again")
            try:
                shutil.rmtree(textures_dir)
            except Exception as e:
                print(f"Failed to remove directory: {e}")
                print(f"THIS MAY CAUSE TEXTURE ISSUES - check Blender log!")
    
    return copied_textures

def main():
    """Main entry point."""
    import argparse
    from lib.parse_3db import parse_3db_file
    
    parser = argparse.ArgumentParser(description='Create material mapping for Diggles models')
    parser.add_argument('model_path', help='Path to the .3db model file')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.model_path):
        print(f"Error: Model file not found: {args.model_path}")
        return 1
    
    # Get model name from path
    model_name = os.path.splitext(os.path.basename(args.model_path))[0]
    
    # Create output directory
    output_dir = os.path.join("exports", "fbx")
    os.makedirs(output_dir, exist_ok=True)
    
    # Parse the model
    print(f"Loading model from {args.model_path}")
    with open(args.model_path, 'rb') as f:
        file_data = f.read()
        model = parse_3db_file(file_data)
    
    # Create material mapping
    mapping = create_material_mapping(model, output_dir, model_name)
    
    # Copy textures
    copied_textures = copy_mapped_textures(mapping, model_name)
    
    print(f"Material mapping created for {model_name}")
    print(f"  - {len(mapping['materials'])} materials mapped")
    print(f"  - {len(copied_textures)} textures copied to FBM directory")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
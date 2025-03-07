#!/usr/bin/env python3
"""
Diggles/Wiggles 3db Texture Directory Fixer

This script patches the model conversion process to ensure textures are
properly handled by:

1. Ensuring only the .fbm directory is used for textures
2. Eliminating the problematic exports/fbx/textures directory
3. Fixing texture path references in the Blender script

Usage:
    python fix_texture_directories.py

After running this script, use the normal conversion workflow:
    python python3/run_with_mapping.py assets/models/your_model.3db
"""

import os
import sys
import shutil
import glob
import re

def print_header(message):
    """Print a formatted header message."""
    print("\n" + "="*80)
    print(" " + message)
    print("="*80)

def clean_texture_directories():
    """Remove all texture directories that might cause conflicts."""
    print_header("CLEANING TEXTURE DIRECTORIES")
    
    directories_to_remove = [
        "exports/fbx/textures",
        "exports/gltf/textures",
        "textures"
    ]
    
    # Also find any misnamed .fbm directories
    fbm_dirs = glob.glob("exports/fbx/*.fbm.*")
    directories_to_remove.extend(fbm_dirs)
    
    for directory in directories_to_remove:
        if os.path.exists(directory):
            try:
                shutil.rmtree(directory)
                print(f"✓ Removed: {directory}")
            except Exception as e:
                print(f"✗ Failed to remove {directory}: {e}")
                
                # Try to remove files individually if rmtree fails
                try:
                    files = os.listdir(directory)
                    for file in files:
                        file_path = os.path.join(directory, file)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            print(f"  ✓ Removed file: {file_path}")
                    
                    # Try to remove the empty directory
                    os.rmdir(directory)
                    print(f"  ✓ Removed empty directory: {directory}")
                except Exception as e2:
                    print(f"  ✗ Failed to clean {directory} individually: {e2}")

def patch_export_fbx_binary():
    """Patch the export_fbx_binary.py file to use .fbm directory."""
    print_header("PATCHING EXPORT_FBX_BINARY.PY")
    
    file_path = "python3/lib/export_fbx_binary.py"
    if not os.path.exists(file_path):
        print(f"✗ File not found: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count original occurrences of textures directory creation
    textures_dir_count = content.count("target_dir = os.path.join(export_dir, 'textures')")
    print(f"Found {textures_dir_count} occurrences of textures directory creation")
    
    # 1. Replace textures directory clearing with complete removal
    old_clearing = (
        "# Clear the textures directory to avoid using old textures\n"
        "        textures_dir = os.path.join\\(export_dir, 'textures'\\)\n"
        "        if os.path.exists\\(textures_dir\\):\n"
        "            for file in os.listdir\\(textures_dir\\):\n"
        "                file_path = os.path.join\\(textures_dir, file\\)\n"
        "                if os.path.isfile\\(file_path\\):\n"
        "                    try:\n"
        "                        os.remove\\(file_path\\)\n"
        "                        print\\(f\"Removed old texture: {file_path}\"\\)\n"
        "                    except Exception as e:\n"
        "                        print\\(f\"Error removing {file_path}: {e}\"\\)"
    )
    
    new_clearing = (
        "# Completely remove the textures directory instead of just clearing it\n"
        "        textures_dir = os.path.join(export_dir, 'textures')\n"
        "        if os.path.exists(textures_dir):\n"
        "            try:\n"
        "                shutil.rmtree(textures_dir)\n"
        "                print(f\"Completely removed textures directory: {textures_dir}\")\n"
        "            except Exception as e:\n"
        "                print(f\"Error removing directory {textures_dir}: {e}\")\n"
        "                # If rmtree fails, try to remove files individually\n"
        "                try:\n"
        "                    for file in os.listdir(textures_dir):\n"
        "                        file_path = os.path.join(textures_dir, file)\n"
        "                        if os.path.isfile(file_path):\n"
        "                            try:\n"
        "                                os.remove(file_path)\n"
        "                                print(f\"Removed old texture: {file_path}\")\n"
        "                            except Exception as e2:\n"
        "                                print(f\"Error removing {file_path}: {e2}\")\n"
        "                except Exception as e3:\n"
        "                    print(f\"Error listing files in {textures_dir}: {e3}\")\n"
        "                \n"
        "                # Finally try to remove the empty directory\n"
        "                try:\n"
        "                    os.rmdir(textures_dir)\n"
        "                    print(f\"Removed empty directory: {textures_dir}\")\n"
        "                except Exception as e4:\n"
        "                    print(f\"Could not remove directory {textures_dir}: {e4}\")"
    )
    
    # Use regex for more flexible matching
    content = re.sub(old_clearing, new_clearing, content)
    
    # 2. Replace texture directory creation with FBM directory creation
    content = content.replace(
        "target_dir = os.path.join(export_dir, 'textures')",
        "target_dir = os.path.join(export_dir, f\"{model_name}.fbm\")"
    )
    
    # 3. Replace texture map references to point to FBM
    content = content.replace(
        "texture_map[material_name] = os.path.join('textures', target_filename)",
        "texture_map[material_name] = os.path.join(f\"{model_name}.fbm\", target_filename)"
    )
    
    # Write the modified content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Successfully patched: {file_path}")
    return True

def patch_export_py():
    """Patch export.py to use .fbm directory for textures."""
    print_header("PATCHING EXPORT.PY")
    
    file_path = "python3/lib/export.py"
    if not os.path.exists(file_path):
        print(f"✗ File not found: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Insert model name extraction near the start of copy_textures_for_export function
    model_extraction_code = """def copy_textures_for_export(model: Model, export_dir: str) -> Dict[str, str]:
    """Copy textures to the export directory and return a mapping of material names to texture paths."""
    # Extract model name for FBM directory
    model_basename = ""
    if model.name:
        try:
            if isinstance(model.name, bytes):
                model_basename = os.path.basename(model.name.decode('utf-8')).split('.')[0]
            else:
                model_basename = os.path.basename(str(model.name)).split('.')[0]
        except:
            pass
    
    if not model_basename:
        model_basename = os.path.basename(export_dir).split('.')[0]
    if not model_basename:
        model_basename = "model"  # Fallback name
    
    # Use FBM directory instead of textures subdirectory
    fbm_dir = os.path.join(os.path.dirname(export_dir), f"{model_basename}.fbm")
    os.makedirs(fbm_dir, exist_ok=True)
    
    # Remove any existing textures directory
    textures_dir = os.path.join(export_dir, 'textures')
    if os.path.exists(textures_dir):
        try:
            shutil.rmtree(textures_dir)
            print(f"Removed existing textures directory: {textures_dir}")
        except Exception as e:
            print(f"Warning: Could not remove textures directory: {e}")
    
    # Set texture export directory to FBM
    texture_export_dir = fbm_dir
    
    # Debug information
    print(f"Copying textures to FBM directory: {texture_export_dir}")"""
    
    # Replace the function definition and texture directory creation
    old_function_def = r"def copy_textures_for_export\(model: Model, export_dir: str\) -> Dict\[str, str\]:[\r\n\s]+\"\"\"Copy textures to the export directory and return a mapping of material names to texture paths\.\"\"\"[\r\n\s]+texture_export_dir = os\.path\.join\(export_dir, 'textures'\)[\r\n\s]+os\.makedirs\(texture_export_dir, exist_ok=True\)[\r\n\s]+# Debug information[\r\n\s]+print\(f\"Copying textures to: {texture_export_dir}\"\)"
    
    content = re.sub(old_function_def, model_extraction_code, content)
    
    # Replace texture path references in the texture map
    old_map_entry = r"texture_map\[material\.name\] = os\.path\.join\('textures', target_filename\)"
    new_map_entry = r"texture_map[material.name] = os.path.join(f\"{model_basename}.fbm\", target_filename)"
    
    content = re.sub(old_map_entry, new_map_entry, content)
    
    # Write the modified content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Successfully patched: {file_path}")
    return True

def enhance_blender_script():
    """Enhance blender_script.py to prioritize .fbm directory."""
    print_header("ENHANCING BLENDER_SCRIPT.PY")
    
    file_path = "python3/blender_script.py"
    if not os.path.exists(file_path):
        print(f"✗ File not found: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Enhance get_texture_for_model_part to strictly prioritize .fbm directory
    # Look for current fbm path resolution code
    fbm_resolution_pattern = r"# Check if we have a model-specific FBM directory[\r\n\s]+model_name = os\.environ\.get\(\"MODEL_NAME\", \"\"\)[\r\n\s]+if model_name:[\r\n\s]+# Try the FBM directory first[\r\n\s]+fbm_path = os\.path\.join\(os\.getcwd\(\), \"exports\", \"fbx\", f\"{model_name}\.fbm\"\)"
    
    enhanced_fbm_code = """    # Check if we have a model-specific FBM directory
    model_name = os.environ.get("MODEL_NAME", "")
    if model_name:
        # STRONG PRIORITY: Use FBM directory EXCLUSIVELY if it exists
        fbm_path = os.path.join(os.getcwd(), "exports", "fbx", f"{model_name}.fbm")
        
        # Log FBM directory status
        if os.path.exists(fbm_path):
            print(f"TEXTURE RESOLUTION: Found model-specific FBM directory: {fbm_path}")
            print(f"TEXTURE RESOLUTION: STRICT MODE - Will ONLY use textures from this directory")
        else:
            print(f"WARNING: FBM directory not found: {fbm_path}")"""
    
    content = re.sub(fbm_resolution_pattern, enhanced_fbm_code, content)
    
    # Force the use of .fbm directory for textures by blocking other directories
    # Find the texture search logic
    texture_search_pattern = r"# Check the FBM directory[\r\n\s]+if os\.path\.exists\(fbm_path\):[\r\n\s]+fbm_texture = os\.path\.join\(fbm_path, texture_name\)[\r\n\s]+if os\.path\.exists\(fbm_texture\):[\r\n\s]+print\(f\"Found texture in FBM directory: {fbm_texture}\"\)[\r\n\s]+return fbm_texture"
    
    enhanced_search_code = """            # Check the FBM directory
            if os.path.exists(fbm_path):
                fbm_texture = os.path.join(fbm_path, texture_name)
                if os.path.exists(fbm_texture):
                    print(f"Found texture in FBM directory: {fbm_texture}")
                    return fbm_texture
                else:
                    # STRICT MODE: If FBM directory exists but texture not found there,
                    # look only in the FBM directory and do not fall back to other locations
                    print(f"WARNING: Texture {texture_name} not found in FBM directory")
                    
                    # Debug available textures in FBM
                    if os.path.exists(fbm_path):
                        try:
                            fbm_contents = os.listdir(fbm_path)
                            if fbm_contents:
                                print(f"Available textures in FBM directory:")
                                for texture in sorted(fbm_contents)[:10]:  # Show first 10
                                    print(f"  - {texture}")
                                if len(fbm_contents) > 10:
                                    print(f"  - ... and {len(fbm_contents) - 10} more")
                            else:
                                print(f"FBM directory is empty!")
                        except Exception as e:
                            print(f"Error reading FBM directory: {e}")
                    
                    # Try case-insensitive search in FBM directory as last resort
                    try:
                        if os.path.exists(fbm_path):
                            fbm_files = os.listdir(fbm_path)
                            for fbm_file in fbm_files:
                                if fbm_file.lower() == texture_name.lower():
                                    full_path = os.path.join(fbm_path, fbm_file)
                                    print(f"Found case-insensitive match in FBM: {full_path}")
                                    return full_path
                    except Exception as e:
                        print(f"Error during case-insensitive search: {e}")
                    
                    # If we're in strict mode and can't find in FBM, use a placeholder texture
                    print(f"STRICT MODE: No fallback - using placeholder for {texture_name}")
                    return None"""
    
    content = re.sub(texture_search_pattern, enhanced_search_code, content)
    
    # Add better handling for material name suffixes (.392)
    material_cleanup_pattern = r"# Clean material name for matching[\r\n\s]+material_clean = material_name"
    
    enhanced_material_code = """    # Clean material name for matching
    material_clean = material_name
    
    # Special handling for numeric suffixes (like "kris_4_burg_a.392")
    # Extract base material name without numeric suffix
    base_match = re.match(r'([a-zA-Z0-9_]+(?:_[a-zA-Z0-9_]+)*)(?:\.\d+)?$', material_clean)
    if base_match:
        material_base = base_match.group(1)
        if material_base != material_clean:
            print(f"Extracted base material name: {material_base} from {material_clean}")
            material_clean = material_base"""
    
    content = re.sub(material_cleanup_pattern, enhanced_material_code, content)
    
    # Write the modified content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Successfully enhanced: {file_path}")
    return True

def main():
    """Main function to run all fixes."""
    print_header("TEXTURE DIRECTORY FIXER")
    print("This script will fix texture directory issues in the 3db converter.")
    
    # Clean up existing texture directories
    clean_texture_directories()
    
    # Patch the export files
    patch_export_fbx_binary()
    patch_export_py()
    enhance_blender_script()
    
    print_header("FIXES COMPLETED")
    print("The texture directory issues have been fixed.")
    print("\nTo convert a model, run:")
    print("  python python3/run_with_mapping.py assets/models/your_model.3db")
    print("\nIf you encounter any issues, run this fix script again before conversion.")

if __name__ == "__main__":
    main()
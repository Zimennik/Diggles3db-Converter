"""
Texture finder module for Blender script.
"""

import os
import bpy
import shutil
from .logger import log, error

def find_texture_files():
    """Find texture files, prioritizing the .fbm directory."""
    texture_files = {}
    
    # STRICTLY use ONLY the .fbm directory for textures - no fallbacks
    model_name = os.environ.get("MODEL_NAME", "")
    if model_name:
        fbm_dir = os.path.join(os.getcwd(), "exports", "fbx", f"{model_name}.fbm")
        
        # Log either way to be clear about what's happening
        if os.path.exists(fbm_dir):
            log(f"!!! IMPORTANT: Using ONLY .fbm directory for textures: {fbm_dir} !!!")
            
            # Look for textures in the FBM directory
            for file in os.listdir(fbm_dir):
                if file.lower().endswith(('.tga', '.png', '.jpg', '.jpeg')):
                    texture_path = os.path.join(fbm_dir, file)
                    file_lower = file.lower()
                    
                    # Add to the texture_files dictionary
                    texture_files[file_lower] = texture_path
                    
                    # Also store without extension
                    name_without_ext = os.path.splitext(file)[0].lower()
                    if name_without_ext not in texture_files:
                        texture_files[name_without_ext] = texture_path
                        
                    # Log special textures
                    is_special = False
                    if "hamster" in file_lower:
                        is_special = "hamster"
                    elif "fenris" in file_lower:
                        is_special = "fenris"
                    elif "baby" in file_lower:
                        is_special = "baby"
                    elif "kris_" in file_lower or "kristall" in file_lower:
                        is_special = "kristall"
                        
                    if is_special:
                        log(f"Found {is_special} texture in FBM: {file_lower} -> {texture_path}")
            
            log(f"Found {len(texture_files)} textures in FBM directory")
            
            # Even if we don't have textures, we STILL use ONLY the FBM directory
            # This is to force an error if texture files are missing, rather than silently falling back
            log("!!! CRITICAL: STRICT MODE - Using ONLY textures from .fbm directory, all other directories are BLOCKED !!!")
            return texture_files
        else:
            log(f"!!! WARNING: FBM directory not found: {fbm_dir} !!!")
            # Force empty texture list to prevent wrong texture lookups
            log("!!! CRITICAL: STRICT MODE - No FBM directory found, all texture lookups will fail !!!")
            return texture_files
    
    # Fallback texture directories if .fbm directory doesn't exist or is empty
    texture_dirs = [
        # Next check high resolution textures (preferred for quality)
        os.path.join(os.getcwd(), "assets", "textures", "m256"),
        
        # Then medium resolution
        os.path.join(os.getcwd(), "assets", "textures", "m128"),
        
        # Then lower resolution
        os.path.join(os.getcwd(), "assets", "textures", "m064"),
        os.path.join(os.getcwd(), "assets", "textures", "m032"),
        
        # Special directories
        os.path.join(os.getcwd(), "assets", "textures", "Gray"),
        os.path.join(os.getcwd(), "assets", "textures", "ClassIcons"),
        os.path.join(os.getcwd(), "assets", "textures", "Misc"),
        
        # Finally the base textures directory
        os.path.join(os.getcwd(), "assets", "textures"),
        
        # Also check the Blender file directory
        os.path.join(os.path.dirname(bpy.data.filepath), "textures"),
        os.path.dirname(bpy.data.filepath)]
    
    log("WARNING: FBM directory not found or empty, using fallback texture directories")
    
    for texture_dir in texture_dirs:
        if not os.path.exists(texture_dir):
            continue
            
        log(f"Searching for textures in: {texture_dir}")
        for file in os.listdir(texture_dir):
            if file.lower().endswith(('.tga', '.png', '.jpg', '.jpeg')):
                texture_path = os.path.join(texture_dir, file)
                file_lower = file.lower()
                
                # Track specific textures for debugging
                is_special = False
                if "hamster" in file_lower:
                    is_special = "hamster"
                elif "fenris" in file_lower:
                    is_special = "fenris"
                elif "baby" in file_lower:
                    is_special = "baby"
                elif "kris_" in file_lower or "kristall" in file_lower:
                    is_special = "kristall"
                
                # Only add if we haven't found this file before (higher resolution dirs are searched first)
                if file_lower not in texture_files:
                    texture_files[file_lower] = texture_path
                    if is_special:
                        log(f"Found {is_special} texture: {file_lower} -> {texture_path}")
                    
                    # Also store without extension
                    name_without_ext = os.path.splitext(file)[0].lower()
                    if name_without_ext not in texture_files:
                        texture_files[name_without_ext] = texture_path
                else:
                    # If found before, check if the current version has a better resolution
                    current_resolution = "m256" if "m256" in texture_path else \
                                "m128" if "m128" in texture_path else \
                                "m064" if "m064" in texture_path else "other"
                    
                    existing_path = texture_files[file_lower]
                    existing_resolution = "m256" if "m256" in existing_path else \
                                "m128" if "m128" in existing_path else \
                                "m064" if "m064" in existing_path else "other"
                    
                    resolution_priority = {"m256": 0, "m128": 1, "m064": 2, "other": 3}
                    
                    # Replace only if current has higher resolution
                    if resolution_priority[current_resolution] < resolution_priority[existing_resolution]:
                        texture_files[file_lower] = texture_path
                        if is_special:
                            log(f"Replacing with higher resolution {is_special} texture: {file_lower} -> {texture_path}")
                        
                        # Also update without extension
                        name_without_ext = os.path.splitext(file)[0].lower()
                        texture_files[name_without_ext] = texture_path
    
    # Debug output for special textures
    hamster_textures = [(name, path) for name, path in texture_files.items() if "hamster" in name]
    if hamster_textures:
        log(f"DEBUG: Found {len(hamster_textures)} hamster textures:")
        for name, path in hamster_textures:
            log(f"  - {name}: {path}")
            
    fenris_textures = [(name, path) for name, path in texture_files.items() if "fenris" in name]
    if fenris_textures:
        log(f"DEBUG: Found {len(fenris_textures)} fenris textures:")
        for name, path in fenris_textures:
            log(f"  - {name}: {path}")
            
    baby_textures = [(name, path) for name, path in texture_files.items() if "baby" in name]
    if baby_textures:
        log(f"DEBUG: Found {len(baby_textures)} baby textures:")
        for name, path in baby_textures:
            log(f"  - {name}: {path}")
            
    kristall_textures = [(name, path) for name, path in texture_files.items() if "kris_" in name or "kristall" in name]
    if kristall_textures:
        log(f"DEBUG: Found {len(kristall_textures)} kristall/kris textures:")
        for name, path in kristall_textures:
            log(f"  - {name}: {path}")
    
    log(f"Found {len(texture_files)} texture files")
    return texture_files

def force_copy_textures(textures_dir):
    """Copy all available textures to export directory to ensure proper matching."""
    if not os.path.exists(textures_dir):
        os.makedirs(textures_dir, exist_ok=True)
    
    log(f"Copying all textures to: {textures_dir}")
    copied_count = 0
    
    # Get a set of already existing files in target directory
    existing_files = set()
    if os.path.exists(textures_dir):
        for filename in os.listdir(textures_dir):
            existing_files.add(filename.lower())
    
    # Common texture directories to search
    texture_dirs = [
        # First check local project directories (may contain override textures)
        os.path.join(os.getcwd(), "exports", "fbx", "textures"),
        os.path.join(os.getcwd(), "textures"),
        
        # Next check high resolution textures (preferred for quality)
        os.path.join(os.getcwd(), "assets", "textures", "m256"),
        
        # Then medium resolution
        os.path.join(os.getcwd(), "assets", "textures", "m128"),
        
        # Then lower resolution
        os.path.join(os.getcwd(), "assets", "textures", "m064"),
        os.path.join(os.getcwd(), "assets", "textures", "m032"),
        
        # Special directories
        os.path.join(os.getcwd(), "assets", "textures", "Gray"),
        os.path.join(os.getcwd(), "assets", "textures", "ClassIcons"),
        os.path.join(os.getcwd(), "assets", "textures", "Misc"),
        
        # Finally the base textures directory
        os.path.join(os.getcwd(), "assets", "textures"),
        
        # Also check the Blender file directory
        os.path.join(os.path.dirname(bpy.data.filepath), "textures"),
        os.path.dirname(bpy.data.filepath)
    ]
    
    # Get model name for .fbm directory
    model_name = os.environ.get("MODEL_NAME", "")
    if model_name:
        fbm_dir = os.path.join(os.getcwd(), "exports", "fbx", f"{model_name}.fbm")
        if os.path.exists(fbm_dir):
            log(f"Prioritizing FBM directory for textures: {fbm_dir}")
            texture_dirs.insert(0, fbm_dir)  # Add as highest priority
    
    # Priority for specific textures
    critical_textures = [
        "Character_ZBaby_a.tga",
        "helme_huete_a.tga",
        "Character_Hamster_a_128.tga",
        "Character_Hamster_gross.tga",
        "Character_Drache_b_256.tga",
        "Elfen_Koerper.tga",
        "Elfen_Kopf.tga",
        "Troll001.tga",
        "Troll_Kopf001.tga",
        "kris_4_burg_a.tga",
        "kris_4_burg_b.tga",
        "kris_4_burg_bc.tga",
        "kris_4_brain_a.tga",
        "kristall_details_a.tga"
    ]
    
    # First copy critical textures that must be available
    for texture_name in critical_textures:
        for texture_dir in texture_dirs:
            source_path = os.path.join(texture_dir, texture_name)
            if os.path.exists(source_path):
                target_path = os.path.join(textures_dir, texture_name)
                if not os.path.exists(target_path):
                    try:
                        shutil.copy2(source_path, target_path)
                        log(f"Copied critical texture: {texture_name}")
                        copied_count += 1
                    except Exception as e:
                        error(f"Error copying texture {texture_name}: {str(e)}")
                break
    
    # Then copy all other textures
    for texture_dir in texture_dirs:
        if not os.path.exists(texture_dir):
            continue
            
        for filename in os.listdir(texture_dir):
            if not filename.lower().endswith(('.tga', '.png', '.jpg', '.jpeg')):
                continue
                
            # Skip if file already copied (for critical textures)
            if filename.lower() in existing_files:
                continue
                
            source_path = os.path.join(texture_dir, filename)
            target_path = os.path.join(textures_dir, filename)
            
            if not os.path.exists(target_path):
                try:
                    shutil.copy2(source_path, target_path)
                    existing_files.add(filename.lower())
                    copied_count += 1
                except Exception as e:
                    error(f"Error copying texture {filename}: {str(e)}")
    
    log(f"Copied {copied_count} textures to export directory")
    return copied_count
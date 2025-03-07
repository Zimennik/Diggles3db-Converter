import os
import shutil
import struct
import numpy as np
from typing import List, Dict, Tuple, Optional
import subprocess
import sys
import tempfile
import json
import time
import signal
import re
from lib.parse_3db import Model, Animation, Mesh, MeshLink
from lib.export_fbx import extract_texture_filename, get_texture_path, copy_textures_for_export, transform_point
from lib.export_config import (
    MATERIAL_SPECULAR, MATERIAL_ROUGHNESS, EMBED_TEXTURES, BLENDER_TIMEOUT,
    BLENDER_SCRIPT, MODEL_HIERARCHY, TEXTURE_SETTINGS
)

from lib.export import clean_material_name

# Function to load configuration
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"Error loading config file: {str(e)}")
    return {}

def validate_blender_script(script_path):
    """Validate and fix the Blender script to ensure it doesn't have syntax errors."""
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix common syntax errors with escape sequences
    replacements = [
        (r'\!=', '!='),
        (r'\!', '!'),
        (r'\<', '<'),
        (r'\>', '>'),
        (r'\==', '=='),
        (r'\=', '='),
        (r'\+', '+'),
        (r'\-', '-'),
        (r'\*', '*'),
        (r'\/', '/'),
        (r'\%', '%')
    ]
    
    # Apply all replacements
    for old, new in replacements:
        content = content.replace(old, new)
    
    # Write the corrected content back
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Validated and fixed Blender script: {script_path}")
    return True

def export_to_fbx_binary(model: Model, output_path: str = 'exports/fbx/model.fbx') -> None:
    """
    Export the model to binary FBX format with proper hierarchy and materials.
    
    This function attempts to use Blender as an intermediary to convert from glTF to binary FBX.
    If Blender is not available or an error occurs, falls back to the ASCII FBX export.
    
    The exported FBX will have the following hierarchy:
    - ModelName (root)
      - AnimationName (e.g. "walk", "run", etc.)
        - frame_xxx (e.g. "frame_000", "frame_001", etc.)
          - link_xx (mesh parts, e.g. "link_00", "link_01", etc.)
    
    Each mesh part will have a properly assigned material with textures.
    No animations are included - just the static frame hierarchy.
    """
    # Create directories for export if they don't exist
    export_dir = os.path.dirname(output_path)
    os.makedirs(export_dir, exist_ok=True)
    
    # Create a debug log file in the current directory
    debug_log_path = 'blender_debug.log'
    with open(debug_log_path, 'w') as debug_log:
        debug_log.write(f"=== BLENDER CONVERSION DEBUG LOG ===\n")
        debug_log.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        debug_log.write(f"Starting export_to_fbx_binary function\n")
        debug_log.write(f"Model name: {model.name}\n")
        debug_log.write(f"Output path: {output_path}\n")
        # Note: temp_gltf_path will be initialized later in the code
    
    # Load configuration
    config = load_config()
    
    # Check if Blender is available before starting the export
    blender_path = None
    
    # First check the path from the configuration file
    if 'blender_path' in config and config['blender_path']:
        config_blender_path = config['blender_path']
        print(f"Found Blender path in config: {config_blender_path}")
        if os.path.exists(config_blender_path):
            print(f"Verified Blender at config path: {config_blender_path}")
            blender_path = config_blender_path
    
    # If the path in configuration is not specified or invalid, look for Blender in standard locations
    if not blender_path:
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
        
        print("Searching for Blender installation...")
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
    
    # Обновляем таймаут из конфигурации, если указан
    if 'settings' in config and 'blender_timeout' in config['settings']:
        timeout = config['settings']['blender_timeout']
        if isinstance(timeout, (int, float)) and timeout > 0:
            print(f"Using Blender timeout from config: {timeout}s (overriding default: {BLENDER_TIMEOUT}s)")
            blender_timeout = timeout
        else:
            blender_timeout = BLENDER_TIMEOUT
    else:
        blender_timeout = BLENDER_TIMEOUT
    
    if not blender_path:
        print("\n" + "="*80)
        print("WARNING: Blender not found. Binary FBX export will not be available.")
        print("The converter will fall back to ASCII FBX export, which may not be compatible with all software.")
        print("Please install Blender for full functionality.")
        print("Recommended Blender paths checked:")
        for path in possible_blender_paths:
            exists = "Found" if os.path.exists(path) else "Not found"
            in_path = "Found in PATH" if shutil.which(path) else "Not in PATH"
            print(f"  - {path}: {exists}, {in_path}")
        print("="*80 + "\n")
        
        # Fall back to ASCII FBX export
        print("\nBlender not found. Falling back to ASCII FBX export...")
        print("NOTE: ASCII FBX files are not supported by many applications, including Blender itself.")
        print("Please install Blender for full compatibility.")
        from lib.export_fbx import export_to_fbx
        export_to_fbx(model, output_path)
        return
    
    # Create a temporary directory for intermediate files
    temp_dir = tempfile.mkdtemp()
    try:
        # Export to glTF first with the actual model name (not temp_model)
        model_name = os.path.splitext(os.path.basename(output_path))[0]
        temp_gltf_path = os.path.join(temp_dir, f'{model_name}.gltf')
        
        # Update debug log with temp_gltf_path now that it's initialized
        with open(debug_log_path, 'a') as debug_log:
            debug_log.write(f"Temp GLTF path: {temp_gltf_path}\n")
            debug_log.write(f"Blender executable: {blender_path}\n\n")
        
        from lib.export import export_to_gltf
        export_to_gltf(model, temp_gltf_path)
        
        # Completely remove the textures directory instead of just clearing it
        textures_dir = os.path.join(export_dir, 'textures')
        if os.path.exists(textures_dir):
            try:
                shutil.rmtree(textures_dir)
                print(f"Completely removed textures directory: {textures_dir}")
            except Exception as e:
                print(f"Error removing directory {textures_dir}: {e}")
                # If rmtree fails, try to remove files individually
                try:
                    for file in os.listdir(textures_dir):
                        file_path = os.path.join(textures_dir, file)
                        if os.path.isfile(file_path):
                            try:
                                os.remove(file_path)
                                print(f"Removed old texture: {file_path}")
                            except Exception as e2:
                                print(f"Error removing {file_path}: {e2}")
                except Exception as e3:
                    print(f"Error listing files in {textures_dir}: {e3}")
                
                # Finally try to remove the empty directory
                try:
                    os.rmdir(textures_dir)
                    print(f"Removed empty directory: {textures_dir}")
                except Exception as e4:
                    print(f"Could not remove directory {textures_dir}: {e4}")
        
        # Copy textures to the export directory
        # First look for special case textures directly
        special_textures = {}
        
        # Find special textures like Character_ZBaby_a.tga
        for i, material in enumerate(model.materials):
            # Special handling for baby texture
            texture_found = False
            
            # Convert material name to string if it's bytes
            material_name_str = ""
            if isinstance(material.name, bytes):
                try:
                    material_name_str = material.name.decode('utf-8', errors='ignore')
                except Exception:
                    material_name_str = str(material.name)
            else:
                material_name_str = str(material.name)
                
            material_name_lower = material_name_str.lower()
            
            if "zbaby" in material_name_lower or "baby" in material_name_lower:
                # Priority order - high resolution first!
                baby_paths = [
                    # Highest resolution first
                    os.path.join('assets', 'textures', 'm256', 'Character_ZBaby_a.tga'),
                    
                    # Medium resolution next
                    os.path.join('assets', 'textures', 'm128', 'Character_ZBaby_a.tga'),
                    
                    # Lower resolutions last
                    os.path.join('assets', 'textures', 'm064', 'Character_ZBaby_a.tga'),
                    os.path.join('assets', 'textures', 'Gray', 'Character_ZBaby_a.tga')
                ]
                
                # Try each baby path
                for path in baby_paths:
                    if os.path.exists(path):
                        texture_name = os.path.basename(path)
                        # Create FBM directory instead of textures directory
                        fbm_dir = os.path.join(export_dir, f"{model_name}.fbm")
                        os.makedirs(fbm_dir, exist_ok=True)
                        target_path = os.path.join(fbm_dir, texture_name)
                        
                        print(f"Copying texture: {path} -> {target_path}")
                        shutil.copy2(path, target_path)
                        special_textures[material.name] = path
                        texture_found = True
                        break
            
            # Check for hat/helmet texture
            elif ("huete" in material_name_lower or "helme" in material_name_lower or 
                  "hat" in material_name_lower):
                # Priority order - high resolution first!
                helmet_paths = [
                    # Try highest resolution first
                    os.path.join('assets', 'textures', 'm256', 'helme_huete_a.tga'),
                    
                    # Medium resolution next
                    os.path.join('assets', 'textures', 'm128', 'helme_huete_a.tga'),
                    
                    # Lower resolution last
                    os.path.join('assets', 'textures', 'm064', 'helme_huete_a.tga'),
                    os.path.join('assets', 'textures', 'helme_huete_a.tga')
                ]
                
                # Try each helmet path
                for path in helmet_paths:
                    if os.path.exists(path):
                        texture_name = os.path.basename(path)
                        # Create FBM directory instead of textures directory
                        fbm_dir = os.path.join(export_dir, f"{model_name}.fbm")
                        os.makedirs(fbm_dir, exist_ok=True)
                        target_path = os.path.join(fbm_dir, texture_name)
                        
                        print(f"Copying texture: {path} -> {target_path}")
                        shutil.copy2(path, target_path)
                        special_textures[material.name] = path
                        texture_found = True
                        break
            
            # Check for hamster texture
            elif ("hamster" in material_name_lower):
                print(f"DEBUG: Found hamster material: {material_name_lower}")
                # Priority order - high resolution first!
                hamster_paths = [
                    # Try highest resolution first - note that Character_Hamster_a_128.tga doesn't exist in m256
                    os.path.join('assets', 'textures', 'm256', 'Character_Hamster_gross.tga'),
                    
                    # Medium resolution next
                    os.path.join('assets', 'textures', 'm128', 'Character_Hamster_a_128.tga'),
                    os.path.join('assets', 'textures', 'm128', 'Character_Hamster_b_128.tga'),
                    
                    # Lower resolution last
                    os.path.join('assets', 'textures', 'm064', 'Character_Hamster_a_128.tga'),
                    os.path.join('assets', 'textures', 'Gray', 'Character_Hamster_a_128.tga'),
                    os.path.join('assets', 'textures', 'Gray', 'Character_Hamster_gross.tga')
                ]
                
                print(f"DEBUG: Checking hamster texture paths:")
                # Try each hamster path and print its existence
                for path in hamster_paths:
                    path_exists = os.path.exists(path)
                    print(f"  - {path}: {'EXISTS' if path_exists else 'NOT FOUND'}")
                    
                # Now try to use them
                for path in hamster_paths:
                    if os.path.exists(path):
                        texture_name = os.path.basename(path)
                        # Create FBM directory instead of textures directory
                        fbm_dir = os.path.join(export_dir, f"{model_name}.fbm")
                        os.makedirs(fbm_dir, exist_ok=True)
                        target_path = os.path.join(fbm_dir, texture_name)
                        
                        print(f"DEBUG: Selected hamster texture: {path}")
                        print(f"Copying texture: {path} -> {target_path}")
                        try:
                            shutil.copy2(path, target_path)
                            special_textures[material.name] = path
                            texture_found = True
                            # Also copy to additional directories to ensure it can be found
                            temp_texture_dir = os.path.join(temp_dir, 'textures')
                            os.makedirs(temp_texture_dir, exist_ok=True)
                            temp_target_path = os.path.join(temp_texture_dir, texture_name)
                            shutil.copy2(path, temp_target_path)
                            print(f"Also copied to: {temp_target_path}")
                        except Exception as e:
                            print(f"Warning: Error copying texture {path}: {str(e)}")
                        break
        
        # Also copy textures to the temporary directory to ensure they're available for Blender
        temp_texture_dir = os.path.join(temp_dir, 'textures')
        os.makedirs(temp_texture_dir, exist_ok=True)
        
        for material_name, texture_path in special_textures.items():
            # Copy to temp dir for Blender
            texture_name = os.path.basename(texture_path)
            clean_name = clean_material_name(material_name)
            target_filename = texture_name
            target_path = os.path.join(temp_texture_dir, target_filename)
            try:
                shutil.copy2(texture_path, target_path)
                print(f"Copied texture to temp dir: {texture_path} -> {target_path}")
            except Exception as e:
                print(f"Warning: Could not copy texture {texture_path} to temp dir: {str(e)}")
        
        # Now use the regular texture copy function for any textures we didn't find
        print(f"\nDEBUG: Searching for textures with copy_textures_for_export()")
        texture_map = copy_textures_for_export(model, export_dir)
        
        # Print the texture map to debug
        print(f"\nDEBUG: Texture map from copy_textures_for_export():")
        for mat_name, tex_path in texture_map.items():
            print(f"  - {mat_name}: {tex_path}")
        
        # Add any special textures we found - IMPORTANT: these should override any conflicting textures
        print(f"\nDEBUG: Adding special textures to texture map:")
        for material_name, texture_path in special_textures.items():
            texture_name = os.path.basename(texture_path)
            clean_name = clean_material_name(material_name)
            target_filename = texture_name
            texture_map[material_name] = os.path.join(f"{model_name}.fbm", target_filename)
            print(f"  - Added special texture: {material_name} -> {texture_path}")
        
        # Remove existing output file if it exists to ensure it's overwritten
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
                print(f"Removed existing file: {output_path}")
            except Exception as e:
                print(f"Warning: Could not remove existing file {output_path}: {str(e)}")
        
        # Copy the external Blender script
        blender_script = os.path.join(temp_dir, 'convert_to_fbx.py')
        
        # Use script from config or fall back to default scripts
        custom_script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), BLENDER_SCRIPT)
        modular_script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'new_blender_script.py')
        fixed_script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'blender_script_fixed.py')
        regular_script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'blender_script.py')
        
        if os.path.exists(custom_script_path):
            # Use the configured script
            shutil.copy2(custom_script_path, blender_script)
            print(f"Using Blender script from config: {custom_script_path}")
        elif os.path.exists(modular_script_path):
            # Use the new modular script
            shutil.copy2(modular_script_path, blender_script)
            print(f"Using NEW MODULAR Blender script: {modular_script_path}")
        elif os.path.exists(fixed_script_path):
            # Use the fixed script with main() function
            shutil.copy2(fixed_script_path, blender_script)
            print(f"Using fixed Blender script with main() function from: {fixed_script_path}")
        elif os.path.exists(regular_script_path):
            # Fall back to the regular script
            if os.path.exists(regular_script_path + ".fixed"):
                shutil.copy2(regular_script_path + ".fixed", blender_script)
            else:
                shutil.copy2(regular_script_path, blender_script)
            # Validate and fix the copied script
            validate_blender_script(blender_script)
            print(f"Using original Blender script from: {regular_script_path}")
        else:
            print(f"Warning: No Blender script found!")
            print("Falling back to ASCII FBX export...")
            from lib.export_fbx import export_to_fbx
            export_to_fbx(model, output_path)
            return
        
        with open(blender_script, 'r') as f:
            print(f"Blender script size: {len(f.read())} bytes")
        
        # Set essential environment variables
        os.environ['ANIMATION_FPS'] = '6'
        os.environ['ANIMATION_FRAME_DURATION'] = '2'
        os.environ['EXPORT_TEXTURES'] = 'True'  # Force texture export
        os.environ['DEBUG_MATERIALS'] = 'True'  # Enable materials debugging
        os.environ['MODEL_NAME'] = model_name     # Pass the model name to use as root
        
        # Also create a simple JSON config to pass more settings to Blender
        config_file = os.path.join(temp_dir, 'export_config.json')
        with open(config_file, 'w') as f:
            # Copy texture map to the config so Blender script knows exactly 
            # which textures to use for which materials
            material_texture_map = {}
            for material_name, texture_path in texture_map.items():
                material_str = str(material_name)
                if isinstance(material_name, bytes):
                    try:
                        material_str = material_name.decode('utf-8', errors='ignore')
                    except:
                        material_str = str(material_name)
                
                # Clean up material name
                material_str = material_str.replace("b'", "").replace("'", "")
                material_texture_map[material_str] = texture_path
            
            # Create a mapping from link positions to material names
            link_position_map = {}
            
            # Analyze entire mesh structure
            for mesh_idx, mesh in enumerate(model.meshes):
                for link_idx, link in enumerate(mesh.links):
                    if link.material < len(model.materials):
                        material = model.materials[link.material]
                        material_str = str(material.name)
                        if isinstance(material.name, bytes):
                            try:
                                material_str = material.name.decode('utf-8', errors='ignore')
                            except:
                                material_str = str(material.name)
                        
                        material_str = material_str.replace("b'", "").replace("'", "")
                        
                        if link_idx not in link_position_map:
                            link_position_map[link_idx] = []
                        
                        if material_str not in link_position_map[link_idx]:
                            link_position_map[link_idx].append(material_str)
            
            # Log the material-texture mappings
            with open(debug_log_path, 'a') as debug_log:
                debug_log.write("\n=== MATERIAL-TEXTURE MAPPINGS ===\n")
                for mat, tex in material_texture_map.items():
                    debug_log.write(f"{mat} -> {tex}\n")
                
                debug_log.write("\n=== LINK POSITION MAPPINGS ===\n")
                for link_idx, materials in link_position_map.items():
                    debug_log.write(f"Link position {link_idx}: {', '.join(materials[:5])}")
                    if len(materials) > 5:
                        debug_log.write(f" and {len(materials) - 5} more...")
                    debug_log.write("\n")
            
            config = {
                "model_name": model_name,
                "texture_dirs": TEXTURE_SETTINGS["SEARCH_SUBDIRS"],
                "default_texture_ext": TEXTURE_SETTINGS["DEFAULT_EXTENSION"],
                "material_texture_map": material_texture_map,
                "link_position_map": link_position_map,
                "material_settings": {
                    "specular": MATERIAL_SPECULAR,
                    "roughness": MATERIAL_ROUGHNESS,
                    "color_space": TEXTURE_SETTINGS["COLOR_SPACE"]
                }
            }
            json.dump(config, f, indent=2)
        
        success = False  # Flag to track if binary FBX export was successful
        
        try:
            # Run Blender with the script
            cmd = [
                blender_path,
                '--background',
                '--python', blender_script,
                '--',  # Separator for script arguments
                temp_gltf_path,
                output_path,
                str(EMBED_TEXTURES).lower(),  # Pass EMBED_TEXTURES as a string argument
                config_file  # Pass the config file path
            ]
            
            print(f"Running Blender to convert glTF to binary FBX...")
            print(f"This may take a while for complex models (timeout: {blender_timeout}s)...")
            
            # Add a progress indicator
            start_time = time.time()
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for process to complete with a simple progress indicator and timeout
            try:
                # Start reading output in a non-blocking way
                stdout_data = []
                stderr_data = []
                
                # Check for FBX file creation periodically
                while process.poll() is None:
                    elapsed = time.time() - start_time
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        print(f"FBX file created after {elapsed:.1f}s, waiting for Blender to complete...")
                        # File exists, but we still wait for the process to complete
                        
                    # Print progress every 5 seconds
                    if int(elapsed) % 5 == 0:
                        print(f"Processing... (elapsed: {elapsed:.1f}s, timeout: {BLENDER_TIMEOUT}s)")
                        
                    # Read any available output
                    while True:
                        output = process.stdout.readline()
                        if output:
                            stdout_data.append(output.decode('utf-8', errors='ignore').strip())
                        else:
                            break
                            
                    # Check for timeout
                    if elapsed > blender_timeout:
                        print(f"Timeout reached ({blender_timeout}s). Terminating Blender process...")
                        process.terminate()
                        # Give it a moment to terminate gracefully
                        time.sleep(2)
                        if process.poll() is None:
                            process.kill()
                        break
                        
                    # Small sleep to avoid CPU thrashing
                    time.sleep(0.5)
                
                # Get any remaining output
                stdout, stderr = process.communicate()
                if stdout:
                    stdout_data.append(stdout.decode('utf-8', errors='ignore').strip())
                if stderr:
                    stderr_data.append(stderr.decode('utf-8', errors='ignore').strip())
                
                # Write output to log file for debugging
                with open(debug_log_path, 'a') as debug_log:
                    debug_log.write("\n=== BLENDER STDOUT ===\n")
                    debug_log.write("\n".join(stdout_data))
                    debug_log.write("\n\n=== BLENDER STDERR ===\n")
                    debug_log.write("\n".join(stderr_data))
                
                # Check if the process completed successfully
                if process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    print(f"Blender completed successfully after {time.time() - start_time:.1f}s")
                    print(f"FBX file created: {output_path} ({os.path.getsize(output_path) / 1024:.1f} KB)")
                    success = True
                else:
                    error_message = "\n".join(stderr_data)
                    print(f"Blender process failed or timed out (returncode: {process.returncode})")
                    if error_message:
                        print(f"Error message: {error_message}")
                    print(f"See {debug_log_path} for details")
                    
                    # Check if output file exists but process failed
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        print("Warning: Output file exists but Blender process failed. File may be incomplete.")
                        success = True  # Still treat as success if we have a file
                
            except KeyboardInterrupt:
                print("\nProcess interrupted by user. Terminating Blender...")
                process.terminate()
                time.sleep(2)
                if process.poll() is None:
                    process.kill()
                print("Process terminated.")
            
            # If the binary FBX export failed, fall back to ASCII FBX export
            if not success:
                print("Binary FBX export failed or timed out. Falling back to ASCII FBX export...")
                from lib.export_fbx import export_to_fbx
                export_to_fbx(model, output_path)
        
        except Exception as e:
            print(f"Error running Blender: {str(e)}")
            print("Falling back to ASCII FBX export...")
            from lib.export_fbx import export_to_fbx
            export_to_fbx(model, output_path)
    
    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: Could not remove temporary directory {temp_dir}: {str(e)}")

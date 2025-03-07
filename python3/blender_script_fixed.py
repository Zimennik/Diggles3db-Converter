import bpy
import os
import json
import sys
import re
import traceback
import shutil
import datetime

# Create a log file for debugging
log_file_path = 'blender_log.txt'
log_file = open(log_file_path, 'w')

def log(message, level="INFO"):
    """Log a message with timestamp and level."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    log_message = f"[{timestamp}] [{level}] {message}"
    print(log_message)
    log_file.write(log_message + "\n")
    log_file.flush()  # Ensure the message is written immediately

def error(message):
    """Log an error message."""
    log(message, "ERROR")

log("DEBUG: Fixed Blender script is starting!")
log(f"DEBUG: Python version: {sys.version}")
log(f"DEBUG: Arguments: {sys.argv}")
log(f"DEBUG: Working directory: {os.getcwd()}")

def find_texture_files():
    """Find texture files in standard directories."""
    texture_files = {}
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
        os.path.dirname(bpy.data.filepath)]
    
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
                if "hamster" in file_lower or "fifi" in file_lower or "odin" in file_lower:
                    is_special = file_lower
                    log(f"Found special texture: {file_lower} -> {texture_path}")
                
                # Only add if we haven't found this file before (higher resolution dirs are searched first)
                if file_lower not in texture_files:
                    texture_files[file_lower] = texture_path
                    
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
                            log(f"Replacing with higher resolution texture: {file_lower} -> {texture_path}")
                        
                        # Also update without extension
                        name_without_ext = os.path.splitext(file)[0].lower()
                        texture_files[name_without_ext] = texture_path
    
    # Check for specific textures we always want to log
    odin_textures = [(name, path) for name, path in texture_files.items() if "odin" in name]
    if odin_textures:
        log(f"DEBUG: Found {len(odin_textures)} Odin textures:")
        for name, path in odin_textures:
            log(f"  - {name}: {path}")
            
    fifi_textures = [(name, path) for name, path in texture_files.items() if "fifi" in name]
    if fifi_textures:
        log(f"DEBUG: Found {len(fifi_textures)} Fifi textures:")
        for name, path in fifi_textures:
            log(f"  - {name}: {path}")
    
    log(f"Found {len(texture_files)} texture files")
    return texture_files

def setup_material(obj, material_name, texture_path):
    """Create material with texture for an object."""
    if not texture_path or not os.path.exists(texture_path):
        error(f"Texture not found: {texture_path}")
        return
        
    # Create new material or get existing one
    if material_name in bpy.data.materials:
        mat = bpy.data.materials[material_name]
    else:
        mat = bpy.data.materials.new(name=material_name)
    
    # Setup nodes
    mat.use_nodes = True
    node_tree = mat.node_tree
    node_tree.nodes.clear()
    
    # Create shader
    bsdf = node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    # Set material properties with error checking (different Blender versions have different property names)
    try:
        # Attempt to set specular value - names may vary by Blender version
        if 'Specular' in bsdf.inputs:
            bsdf.inputs['Specular'].default_value = 0.1  # Low specular
        elif 'Specular IOR Level' in bsdf.inputs:
            bsdf.inputs['Specular IOR Level'].default_value = 0.1
        
        # Attempt to set roughness value
        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = 0.8  # High roughness for non-metal look
    except Exception as e:
        error(f"Could not set material properties: {str(e)}. This is not critical.")
    
    # Create output
    output = node_tree.nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    
    # Create texture node
    tex_image = node_tree.nodes.new('ShaderNodeTexImage')
    tex_image.location = (-300, 0)
    
    # Create UV mapping node
    uv_node = node_tree.nodes.new('ShaderNodeTexCoord')
    uv_node.location = (-500, 0)
    
    # Load texture
    try:
        image = None
        # Check if image already loaded
        for img in bpy.data.images:
            if img.filepath == texture_path:
                image = img
                log(f"Using existing image: {img.name}")
                break
                
        if not image:
            image = bpy.data.images.load(texture_path)
            log(f"Loaded new image: {image.name} from {texture_path}")
        
        tex_image.image = image
        
        # Set proper colorspace
        if hasattr(image, 'colorspace_settings'):
            image.colorspace_settings.name = 'sRGB'
    except Exception as e:
        error(f"Error loading texture {texture_path}: {str(e)}")
        return mat
        
    # Connect nodes
    node_tree.links.new(uv_node.outputs['UV'], tex_image.inputs['Vector'])
    node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    node_tree.links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])
    
    # If image has alpha channel, set up transparency
    if image.depth == 32:  # 32-bit depth indicates RGBA
        mat.blend_method = 'BLEND'
        node_tree.links.new(tex_image.outputs['Alpha'], bsdf.inputs['Alpha'])
    
    # Assign material to object
    if len(obj.material_slots) == 0:
        obj.data.materials.append(mat)
    else:
        obj.material_slots[0].material = mat
        
    log(f"Created material {material_name} with texture {os.path.basename(texture_path)}")
    return mat

def load_material_mappings():
    """Load material mappings from the model's JSON file if available."""
    # Check if we have a model name
    model_name = os.environ.get('MODEL_NAME')
    if not model_name:
        # Try to get from command line arguments
        args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
        if len(args) > 0:
            model_name = os.path.splitext(os.path.basename(args[0]))[0]
    
    if not model_name:
        log("No model name available, cannot load material mappings")
        return None
        
    # Check for mapping file
    mapping_file = os.path.join(os.getcwd(), f"materials_{model_name}.json")
    if not os.path.exists(mapping_file):
        # Try alternate locations
        alt_locations = [
            os.path.join(os.getcwd(), "exports", "fbx", f"materials_{model_name}.json"),
            os.path.join(os.path.dirname(os.getcwd()), "exports", "fbx", f"materials_{model_name}.json"),
            os.path.join(os.path.dirname(bpy.data.filepath), f"materials_{model_name}.json")
        ]
        
        for alt_file in alt_locations:
            if os.path.exists(alt_file):
                mapping_file = alt_file
                break
                
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, 'r') as f:
                mapping_data = json.load(f)
                log(f"Loaded material mappings from {mapping_file}")
                return mapping_data
        except Exception as e:
            error(f"Error loading material mappings: {str(e)}")
            
    log(f"No material mapping file found for {model_name}")
    return None

def extract_model_info(obj_name):
    """Extract animation name, frame number, and link number from object name."""
    # Normalize object name to string if it's bytes
    if isinstance(obj_name, bytes):
        try:
            obj_name = obj_name.decode('utf-8', errors='ignore')
        except:
            obj_name = str(obj_name)
    
    obj_name_str = str(obj_name)
    
    # Common regex patterns for object naming formats
    # IMPORTANT: The order of patterns matters - more specific patterns first
    patterns = [
        # Handle our new material-based naming format (without explicit link)
        r"([^_]+(?:_[^_]+)*)_frame(\d+)_(.+)",  # anim_name_frame01_MaterialName
        
        # Handle older naming formats that included link numbers for backward compatibility
        r"([^_]+(?:_[^_]+)*)_frame(\d+)_link(\d+)_(.+)",  # anim_name_frame01_link00_MaterialName        
        r"b'([^']+)'_frame(\d+)_link(\d+)",      # b'full_anim_name'_frame01_link00
        r"([^_]+(?:_[^_]+)*)_frame(\d+)_link(\d+)",  # full_anim_name_frame01_link00
        r"([^_]+(?:_[^_]+)*)_frame_(\d+)_link_(\d+)",  # full_anim_name_frame_01_link_00
        
        # Alternative formats
        r"(.+)_frame(\d+)_part(\d+)",            # anim_name_frame01_part00
        
        # More flexible pattern as fallback
        r"(.*?)_?frame_?(\d+)_?(?:link|part)?_?(\d+)?(?:_(.+))?"  # any_pattern_frame_00_anything
    ]
    
    # Try each pattern
    for pattern in patterns:
        try:
            match = re.search(pattern, obj_name_str)
            if match:
                # Get full animation name from match
                anim_name = match.group(1)
                
                # Clean up animation name - remove byte string markers but preserve the full name
                if isinstance(anim_name, str):
                    if anim_name.startswith("b'") and anim_name.endswith("'"):
                        anim_name = anim_name[2:-1]
                    elif anim_name.startswith("b'"):
                        anim_name = anim_name[2:]
                    elif anim_name.startswith("b\"") and anim_name.endswith("\""):
                        anim_name = anim_name[2:-1]
                    elif anim_name.startswith("'") and anim_name.endswith("'"):
                        anim_name = anim_name[1:-1]
                    elif anim_name.endswith("'"):
                        anim_name = anim_name[:-1]
                    
                    # Remove escape characters if any
                    anim_name = anim_name.replace('\\', '')
                    
                    # If the name is still enclosed in quotes, remove them
                    if (anim_name.startswith("'") and anim_name.endswith("'")) or \
                       (anim_name.startswith('"') and anim_name.endswith('"')):
                        anim_name = anim_name[1:-1]
                
                # Extract material name if present
                material_name = None
                
                # Handle new naming format (anim_name_frame01_MaterialName)
                # First pattern has: group(1)=anim_name, group(2)=frame, group(3)=material_name
                if pattern.startswith(r"([^_]+(?:_[^_]+)*)_frame(\d+)_(.+)"):
                    material_name = match.group(3)
                    log(f"Extracted material name (new format): '{material_name}' from object name")
                    
                    # Generate a link number from material name - just for uniqueness
                    link_num = hash(material_name) % 100  # Use hash for a semi-stable number
                    
                    # Convert frame number to integer
                    try:
                        frame_num = int(match.group(2))
                        log(f"Extracted animation: '{anim_name}', frame: {frame_num}, material: '{material_name}' from {obj_name}")
                        return anim_name, frame_num, link_num
                    except (ValueError, TypeError) as e:
                        error(f"Error parsing frame number from {obj_name}: {str(e)}")
                        continue
                
                # Handle older formats with explicit link numbers
                # Extract material name if present (4th group in some patterns)
                elif len(match.groups()) >= 4 and match.group(4):
                    material_name = match.group(4)
                    log(f"Extracted material name: '{material_name}' from object name")
                
                # Store the material name on the object for later use
                # We don't know if obj_name is a string or an object that can have attributes,
                # so we'll just store it if we have material_name
                if material_name:
                    try:
                        # Try using attribute
                        obj_name.original_material = material_name
                    except:
                        # Handle failure silently, we'll extract from name later if needed
                        pass
                
                # Convert frame and link to integers
                try:
                    frame_num = int(match.group(2))
                    link_num = None
                    
                    # Try to get link number from pattern
                    if len(match.groups()) >= 3 and match.group(3):
                        try:
                            link_num = int(match.group(3))
                        except (ValueError, TypeError):
                            # If not a valid number, use hash of material name if available
                            if material_name:
                                link_num = hash(material_name) % 100
                            else:
                                link_num = 0
                    else:
                        # If no link number found, use hash of material name if available
                        if material_name:
                            link_num = hash(material_name) % 100
                        else:
                            link_num = 0
                    
                    log(f"Extracted animation: '{anim_name}', frame: {frame_num}, link: {link_num}, material: '{material_name}' from {obj_name}")
                    return anim_name, frame_num, link_num
                except (ValueError, TypeError) as e:
                    error(f"Error parsing frame/link numbers from {obj_name}: {str(e)}")
        except Exception as e:
            error(f"Error processing pattern {pattern} on {obj_name_str}: {str(e)}")
            continue
                
    # No match found - log this for debugging
    log(f"Failed to extract model info from object name: {obj_name}")
    return None, None, None

def process_gltf_structure(gltf_path, model_name=None):
    """Organize imported GLTF into proper hierarchy."""
    # Import GLTF
    result = bpy.ops.import_scene.gltf(filepath=gltf_path)
    if 'FINISHED' not in result:
        error(f"Failed to import GLTF: {result}")
        return False
        
    log(f"Imported {len(bpy.context.scene.objects)} objects from GLTF")
    
    # Remove default cube if it exists
    for obj in bpy.data.objects:
        if obj.name.lower() == 'cube':
            bpy.data.objects.remove(obj)
            log("Removed default cube")
    
    # If no model name provided, get from filename
    if not model_name:
        model_name = os.path.splitext(os.path.basename(gltf_path))[0]
        log(f"Using model name from filename: {model_name}")
        
    # Create root object
    root = bpy.data.objects.new(model_name, None)
    bpy.context.scene.collection.objects.link(root)
    
    # Find textures and load material mappings
    textures = find_texture_files()
    material_mappings = load_material_mappings()
    
    # Extract animation, frame, and link information from object names
    animations = {}
    
    # Track imported objects that don't match naming pattern
    unmatched_objects = []
    
    for obj in list(bpy.context.scene.objects):
        if obj.type != 'MESH' or obj == root:
            continue
            
        # Try to extract animation, frame, and link from object name
        anim_name, frame_num, link_num = extract_model_info(obj.name)
        
        if anim_name is not None and frame_num is not None and link_num is not None:
            # Create entry in animations dict
            if anim_name not in animations:
                animations[anim_name] = {}
            
            if frame_num not in animations[anim_name]:
                animations[anim_name][frame_num] = []
                
            animations[anim_name][frame_num].append((obj, link_num))
            
            # CRITICAL CHANGE: Instead of using link number for material name, 
            # use the material name from the object name or from mapping
            material_name = None
            
            # First try to extract material name directly from object name
            # Our new naming scheme: anim_name_frameXX_MaterialName
            obj_name_parts = obj.name.split("_frame")
            if len(obj_name_parts) >= 2:
                # Get everything after frame number
                frame_part = obj_name_parts[1]
                # Split frame number from material name
                frame_material_parts = frame_part.split("_", 1)  # Split on first underscore
                if len(frame_material_parts) >= 2:
                    # Parts should be ["XX", "MaterialName"]
                    potential_material_name = frame_material_parts[1]
                    if potential_material_name:
                        material_name = potential_material_name
                        log(f"Extracted material name directly from object name: {material_name}")
            
            # If no material name extracted from object name, try mappings
            if not material_name and material_mappings and "link_materials" in material_mappings:
                link_key = f"link{link_num}"
                if link_key in material_mappings["link_materials"]:
                    # Use the first material mapped to this link
                    if material_mappings["link_materials"][link_key]:
                        material_name = material_mappings["link_materials"][link_key][0]
                        log(f"Using mapped material name for {obj.name}: {material_name}")
            
            # If no mapping found, fall back to the original method
            if not material_name:
                # Try to find material name elsewhere in object name
                for part in obj.name.split("_"):
                    # Check if any part looks like a material name (not a common keyword)
                    if part and part.lower() not in ["link", "frame", "anim", "animation", "part"]:
                        if len(part) > 3:  # Exclude short parts
                            material_name = part
                            log(f"Extracted potential material name from object name part: {material_name}")
                            break
            
            # If still no material name, use link number as fallback
            if not material_name:
                material_name = f"link{link_num}_material"
                log(f"No material name found, using default based on link number: {material_name}")
            
            # Find texture path for this material
            texture_path = None
            
            # First check if there's a mapped texture in the material mappings
            if material_mappings and "materials" in material_mappings:
                if material_name in material_mappings["materials"]:
                    # Use the texture path from mapping
                    texture_file = material_mappings["materials"][material_name]["texture_name"]
                    log(f"Found texture mapping for {material_name}: {texture_file}")
                    
                    # Try to find the texture in our texture files
                    texture_path = None
                    
                    # Check for exact match
                    if texture_file.lower() in textures:
                        texture_path = textures[texture_file.lower()]
                        log(f"Found exact texture match: {texture_path}")
                    
                    # Check with filename only (no extension)
                    if not texture_path:
                        base_name = os.path.splitext(texture_file)[0].lower()
                        if base_name in textures:
                            texture_path = textures[base_name]
                            log(f"Found texture match by base name: {texture_path}")
                    
                    # Check for texture in current directory
                    if not texture_path:
                        local_path = os.path.join(os.path.dirname(bpy.data.filepath), texture_file)
                        if os.path.exists(local_path):
                            texture_path = local_path
                            log(f"Found texture in local directory: {texture_path}")
            
            # If no texture path from mapping, try to find one
            if not texture_path:
                # Look for texture name in object's material
                if obj.material_slots and obj.material_slots[0].material:
                    existing_material = obj.material_slots[0].material
                    
                    # If material has a texture, use that
                    if existing_material.node_tree and existing_material.node_tree.nodes:
                        for node in existing_material.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image:
                                texture_path = node.image.filepath
                                if texture_path and os.path.exists(texture_path):
                                    log(f"Using existing texture: {texture_path}")
                                    break
            
            # If still no texture, try to find one based on material name
            if not texture_path and material_name:
                # Try to match texture name to material name
                material_name_lower = material_name.lower()
                
                # Remove common prefixes/suffixes that might interfere with matching
                clean_material_name = material_name_lower
                for prefix in ["material_", "link", "misc_material_"]:
                    if clean_material_name.startswith(prefix):
                        clean_material_name = clean_material_name[len(prefix):]
                
                # First try exact matches
                exact_matches = []
                for tex_name, tex_path in textures.items():
                    # Try exact match of clean name to texture name
                    if clean_material_name == tex_name.lower():
                        exact_matches.append((tex_path, 1))  # Top priority
                    elif clean_material_name in tex_name.lower():
                        exact_matches.append((tex_path, 2))  # Second priority
                    elif material_name_lower == tex_name.lower():
                        exact_matches.append((tex_path, 3))  # Third priority
                    elif material_name_lower in tex_name.lower():
                        exact_matches.append((tex_path, 4))  # Fourth priority
                    elif any(part in tex_name.lower() for part in clean_material_name.split("_") if len(part) > 3):
                        exact_matches.append((tex_path, 5))  # Fifth priority
                
                # Sort by priority and use the best match
                if exact_matches:
                    exact_matches.sort(key=lambda x: x[1])  # Sort by priority (lower is better)
                    texture_path = exact_matches[0][0]
                    log(f"Found texture matching material name (priority {exact_matches[0][1]}): {texture_path}")
                    
                # If no matches yet, try more flexible matching
                if not texture_path:
                    for tex_name, tex_path in textures.items():
                        # Check if any portion of material name is in texture name
                        for part in clean_material_name.split("_"):
                            if len(part) > 3 and part in tex_name.lower():  # Only check substantial parts
                                texture_path = tex_path
                                log(f"Found texture matching material name part '{part}': {texture_path}")
                                break
                        if texture_path:
                            break
                            
                # Last resort: check if texture name appears in material name
                if not texture_path:
                    for tex_name, tex_path in textures.items():
                        tex_base = os.path.splitext(os.path.basename(tex_name))[0].lower()
                        if len(tex_base) > 3 and tex_base in material_name_lower:
                            texture_path = tex_path
                            log(f"Found texture where texture name appears in material name: {texture_path}")
                            break
            
            # If still no texture, try model-specific textures based on link number
            if not texture_path:
                # Link 0 is usually the body, link 1 is usually accessories/head/etc.
                if link_num == 0:
                    # Look for body textures
                    for tex_name, tex_path in textures.items():
                        if "body" in tex_name or "koerper" in tex_name or model_name.lower() in tex_name:
                            texture_path = tex_path
                            log(f"Using body texture for link 0: {texture_path}")
                            break
                elif link_num == 1:
                    # Look for head/hat textures
                    for tex_name, tex_path in textures.items():
                        if "head" in tex_name or "kopf" in tex_name or "hat" in tex_name or "muetze" in tex_name:
                            texture_path = tex_path
                            log(f"Using head/hat texture for link 1: {texture_path}")
                            break
            
            # Special case for Odin model
            if "odin" in model_name.lower():
                if link_num == 0:
                    # Find Odin texture
                    for tex_name, tex_path in textures.items():
                        if "odin" in tex_name.lower():
                            texture_path = tex_path
                            log(f"Special case: Using Odin texture for link 0: {texture_path}")
                            break
                elif link_num == 1:
                    # Find Fifi texture
                    for tex_name, tex_path in textures.items():
                        if "fifi" in tex_name.lower():
                            texture_path = tex_path
                            log(f"Special case: Using Fifi texture for link 1: {texture_path}")
                            break
            
            # Create and apply material with texture
            if texture_path:
                setup_material(obj, material_name, texture_path)
            else:
                log(f"No texture found for {obj.name} (anim: {anim_name}, frame: {frame_num}, link: {link_num})")
        else:
            log(f"Object name doesn't match pattern: {obj.name}")
            unmatched_objects.append(obj)
    
    # Handle unmatched objects if any
    if unmatched_objects:
        log(f"Found {len(unmatched_objects)} objects with non-standard names")
        # Add a "misc" animation for these objects
        misc_anim = "misc"
        if misc_anim not in animations:
            animations[misc_anim] = {0: []}
        
        for i, obj in enumerate(unmatched_objects):
            # Create a simple link number based on index
            animations[misc_anim][0].append((obj, i))
            
            # Extract material name if available
            material_name = None
            if obj.material_slots and obj.material_slots[0].material:
                material_name = obj.material_slots[0].material.name
            else:
                material_name = f"misc_material_{i}"
            
            # Find appropriate texture
            texture_path = None
            
            # Check if we have a mapping for this material
            if material_mappings and "materials" in material_mappings:
                if material_name in material_mappings["materials"]:
                    texture_file = material_mappings["materials"][material_name]["texture_name"]
                    texture_path = None
                    
                    # Try to find the texture
                    if texture_file.lower() in textures:
                        texture_path = textures[texture_file.lower()]
                        log(f"Found mapped texture for misc object: {texture_path}")
                    
                    # Check for texture in current directory
                    if not texture_path:
                        local_path = os.path.join(os.path.dirname(bpy.data.filepath), texture_file)
                        if os.path.exists(local_path):
                            texture_path = local_path
            
            # If no mapped texture, try to find one
            if not texture_path:
                # Try to match texture name to material name using the same improved logic as earlier
                if material_name:
                    material_name_lower = material_name.lower()
                    
                    # Remove common prefixes/suffixes
                    clean_material_name = material_name_lower
                    for prefix in ["material_", "link", "misc_material_"]:
                        if clean_material_name.startswith(prefix):
                            clean_material_name = clean_material_name[len(prefix):]
                    
                    # Try prioritized matching
                    exact_matches = []
                    for tex_name, tex_path in textures.items():
                        if clean_material_name == tex_name.lower():
                            exact_matches.append((tex_path, 1))  # Top priority
                        elif clean_material_name in tex_name.lower():
                            exact_matches.append((tex_path, 2))  # Second priority
                        elif material_name_lower == tex_name.lower():
                            exact_matches.append((tex_path, 3))  # Third priority
                        elif material_name_lower in tex_name.lower():
                            exact_matches.append((tex_path, 4))  # Fourth priority
                        elif any(part in tex_name.lower() for part in clean_material_name.split("_") if len(part) > 3):
                            exact_matches.append((tex_path, 5))  # Fifth priority
                    
                    # Use best match
                    if exact_matches:
                        exact_matches.sort(key=lambda x: x[1])
                        texture_path = exact_matches[0][0]
                        log(f"Found texture matching misc material name (priority {exact_matches[0][1]}): {texture_path}")
                    
                    # Try partial matching
                    if not texture_path:
                        for tex_name, tex_path in textures.items():
                            for part in clean_material_name.split("_"):
                                if len(part) > 3 and part in tex_name.lower():
                                    texture_path = tex_path
                                    log(f"Found texture matching misc material name part '{part}': {texture_path}")
                                    break
                            if texture_path:
                                break
                    
                    # Check if texture name appears in material name
                    if not texture_path:
                        for tex_name, tex_path in textures.items():
                            tex_base = os.path.splitext(os.path.basename(tex_name))[0].lower()
                            if len(tex_base) > 3 and tex_base in material_name_lower:
                                texture_path = tex_path
                                log(f"Found texture where texture name appears in misc material name: {texture_path}")
                                break
            
            # If still no texture, try model-specific textures
            if not texture_path and model_name:
                for tex_name, tex_path in textures.items():
                    if model_name.lower() in tex_name:
                        texture_path = tex_path
                        log(f"Using model-based texture for misc object: {texture_path}")
                        break
            
            # Create and apply material with texture
            if texture_path:
                setup_material(obj, material_name, texture_path)
            else:
                log(f"No texture found for misc object {obj.name}")
    
    # Build hierarchy
    log(f"Building hierarchy for {len(animations)} animations")
    for anim_name, frames in animations.items():
        # Create animation object
        anim_obj = bpy.data.objects.new(anim_name, None)
        bpy.context.scene.collection.objects.link(anim_obj)
        anim_obj.parent = root
        
        for frame_num, objects in frames.items():
            # Create frame object with standardized name format
            frame_obj = bpy.data.objects.new(f"frame_{frame_num:03d}", None)
            bpy.context.scene.collection.objects.link(frame_obj)
            frame_obj.parent = anim_obj
            
            # Parent objects to frame object
            for obj, link_num in objects:
                # Get material name if available - try to extract from object name since material info could be there
                material_name = None
                
                # Try to extract material from object name directly
                anim_part, frame_part, remaining = None, None, None
                
                if "_frame" in obj.name:
                    parts = obj.name.split("_frame")
                    if len(parts) >= 2:
                        anim_part = parts[0]
                        remaining = "_frame" + parts[1]
                        
                        # Extract material from remaining part (after frame number)
                        frame_parts = remaining.split("_", 2)  # Split only on first 2 underscores
                        if len(frame_parts) >= 3:
                            # frame_parts should be ["_frameXX", "", "MaterialName"]
                            material_name = frame_parts[2]
                            log(f"Extracted material from object name: {material_name}")
                
                # If not found in object name, check if we stored it during extraction
                # For Blender objects we need to be more careful with custom attributes
                if not material_name:
                    try:
                        if 'original_material' in obj:
                            material_name = obj['original_material']
                            log(f"Using stored material name from obj['original_material']: {material_name}")
                    except:
                        # Fallback method
                        try:
                            if hasattr(obj, 'original_material') and obj.original_material:
                                material_name = obj.original_material
                                log(f"Using stored material name from obj.original_material: {material_name}")
                        except:
                            pass
                
                # Create a name that combines link number and material name for clarity
                if material_name:
                    # Use material name directly for the link name
                    base_link_name = f"{material_name}"
                else:
                    # Fallback to using link number if no material name available
                    base_link_name = f"link_{link_num:02d}"
                
                # Check for existing objects with the same base name in this frame
                existing_links = [child for child in frame_obj.children 
                                 if child.name == base_link_name or 
                                    child.name.startswith(f"{base_link_name}_") or
                                    child.name.startswith(f"{base_link_name}.")
                                 ]
                
                # Create a unique name
                if existing_links:
                    # Use incrementing index for unique name
                    link_name = f"{base_link_name}_{len(existing_links)}"
                    log(f"Creating unique link name {link_name} (instead of {base_link_name}) to avoid duplicates")
                else:
                    link_name = base_link_name
                
                # Rename object and assign parent
                obj.name = link_name
                obj.parent = frame_obj
                
                # Log hierarchy for debugging
                log(f"Added {link_name} to {frame_obj.name} in {anim_obj.name}")
                
                # Create a links dictionary for the frame if not already created
                if not hasattr(frame_obj, "links_dict"):
                    frame_obj["links_dict"] = {str(link_num): obj.name}
                else:
                    # Add to existing dictionary
                    links_data = frame_obj["links_dict"]
                    links_data[str(link_num)] = obj.name
    
    # Select all objects for export
    bpy.ops.object.select_all(action='SELECT')
    bpy.context.view_layer.objects.active = root
    
    log("Hierarchy building complete")
    return True

def main():
    """Main function called when script is executed directly."""
    try:
        log("Executing main function in Blender script")
        
        # Check if we have the command-line arguments we need
        if len(sys.argv) < 5:
            error(f"Not enough arguments. Usage: blender --python script.py -- input.gltf output.fbx [embed_textures] [config_file]")
            sys.exit(1)
            
        # Get arguments after -- separator
        args = sys.argv[sys.argv.index("--") + 1:]
        if len(args) < 2:
            error(f"Missing arguments after --. Found: {args}")
            sys.exit(1)
            
        input_gltf = args[0]
        output_fbx = args[1]
        embed_textures = args[2].lower() == 'true' if len(args) > 2 else False
        config_file = args[3] if len(args) > 3 else None
        
        log(f"Input GLTF: {input_gltf}")
        log(f"Output FBX: {output_fbx}")
        log(f"Embed textures: {embed_textures}")
        
        # Load config if provided
        model_name = None
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    if 'model_name' in config:
                        model_name = config['model_name']
                        log(f"Using model name from config: {model_name}")
            except Exception as e:
                error(f"Error loading config: {str(e)}")
        
        # Also check environment variable for model name
        if not model_name and 'MODEL_NAME' in os.environ:
            model_name = os.environ['MODEL_NAME']
            log(f"Using model name from environment: {model_name}")
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_fbx)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        # Clear default scene
        bpy.ops.wm.read_factory_settings(use_empty=True)
        
        # Process the GLTF file and create proper hierarchy
        if not process_gltf_structure(input_gltf, model_name):
            error("Failed to process GLTF structure")
            sys.exit(1)
        
        # Make sure we select all objects for export
        bpy.ops.object.select_all(action='SELECT')
        
        # Export to FBX
        log(f"FBX export starting... '{output_fbx}'")
        # Create the FBM directory if it doesn't exist
        fbm_dir = os.path.splitext(output_fbx)[0] + ".fbm"
        os.makedirs(fbm_dir, exist_ok=True)
        
        # Get model name (used for setting up texture paths)
        model_basename = os.path.splitext(os.path.basename(output_fbx))[0]
        
        # Update all texture paths to point to the .fbm directory
        for img in bpy.data.images:
            img_name = os.path.basename(img.filepath)
            # Set the filepath to point to the .fbm directory
            img.filepath = os.path.join(model_basename + ".fbm", img_name)
            log(f"Updated texture path: {img.filepath}")
        
        # Export to FBX with ABSOLUTE path mode to preserve our custom paths
        export_result = bpy.ops.export_scene.fbx(
            filepath=output_fbx,
            use_selection=False,  # Export all objects, not just selected
            object_types={'ARMATURE', 'MESH', 'EMPTY'},
            use_mesh_modifiers=True,
            mesh_smooth_type='FACE',
            use_tspace=True,
            use_custom_props=True,
            path_mode='ABSOLUTE',  # Use absolute paths to preserve our custom file paths
            embed_textures=embed_textures,
            bake_anim=False,  # No animation needed
            axis_forward='-Z',
            axis_up='Y'
        )
        
        if 'FINISHED' in export_result:
            log(f"FBX export successful!")
            if os.path.exists(output_fbx):
                filesize_kb = os.path.getsize(output_fbx) / 1024
                log(f"Output file size: {filesize_kb:.2f} KB")
                
                # Explicitly close the log file before exiting
                log_file.close()
                
                # Return success
                return True
            else:
                error(f"Export operation completed but file not found: {output_fbx}")
                sys.exit(1)
        else:
            error(f"FBX export failed: {export_result}")
            sys.exit(1)
            
    except Exception as e:
        error(f"ERROR in Blender script: {str(e)}")
        error(traceback.format_exc())
        
        # Make sure log is written
        log_file.flush()
        sys.exit(1)
    finally:
        # Ensure log file is closed
        log_file.close()

# Call the main function if this script is being run directly
if __name__ == "__main__" or "--" in sys.argv:
    main()
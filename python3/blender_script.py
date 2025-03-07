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

log("DEBUG: Blender script is starting!")
log(f"DEBUG: Python version: {sys.version}")
log(f"DEBUG: Arguments: {sys.argv}")
log(f"DEBUG: Working directory: {os.getcwd()}")

# Check for mappings.json file that would override material-texture mappings
PRIORITIZE_MAPPINGS = True  # Set to True to force texture assignments from mappings
mappings_file = os.path.join(os.getcwd(), "mappings.json")
MATERIAL_TEXTURE_MAPPINGS = {}

# Global variable to store model-specific material data
MODEL_MATERIAL_DATA = {}

# Global variables for direct material-texture mappings
DIRECT_MATERIAL_MAPPINGS = {}
BASE_MATERIAL_MAPPINGS = {}
MODEL_TEXTURES_DIR = ""


# Check for model-specific material mapping files
def load_model_specific_mappings(model_name):
    """Load model-specific material mappings from the exports/fbx directory."""
    # Regular material mapping
    mapping_path = os.path.join(os.getcwd(), "exports", "fbx", f"materials_{model_name}.json")
    material_data = {}
    try:
        if os.path.exists(mapping_path):
            log(f"Found model-specific mapping file: {mapping_path}")
            with open(mapping_path, 'r') as f:
                material_data = json.load(f)
            log(f"Loaded material mapping for {model_name} with {len(material_data.get('materials', {}))} materials")
    except Exception as e:
        error(f"Error loading model material mapping: {str(e)}")
    
    # Also check for direct material mapping file (new approach)
    global DIRECT_MATERIAL_MAPPINGS, BASE_MATERIAL_MAPPINGS, MODEL_TEXTURES_DIR
    direct_mapping_path = os.path.join(os.getcwd(), "exports", "fbx", f"direct_materials_{model_name}.json")
    
    try:
        if os.path.exists(direct_mapping_path):
            log(f"Found direct material mapping file: {direct_mapping_path}")
            with open(direct_mapping_path, 'r') as f:
                direct_mapping_data = json.load(f)
            
            # Load direct mappings
            DIRECT_MATERIAL_MAPPINGS = direct_mapping_data.get("direct_mappings", {})
            log(f"Loaded {len(DIRECT_MATERIAL_MAPPINGS)} direct material->texture mappings")
            
            # Load base material mappings
            BASE_MATERIAL_MAPPINGS = direct_mapping_data.get("base_material_mappings", {})
            log(f"Loaded {len(BASE_MATERIAL_MAPPINGS)} base material mappings")
            
            # Get textures directory
            MODEL_TEXTURES_DIR = direct_mapping_data.get("textures_dir", "")
            log(f"Model textures directory: {MODEL_TEXTURES_DIR}")
    except Exception as e:
        error(f"Error loading direct material mapping: {str(e)}")
    
    return material_data

    except Exception as e:
        error(f"Error loading model material mapping: {str(e)}")
    return {}

# Load global mappings first
if os.path.exists(mappings_file):
    try:
        with open(mappings_file, 'r') as f:
            MATERIAL_TEXTURE_MAPPINGS = json.load(f)
        log(f"Loaded {len(MATERIAL_TEXTURE_MAPPINGS)} mappings from mappings.json")
    except Exception as e:
        error(f"Error loading mappings.json: {str(e)}")
else:
    log("No mappings.json file found, using built-in defaults")

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
                        texture_files[name_without_ext] = texture_path    log(f"Found {len(texture_files)} texture files")
        
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
                
            log(f"Found {len(texture_files)} texture files")
    return texture_files

def setup_material(obj, material_name, texture_path, suffix=None):
    """Create material with texture for an object."""
    if not texture_path or not os.path.exists(texture_path):
        error(f"Texture not found: {texture_path}")
        return
    
    # First check if this is a direct 3DB material name
    is_direct_material = False
    if material_data := MODEL_MATERIAL_DATA.get('materials', {}):
        for mat_name in material_data.keys():
            clean_mat_name = mat_name.replace("b'", "").replace("'", "").strip()
            if clean_mat_name == material_name:
                is_direct_material = True
                # Use exact material name without modifications
                actual_material_name = material_name
                log(f"Using direct 3DB material name: {actual_material_name}")
                break
    
    # If not a direct material, create a derived name
    if not is_direct_material:
        if suffix is not None:
            actual_material_name = f"{material_name}_{suffix}"
        else:
            # Just use the material name directly to avoid confusion with texture names
            actual_material_name = material_name
        
        # Limit material name length for Blender
        if len(actual_material_name) > 60:
            actual_material_name = actual_material_name[:60]
    
    # Create new material or get existing one
    if actual_material_name in bpy.data.materials:
        mat = bpy.data.materials[actual_material_name]
        # If this material already has same texture, just reuse it
        if hasattr(mat, 'original_texture') and mat.original_texture == texture_path:
            log(f"Reusing existing material {actual_material_name} with texture {os.path.basename(texture_path)}")
            # Assign material to object
            if len(obj.material_slots) == 0:
                obj.data.materials.append(mat)
            else:
                obj.material_slots[0].material = mat
            return mat
    else:
        mat = bpy.data.materials.new(name=actual_material_name)
    
    # Store the original texture path for reference
    mat.original_texture = texture_path
    
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

def get_texture_for_model_part(anim_name, link_num, material_name, textures):
    """Find the most appropriate texture for a model part based on animation, link, and material."""
    texture_path = None
    
    # Safety check - ensure we have valid inputs
    if not textures:
        log(f"Warning: No textures provided for lookup")
        return None
        
        # Clean material name if it exists
    material_clean = None
    base_material_name = None
    if material_name:
        try:
            if isinstance(material_name, bytes):
                material_clean = material_name.decode('utf-8', errors='ignore').lower()
            else:
                material_clean = str(material_name).lower()
            
            # Remove byte string markers if present
            material_clean = material_clean.replace("b'", "").replace("'", "").strip()
            
            # Extract base material name without numeric suffix (like .001, .002)
            # But preserve numbers that are part of the original material name (e.g., kris_4_burg_a)
            import re
            # Match only numeric suffixes with dots (.001, .002) not numbers in the material name
            base_match = re.match(r'([a-zA-Z0-9_]+(?:_[a-zA-Z0-9_]+)*)(?:\.\d{3,})?$', material_clean)
            if base_match:
                base_material_name = base_match.group(1)
                log(f"Extracted base material name: {base_material_name} from {material_clean}")
        except Exception as e:
            error(f"Error cleaning material name {material_name}: {str(e)}")
            material_clean = None
            base_material_name = None
    
    # DIRECT MAPPING APPROACH - Always try this first if available
    if DIRECT_MATERIAL_MAPPINGS:
        log(f"Using DIRECT MAPPING approach for {material_clean}")
        
        # First try exact match with full material name (including suffix)
        if material_clean and material_clean in DIRECT_MATERIAL_MAPPINGS:
            texture_path = DIRECT_MATERIAL_MAPPINGS[material_clean]
            log(f"DIRECT MAPPING: Found exact match for '{material_clean}' -> {texture_path}")
            return texture_path
            
        # Then try with base material name (without suffix)
        if base_material_name and base_material_name in DIRECT_MATERIAL_MAPPINGS:
            texture_path = DIRECT_MATERIAL_MAPPINGS[base_material_name]
            log(f"DIRECT MAPPING: Found base material match for '{base_material_name}' -> {texture_path}")
            return texture_path
            
        # If material has a suffix, try to look up the base material in BASE_MATERIAL_MAPPINGS
        if base_material_name and base_material_name in BASE_MATERIAL_MAPPINGS and base_material_name != material_clean:
            texture_path = BASE_MATERIAL_MAPPINGS[base_material_name]
            log(f"DIRECT MAPPING: Found base mapping for suffixed material '{material_clean}' using '{base_material_name}' -> {texture_path}")
            return texture_path
            
        log(f"No direct mapping found for material '{material_clean}' or '{base_material_name}'")
        
        # If we have a textures directory path, try to find texture by matching name directly
        if MODEL_TEXTURES_DIR and base_material_name:
            # Try to find texture with same name as material
            possible_texture = os.path.join(MODEL_TEXTURES_DIR, f"{base_material_name}.tga")
            if os.path.exists(possible_texture):
                log(f"DIRECT LOOKUP: Found texture matching material name: {possible_texture}")
                return possible_texture
    # IMPORTANT: First check if we have model-specific material data from mapping file
    if MODEL_MATERIAL_DATA and 'materials' in MODEL_MATERIAL_DATA and (material_clean or base_material_name):
        for mat_name, mat_info in MODEL_MATERIAL_DATA['materials'].items():
            clean_mat_name = mat_name.replace("b'", "").replace("'", "").strip().lower()
            
            # Check for exact material name match (checking both full material name and base name without suffix)
            if clean_mat_name == material_clean or (base_material_name and clean_mat_name == base_material_name):
                if 'texture_name' in mat_info and mat_info['texture_name']:
                    texture_name = mat_info['texture_name']
                    match_type = "exact material match" if clean_mat_name == material_clean else "base material match"
                    log(f"Found {match_type} in mapping: {clean_mat_name} -> {texture_name}")
                    
                    # First try to find the texture directly in FBM directory (preferred)
                    model_name = os.environ.get("MODEL_NAME", "")
                    if model_name:
                        fbm_path = os.path.join(os.getcwd(), "exports", "fbx", f"{model_name}.fbm", texture_name)
                        if os.path.exists(fbm_path):
                            log(f"USING EXACT MAPPING from FBM: {clean_mat_name} -> {fbm_path}")
                            return fbm_path
                    
                    # Then search in textures dict
                    for tex_name, tex_path in textures.items():
                        tex_basename = os.path.basename(tex_path).lower()
                        if texture_name.lower() == tex_basename.lower():
                            log(f"USING EXACT MAPPING: {material_clean} -> {tex_path}")
                            return tex_path
                        elif texture_name.lower() in tex_basename.lower():
                            log(f"USING PARTIAL MAPPING: {material_clean} -> {tex_path}")
                            return tex_path
    
    # First check in mappings if PRIORITIZE_MAPPINGS is enabled
    if PRIORITIZE_MAPPINGS and MATERIAL_TEXTURE_MAPPINGS:
        # Check for direct material name match in mappings
        if material_clean and material_clean in MATERIAL_TEXTURE_MAPPINGS:
            mapped_paths = MATERIAL_TEXTURE_MAPPINGS[material_clean]
            log(f"Found material in global mappings: {material_clean} -> {mapped_paths}")
            
            # Try each path in the mapping
            for mapped_path in mapped_paths:
                if os.path.exists(mapped_path):
                    log(f"Using mapped texture path: {mapped_path}")
                    return mapped_path
                    
        # Check for base material name match (without numeric suffix)
        if base_material_name and base_material_name in MATERIAL_TEXTURE_MAPPINGS:
            mapped_paths = MATERIAL_TEXTURE_MAPPINGS[base_material_name]
            log(f"Found base material in global mappings: {base_material_name} -> {mapped_paths}")
            
            # Try each path in the mapping
            for mapped_path in mapped_paths:
                if os.path.exists(mapped_path):
                    log(f"Using mapped texture path for base material: {mapped_path}")
                    return mapped_path
        
        # Also try partial matches for material name in mappings
        for map_key, map_paths in MATERIAL_TEXTURE_MAPPINGS.items():
            material_to_check = material_clean or base_material_name
            if material_to_check and (map_key in material_to_check or material_to_check in map_key):
                log(f"Found partial material match in global mappings: {map_key} ~ {material_to_check}")
                for path in map_paths:
                    if os.path.exists(path):
                        log(f"Using partial match mapped texture: {path}")
                        return path
    
    # Special handling for link 0 (usually body)
    if link_num == 0:
        # Check for specific model type textures based on material name if available
        if material_clean and ("zbaby" in material_clean or "baby" in material_clean):
            # Baby texture takes priority for baby models
            baby_textures = ["character_zbaby_a"]
            for tex_name, tex_path in textures.items():
                for pattern in baby_textures:
                    if pattern in tex_name.lower():
                        log(f"Using baby texture for link 0: {tex_path}")
                        return tex_path
        
        # Otherwise check common body textures
        body_textures = ["character_zbaby_a", "character_hamster", "troll", "hamster_gross", "koerper", "body"]
        for tex_name, tex_path in textures.items():
            for pattern in body_textures:
                if pattern in tex_name.lower():
                    log(f"Using body texture for link 0: {tex_path}")
                    return tex_path
    
    # Special handling for link 1 (usually hats/accessories)
    elif link_num == 1:
        # For link 1, use the same logic as link 0, but check specifically for head/hat textures
        # if we couldn't find a good match in link 0
        
        # First try model-specific head textures
        model_name = os.environ.get("MODEL_NAME", "").lower()
        head_keywords = ["kopf", "head", "hat", "hut", "helmet", "muetze", "schatzbuch"]
        
        # Look for textures matching both model name and head keywords
        model_head_textures = []
        for tex_name, tex_path in textures.items():
            tex_name_lower = tex_name.lower()
            if model_name in tex_name_lower and any(keyword in tex_name_lower for keyword in head_keywords):
                resolution = "m256" if "m256" in tex_path else \
                            "m128" if "m128" in tex_path else \
                            "m064" if "m064" in tex_path else "other"
                model_head_textures.append((resolution, tex_path))
        
        # Sort by resolution and use best quality if found
        if model_head_textures:
            model_head_textures.sort(key=lambda x: {"m256": 0, "m128": 1, "m064": 2, "other": 3}[x[0]])
            best_tex_path = model_head_textures[0][1]
            log(f"Using model-specific head texture: {best_tex_path}")
            return best_tex_path
        
        # If not found, fall back to the primary model texture
        for tex_name, tex_path in textures.items():
            # Model name in texture is a good indicator
            if model_name in tex_name.lower():
                log(f"Using model primary texture for head: {tex_path}")
                return tex_path    # *** IMPROVED MATERIAL-TEXTURE MATCHING ***
    # First check if we have model-specific material data
    if MODEL_MATERIAL_DATA and 'materials' in MODEL_MATERIAL_DATA and (material_clean or base_material_name):
        for mat_name, mat_info in MODEL_MATERIAL_DATA['materials'].items():
            clean_mat_name = mat_name.replace("b'", "").replace("'", "").strip().lower()
            
            # Check for exact material name match or base name match
            if (clean_mat_name == material_clean or (base_material_name and clean_mat_name == base_material_name)) and 'texture_name' in mat_info:
                texture_name = mat_info['texture_name']
                match_type = "exact material match" if clean_mat_name == material_clean else "base material match"
                log(f"Found {match_type} in mapping (second pass): {clean_mat_name} -> {texture_name}")
                
                # First check FBM directory directly (preferred)
                model_name = os.environ.get("MODEL_NAME", "")
                if model_name:
                    fbm_path = os.path.join(os.getcwd(), "exports", "fbx", f"{model_name}.fbm", texture_name)
                    if os.path.exists(fbm_path):
                        log(f"USING EXACT MAPPING from FBM (second pass): {clean_mat_name} -> {fbm_path}")
                        return fbm_path
                
                # Then search for this texture in the textures dict
                for tex_name, tex_path in textures.items():
                    if texture_name.lower() in tex_name.lower():
                        log(f"Using exact material-texture mapping: {clean_mat_name} -> {tex_path}")
                        return tex_path

    # If no specific category match, try to match by material name
    material_to_try = material_clean or base_material_name
    if material_to_try:
        for tex_name, tex_path in textures.items():
            tex_basename = os.path.basename(tex_path).lower()
            
            # Try exact match first
            if material_to_try == tex_basename or material_to_try == os.path.splitext(tex_basename)[0]:
                log(f"Using texture with EXACT material name match: {material_to_try} -> {tex_path}")
                return tex_path
            
            # Then try substring match with MUCH stricter criteria 
            # to prevent kris_4_burg_a matching kristall_details_a
            material_base = material_to_try
            texture_base = os.path.splitext(tex_basename)[0]
            
            # Calculate minimum required matching characters (80% of the shorter string)
            min_length = min(len(material_base), len(texture_base))
            required_matching_chars = int(min_length * 0.8)
            
            # Only consider matches if they meet the minimum matching requirement
            if min_length >= 5 and required_matching_chars >= 4:
                # Check if there is a strong prefix match
                if material_base.startswith(texture_base) and len(texture_base) >= required_matching_chars:
                    log(f"Using texture with STRONG prefix match ({material_base}/{texture_base}): {material_to_try} -> {tex_path}")
                    return tex_path
                
                # Or texture starts with material name
                if texture_base.startswith(material_base) and len(material_base) >= required_matching_chars:
                    log(f"Using texture with STRONG prefix match ({texture_base}/{material_base}): {material_to_try} -> {tex_path}")
                    return tex_path
    
    # If no match yet, try animation-specific matches
    if anim_name:
        try:
            # Ensure anim_name is a string
            if isinstance(anim_name, bytes):
                anim_name = anim_name.decode('utf-8', errors='ignore')
            
            anim_clean = str(anim_name).lower()
            # Special animation-specific textures
            if "sterben" in anim_clean or "getroffen" in anim_clean or "tot" in anim_clean:
                # Wounded/death animations
                wounded_textures = ["wounded", "damage", "getroffen", "tot"]
                for tex_name, tex_path in textures.items():
                    for pattern in wounded_textures:
                        if pattern in tex_name.lower():
                            log(f"Using wounded texture for animation {anim_name}: {tex_path}")
                            return tex_path
        except Exception as e:
            error(f"Error processing animation name {anim_name}: {str(e)}")
    
    # Try model name-based matching for generic parts
    model_name = None
    if 'MODEL_NAME' in os.environ:
        model_name = os.environ['MODEL_NAME'].lower()
    elif anim_name:
        # Use first part of animation name as fallback model name
        try:
            model_parts = str(anim_name).split('_')
            if model_parts and len(model_parts[0]) > 1:
                model_name = model_parts[0].lower()
        except:
            pass
    
    if model_name:
        # Search for textures matching the model name
        log(f"Trying to match by model name: {model_name}")
        for tex_name, tex_path in textures.items():
            if model_name in tex_name.lower():
                log(f"Found texture matching model name {model_name}: {tex_path}")
                return tex_path
    
    # If still no match, use any available texture as fallback
    for pattern in ["character", "texture", "material"]:
        for tex_name, tex_path in textures.items():
            if pattern in tex_name.lower():
                log(f"Using fallback texture with {pattern}: {tex_path}")
                return tex_path
    
    # Last resort - return first texture if available
    if textures:
        first_texture = list(textures.values())[0]
        log(f"Using first available texture as last resort: {first_texture}")
        return first_texture
    
    # No texture found
    log(f"No suitable texture found for {anim_name}, link {link_num}, material {material_name}")
    return None

def extract_model_info(obj_name):
    """Extract material info and other details from object name."""
    # Normalize object name to string if it's bytes
    if isinstance(obj_name, bytes):
        try:
            obj_name = obj_name.decode('utf-8', errors='ignore')
        except:
            obj_name = str(obj_name)
    
    obj_name_str = str(obj_name)
    
    # Check if this is a direct material object name (from the 3DB file)
    if '.' in obj_name_str: 
        # Blender often adds .001, .002, etc. to object names to make them unique
        # Let's remove that suffix
        # Preserve indices in material names like 'kris_4_burg_a.022'
        # Only remove true Blender suffixes like .001, .002
        if '.' in obj_name_str and obj_name_str.split('.')[-1].isdigit() and len(obj_name_str.split('.')[-1]) == 3:
            base_name = obj_name_str.rsplit('.', 1)[0]
        else:
            base_name = obj_name_str
    else:
        base_name = obj_name_str
    
    # Check if the name is a material name from our mapping file
    material_data = MODEL_MATERIAL_DATA
    if material_data and 'materials' in material_data:
        # Search all material names
        for mat_name, mat_info in material_data['materials'].items():
            # Clean up material name for comparison
            clean_mat_name = mat_name.replace("b'", "").replace("'", "").strip()
            
            # Check if the object name matches a material name
            if clean_mat_name == base_name:
                log(f"Found direct material name match: {clean_mat_name}, index={mat_info['index']}")
                return "default", 0, 0, mat_info['index'], clean_mat_name
    
    # Old format check - material_ prefix
    if obj_name_str.startswith("material_"):
        try:
            # Format is "material_XX_MaterialName" where XX is the index
            parts = obj_name_str.split("_", 2)  # Split into [material, XX, MaterialName]
            if len(parts) >= 3:
                material_index = int(parts[1])
                material_name = parts[2]
                log(f"Found material-based name: index={material_index}, name={material_name}")
                
                # For compatibility with the rest of the code, return defaults for anim/frame/link
                # but include the material info
                return "default", 0, 0, material_index, material_name
        except Exception as e:
            error(f"Error parsing material name from {obj_name_str}: {str(e)}")
    
    # Common regex patterns for legacy naming formats
    # IMPORTANT: The order of patterns matters - more specific patterns first
    patterns = [
        # Handle material index in name
        r"b'([^']+)'_frame(\d+)_link(\d+)_mat_(\d+)",  # with material
        r"([^_]+(?:_[^_]+)*)_frame(\d+)_link(\d+)_mat_(\d+)",  # with material
        
        # Handle byte string prefixes with full animation name preservation
        r"b'([^']+)'_frame(\d+)_link(\d+)",      # b'full_anim_name'_frame01_link00
        
        # Standard patterns with good animation name preservation
        r"([^_]+(?:_[^_]+)*)_frame(\d+)_link(\d+)",  # full_anim_name_frame01_link00
        r"([^_]+(?:_[^_]+)*)_frame_(\d+)_link_(\d+)",  # full_anim_name_frame_01_link_00
        
        # Alternative formats
        r"(.+)_frame(\d+)_part(\d+)",            # anim_name_frame01_part00
        
        # More flexible pattern as fallback
        r"(.*?)_?frame_?(\d+)_?(?:link|part)_?(\d+)"  # any_pattern_frame_00_link_00
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
                
                # Convert frame and link to integers
                try:
                    frame_num = int(match.group(2))
                    link_num = int(match.group(3))
                    
                    # Check if we have material index in the pattern (only first two patterns)
                    material_index = -1
                    if "_mat_" in pattern:
                        try:
                            material_index = int(match.group(4))
                            log(f"Extracted animation: '{anim_name}', frame: {frame_num}, link: {link_num}, material: {material_index} from {obj_name}")
                            return anim_name, frame_num, link_num, material_index, None
                        except (ValueError, TypeError, IndexError) as e:
                            error(f"Error parsing material index from {obj_name}: {str(e)}")
                    
                    log(f"Extracted animation: '{anim_name}', frame: {frame_num}, link: {link_num} from {obj_name}")
                    return anim_name, frame_num, link_num, -1, None  # No material index
                except (ValueError, TypeError) as e:
                    error(f"Error parsing frame/link numbers from {obj_name}: {str(e)}")
        except Exception as e:
            error(f"Error processing pattern {pattern} on {obj_name_str}: {str(e)}")
            continue
                
    # No match found - log this for debugging
    log(f"Failed to extract model info from object name: {obj_name}")
    return None, None, None, None, None

def process_gltf_structure(gltf_path, model_name=None):
    """Organize imported GLTF into proper hierarchy."""
    # Extract material mappings from GLTF to use for naming
    material_indices = extract_material_indices_from_gltf(gltf_path)
    log(f"Found {len(material_indices)} material indices to use for naming")
    
    # Import model-specific material mapping if available
    model_material_data = {}
    if model_name:
        model_material_data = load_model_specific_mappings(model_name)
        if model_material_data and 'materials' in model_material_data:
            log(f"Loaded {len(model_material_data['materials'])} materials from mapping file for {model_name}")
    
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
            
    # Store material information for later use
    # We'll add material indices to object custom properties
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and '_link' in obj.name:
            # Extract material index from our mapping if available
            if obj.name in material_indices:
                material_info = material_indices[obj.name]
                obj['material_index'] = material_info['material']
                log(f"Set material index {material_info['material']} for {obj.name}")
            elif model_material_data and 'materials' in model_material_data:
                # Try to find material index by looking at link position
                try:
                    link_parts = obj.name.split('_link')
                    link_num = int(link_parts[1].split('_')[0])
                    
                    # Check each material in mapping to see which ones use this link position
                    for mat_name, mat_info in model_material_data['materials'].items():
                        if 'links' in mat_info and link_num in mat_info['links']:
                            obj['material_index'] = mat_info['index']
                            log(f"Set material index {mat_info['index']} for {obj.name} based on link position {link_num}")
                            break
                except Exception as e:
                    log(f"Error finding material for {obj.name}: {e}")
    
    # If no model name provided, get from filename
    if not model_name:
        model_name = os.path.splitext(os.path.basename(gltf_path))[0]
        log(f"Using model name from filename: {model_name}")
        
    # Create root object
    root = bpy.data.objects.new(model_name, None)
    bpy.context.scene.collection.objects.link(root)
    
    # Find textures
    textures = find_texture_files()
    
    # Extract animation, frame, and link information from object names
    animations = {}
    
    # Track imported objects that don't match naming pattern


# ======================================================
# Material to texture mappings
# Auto-generated by generate_mappings.py
# ======================================================
MATERIAL_TEXTURE_MAPPINGS = {
    "brainposter": [
        "assets/textures/m256/brainposter.tga",
    ],
    "bunte_waende_a": [
        "assets/textures/m256/bunte_waende_a.tga",
    ],
    "character_drache_b_256": [
        "assets/textures/m256/Character_Drache_b_256.tga",
        "assets/textures/Gray/Character_Drache_b_256.tga",
    ],
    "character_fenris_koerper_a": [
        "assets/textures/m256/Character_Fenris_Koerper_a.tga",
    ],
    "character_fenris_kopf_a": [
        "assets/textures/m256/Character_Fenris_Kopf_a.tga",
    ],
    "character_fenris_rest": [
        "assets/textures/m256/Character_Fenris_rest.tga",
    ],
    "character_hamster_a_128": [
        "assets/textures/m128/Character_Hamster_a_128.tga",
    ],
    "character_hamster_gross": [
        "assets/textures/m256/Character_Hamster_gross.tga",
        "assets/textures/Gray/Character_Hamster_gross.tga",
    ],
    "character_odin_a": [
        "assets/textures/m256/Character_Odin_a.tga",
    ],
    "character_raupe_a_128": [
        "assets/textures/m128/Character_Raupe_a_128.tga",
    ],
    "character_troll_kopf_a_256": [
        "assets/textures/m256/Character_Troll_Kopf_a_256.tga",
    ],
    "character_troll_kopf_b": [
        "assets/textures/m256/Character_Troll_Kopf_b.tga",
    ],
    "character_troll_kopf_c": [
        "assets/textures/m256/Character_Troll_Kopf_c.tga",
    ],
    "character_troll_kopf_d": [
        "assets/textures/m256/Character_Troll_Kopf_d.tga",
    ],
    "character_troll_kopf_e": [
        "assets/textures/m256/Character_Troll_Kopf_e.tga",
    ],
    "character_troll_kopf_f": [
        "assets/textures/m256/Character_Troll_Kopf_f.tga",
    ],
    "character_zbaby_a": [
        "assets/textures/m128/Character_ZBaby_a.tga",
    ],
    "character_zmann_koerper_a_256": [
        "assets/textures/m064/Character_ZMann_Koerper_a_256.tga",
    ],
    "checker": [
        "assets/textures/m032/Checker.tga",
    ],
    "cw_counter1_face": [
        "assets/textures/m128/CW_counter1_face.tga",
    ],
    "cw_counter1_haare": [
        "assets/textures/m128/CW_counter1_haare.tga",
    ],
    "cw_counter1_oben": [
        "assets/textures/m128/CW_counter1_oben.tga",
    ],
    "cw_counter1_unten": [
        "assets/textures/m128/CW_counter1_unten.tga",
    ],
    "cw_waffen": [
        "assets/textures/m128/CW_waffen.tga",
    ],
    "elfen_koerper": [
        "assets/textures/m256/Elfen_Koerper.tga",
    ],
    "elfen_kopf": [
        "assets/textures/m128/Elfen_Kopf.tga",
    ],
    "endgame_a": [
        "assets/textures/m256/endgame_a.tga",
    ],
    "endgame_b": [
        "assets/textures/m256/endgame_b.tga",
    ],
    "endgame_c": [
        "assets/textures/m256/endgame_c.tga",
    ],
    "enviro_chrome": [
        "assets/textures/m064/enviro_chrome.tga",
    ],
    "enviro_glas": [
        "assets/textures/m064/enviro_glas.tga",
    ],
    "enviro_gold": [
        "assets/textures/m064/enviro_gold.tga",
    ],
    "enviro_green": [
        "assets/textures/m064/enviro_green.tga",
    ],
    "enviro_lava": [
        "assets/textures/m064/enviro_lava.tga",
    ],
    "enviro_rot": [
        "assets/textures/m064/enviro_rot.tga",
    ],
    "enviro_rot_2": [
        "assets/textures/m064/enviro_rot_2.tga",
    ],
    "enviro_wasser": [
        "assets/textures/m064/enviro_wasser.tga",
    ],
    "enviro_wohn_a_noalpha": [
        "assets/textures/m064/enviro_wohn_a_noalpha.tga",
    ],
    "enviro_wohn_b_noalpha": [
        "assets/textures/m064/enviro_wohn_b_noalpha.tga",
    ],
    "enviro_wohn_blau": [
        "assets/textures/m064/enviro_wohn_blau.tga",
    ],
    "enviro_wohn_blau_2": [
        "assets/textures/m064/enviro_wohn_blau_2.tga",
    ],
    "enviro_wohn_e": [
        "assets/textures/m064/enviro_wohn_e.tga",
    ],
    "enviro_wohn_f": [
        "assets/textures/m064/enviro_wohn_f.tga",
    ],
    "enviro_wohn_gruen": [
        "assets/textures/m064/enviro_wohn_gruen.tga",
    ],
    "enviro_wohn_gruen_2": [
        "assets/textures/m064/enviro_wohn_gruen_2.tga",
    ],
    "fahne_blau": [
        "assets/textures/m064/fahne_blau.tga",
    ],
    "fahne_gruen": [
        "assets/textures/m064/fahne_gruen.tga",
    ],
    "fahne_mp_blue": [
        "assets/textures/m064/fahne_mp_blue.tga",
    ],
    "fahne_rot": [
        "assets/textures/m064/fahne_rot.tga",
    ],
    "fahne_schwarz": [
        "assets/textures/m064/fahne_schwarz.tga",
    ],
    "fahne_weiss": [
        "assets/textures/m064/fahne_weiss.tga",
    ],
    "feenfluegel?0003": [
        "assets/textures/m128/feenfluegel.tga",
    ],
    "feenfluegel?0004": [
        "assets/textures/m128/feenfluegel.tga",
    ],
    "feenfluegel?0005": [
        "assets/textures/m128/feenfluegel.tga",
    ],
    "feenfluegel?0006": [
        "assets/textures/m128/feenfluegel.tga",
    ],
    "fenbrut_gruen": [
        "assets/textures/m128/fenbrut_gruen.tga",
    ],
    "fenbrut_rot": [
        "assets/textures/m128/fenbrut_rot.tga",
    ],
    "fifi03": [
        "assets/textures/m128/Fifi03.tga",
    ],
    "fx_licht": [
        "assets/textures/Misc/FX_Licht.tga",
    ],
    "fx_licht_b": [
        "assets/textures/Misc/FX_Licht_b.tga",
    ],
    "fx_licht_c": [
        "assets/textures/Misc/FX_Licht_c.tga",
    ],
    "gargoyle": [
        "assets/textures/m256/gargoyle.tga",
    ],
    "gelbneb_4_metall": [
        "assets/textures/m256/gelbneb_4_metall.tga",
    ],
    "gelbneb_4_metall_a": [
        "assets/textures/m256/gelbneb_4_metall_a.tga",
    ],
    "gelbneb_4_metall_b": [
        "assets/textures/m256/gelbneb_4_metall_b.tga",
    ],
    "gelbneb_4_metall_c": [
        "assets/textures/m256/gelbneb_4_metall_c.tga",
    ],
    "gelbneb_hydrant_a": [
        "assets/textures/m256/gelbneb_Hydrant_a.tga",
    ],
    "gelbneb_lampen": [
        "assets/textures/m256/gelbneb_lampen.tga",
    ],
    "gelbneb_maschdet_b": [
        "assets/textures/m256/gelbneb_maschdet_b.tga",
    ],
    "gelbneb_maschdet_d": [
        "assets/textures/m256/gelbneb_maschdet_d.tga",
    ],
    "gelbneb_maschdet_e": [
        "assets/textures/m256/gelbneb_maschdet_e.tga",
    ],
    "gelbneb_rohre_b": [
        "assets/textures/m256/gelbneb_Rohre_b.tga",
    ],
    "gelbneb_rohre_c": [
        "assets/textures/m256/gelbneb_Rohre_c.tga",
    ],
    "gelbneb_saeule1": [
        "assets/textures/m256/gelbneb_saeule1.tga",
    ],
    "gelbneb_saeule_c": [
        "assets/textures/m256/gelbneb_saeule_c.tga",
    ],
    "gelbneb_saeuleb_2": [
        "assets/textures/m256/gelbneb_saeuleb_2.tga",
    ],
    "gelbneb_schw_boden": [
        "assets/textures/m256/gelbneb_schw_boden.tga",
    ],
    "gelbneb_schw_boden2": [
        "assets/textures/m256/gelbneb_schw_boden2.tga",
    ],
    "gelbneb_schw_details": [
        "assets/textures/m256/gelbneb_schw_details.tga",
    ],
    "gelbneb_schw_details2": [
        "assets/textures/m256/gelbneb_schw_details2.tga",
    ],
    "gelbneb_schw_produktion": [
        "assets/textures/m256/gelbneb_schw_produktion.tga",
    ],
    "gelbneb_schwef_saeulen": [
        "assets/textures/m256/gelbneb_schwef_saeulen.tga",
    ],
    "gras_nahtlos": [
        "assets/textures/m128/gras_nahtlos.tga",
    ],
    "helme_huete_a": [
        "assets/textures/m256/helme_huete_a.tga",
    ],
    "holz_deherei_a": [
        "assets/textures/m256/Holz_Deherei_a.tga",
    ],
    "holz_dojo_a": [
        "assets/textures/m256/Holz_Dojo_a.tga",
    ],
    "holz_klotz_a_128": [
        "assets/textures/m128/Holz_Klotz_a_128.tga",
    ],
    "holz_moebeltischler_a": [
        "assets/textures/m256/Holz_Moebeltischler_a.tga",
    ],
    "holz_standard_a_256": [
        "assets/textures/m256/Holz_Standard_a_256.tga",
    ],
    "holz_standard_b_256": [
        "assets/textures/m256/Holz_Standard_b_256.tga",
    ],
    "holz_standard_c_256": [
        "assets/textures/m256/Holz_Standard_c_256.tga",
    ],
    "holz_standard_d_256": [
        "assets/textures/m256/Holz_Standard_d_256.tga",
    ],
    "holz_standard_e_256": [
        "assets/textures/m256/Holz_Standard_e_256.tga",
    ],
    "holz_standard_f_256": [
        "assets/textures/m256/Holz_Standard_f_256.tga",
    ],
    "interface01": [
        "assets/textures/m256/Interface01.tga",
    ],
    "kr_background_a": [
        "assets/textures/m128/kr_background_a.tga",
    ],
    "kr_background_b": [
        "assets/textures/m128/kr_background_b.tga",
    ],
    "kr_enviroment_a": [
        "assets/textures/m064/kr_enviroment_a.tga",
    ],
    "kr_enviroment_a_noalpha": [
        "assets/textures/m064/kr_enviroment_a_noalpha.tga",
    ],
    "kr_enviroment_b": [
        "assets/textures/m064/kr_enviroment_b.tga",
    ],
    "kr_enviroment_b_noalpha": [
        "assets/textures/m064/kr_enviroment_b_noalpha.tga",
    ],
    "kr_enviroment_c": [
        "assets/textures/m064/kr_enviroment_c.tga",
    ],
    "kr_enviroment_c_noalpha": [
        "assets/textures/m064/kr_enviroment_c_noalpha.tga",
    ],
    "kr_enviroment_d": [
        "assets/textures/m064/kr_enviroment_d.tga",
    ],
    "kr_enviroment_e": [
        "assets/textures/m064/kr_enviroment_e.tga",
    ],
    "kr_enviroment_f": [
        "assets/textures/m064/kr_enviroment_f.tga",
    ],
    "kr_enviroment_g": [
        "assets/textures/m064/kr_enviroment_g.tga",
    ],
    "kr_enviroment_h": [
        "assets/textures/m064/kr_enviroment_h.tga",
    ],
    "krake01": [
        "assets/textures/m256/Krake01.tga",
    ],
    "kreide_alpha": [
        "assets/textures/m064/kreide_alpha.tga",
    ],
    "kris_4_brain_a": [
        "assets/textures/m256/kris_4_brain_a.tga",
    ],
    "kris_4_burg_a": [
        "assets/textures/m256/kris_4_burg_a.tga",
    ],
    "kris_4_burg_b": [
        "assets/textures/m256/kris_4_burg_b.tga",
    ],
    "kris_4_burg_bc": [
        "assets/textures/m256/kris_4_burg_bc.tga",
    ],
    "kris_eis": [
        "assets/textures/m128/kris_eis.tga",
    ],
    "kristall_details_a": [
        "assets/textures/m256/kristall_details_a.tga",
    ],
    "kristall_details_b": [
        "assets/textures/m256/kristall_details_b.tga",
    ],
    "kristall_gallerie": [
        "assets/textures/m256/kristall_gallerie.tga",
    ],
    "lava_4_vamp_a": [
        "assets/textures/m256/lava_4_vamp_a.tga",
    ],
    "lava_4_vamp_b": [
        "assets/textures/m256/lava_4_vamp_b.tga",
    ],
    "lava_4_vamp_c": [
        "assets/textures/m256/lava_4_vamp_c.tga",
    ],
    "lava_4_vamp_d": [
        "assets/textures/m256/lava_4_vamp_d.tga",
    ],
    "lava_becken_a": [
        "assets/textures/m256/lava_becken_a.tga",
    ],
    "lava_boden_a": [
        "assets/textures/m256/lava_boden_a.tga",
    ],
    "lava_fenrish_a": [
        "assets/textures/m256/lava_fenrish_a.tga",
    ],
    "lava_moos_a": [
        "assets/textures/m256/lava_moos_a.tga",
    ],
    "lava_moos_b": [
        "assets/textures/m256/lava_moos_b.tga",
    ],
    "lava_nahtlos": [
        "assets/textures/m128/lava_nahtlos.tga",
    ],
    "lava_pfeiler": [
        "assets/textures/m256/lava_pfeiler.tga",
    ],
    "lava_rinne_a": [
        "assets/textures/m256/lava_rinne_a.tga",
    ],
    "lava_rinne_b": [
        "assets/textures/m256/lava_rinne_b.tga",
    ],
    "lava_seulen_128": [
        "assets/textures/m128/lava_seulen_128.tga",
    ],
    "lava_seulen_128_noalpha": [
        "assets/textures/m128/lava_seulen_128_noalpha.tga",
    ],
    "lava_vamp_a": [
        "assets/textures/m256/lava_vamp_a.tga",
    ],
    "leiter_holz": [
        "assets/textures/m064/leiter_holz.tga",
    ],
    "lorenbahn_a": [
        "assets/textures/m256/lorenbahn_a.tga",
    ],
    "lorenbahn_b": [
        "assets/textures/m256/lorenbahn_b.tga",
    ],
    "lorenbahn_c": [
        "assets/textures/m256/lorenbahn_c.tga",
    ],
    "metall_amboss_a_128": [
        "assets/textures/m128/Metall_Amboss_a_128.tga",
    ],
    "metall_bordell_a": [
        "assets/textures/m256/Metall_bordell_a.tga",
    ],
    "metall_dampfaufzug_a_128": [
        "assets/textures/m128/Metall_Dampfaufzug_a_128.tga",
    ],
    "metall_dampflore_a_256": [
        "assets/textures/m256/Metall_Dampflore_a_256.tga",
    ],
    "metall_destilierapp_a_256": [
        "assets/textures/m256/Metall_Destilierapp_a_256.tga",
    ],
    "metall_disco_a": [
        "assets/textures/m256/Metall_Disco_a.tga",
    ],
    "metall_disco_b": [
        "assets/textures/m256/Metall_Disco_b.tga",
    ],
    "metall_gym_bude_a": [
        "assets/textures/m256/Metall_gym_bude_a.tga",
    ],
    "metall_hofen_dhammer_a_256": [
        "assets/textures/m256/Metall_Hofen_Dhammer_a_256.tga",
    ],
    "metall_krankenhaus_a": [
        "assets/textures/m256/Metall_Krankenhaus_a.tga",
    ],
    "metall_kristallmasch": [
        "assets/textures/m256/metall_kristallmasch.tga",
    ],
    "metall_kschmiede_a": [
        "assets/textures/m256/Metall_Kschmiede_a.tga",
    ],
    "metall_kschmiede_b": [
        "assets/textures/m256/Metall_Kschmiede_b.tga",
    ],
    "metall_labor_a": [
        "assets/textures/m256/Metall_labor_a.tga",
    ],
    "metall_moebel_a_256": [
        "assets/textures/m256/Metall_Moebel_a_256.tga",
    ],
    "metall_op_a_256": [
        "assets/textures/m256/Metall_Op_a_256.tga",
    ],
    "metall_opferaltar_a_256": [
        "assets/textures/m256/Metall_Opferaltar_a_256.tga",
    ],
    "metall_schilde_a_128": [
        "assets/textures/m128/Metall_Schilde_a_128.tga",
    ],
    "metall_schleifm_a": [
        "assets/textures/m256/Metall_Schleifm_a.tga",
    ],
    "metall_schleifm_a_256": [
        "assets/textures/m256/Metall_Schleifm_a_256.tga",
    ],
    "metall_standard_a_256": [
        "assets/textures/m256/Metall_Standard_a_256.tga",
    ],
    "metall_standard_b_256": [
        "assets/textures/m256/Metall_Standard_b_256.tga",
    ],
    "metall_standard_c_256": [
        "assets/textures/m256/Metall_Standard_c_256.tga",
    ],
    "metall_standard_d": [
        "assets/textures/m256/metall_standard_d.tga",
    ],
    "metall_waffenfabrik_a": [
        "assets/textures/m256/Metall_Waffenfabrik_a.tga",
    ],
    "metall_waffenschmiede_a": [
        "assets/textures/m256/Metall_Waffenschmiede_a.tga",
    ],
    "metall_wellblech_a": [
        "assets/textures/m256/Metall_Wellblech_a.tga",
    ],
    "metall_wellblech_b": [
        "assets/textures/m256/Metall_Wellblech_b.tga",
    ],
    "metall_werkzeuge_a_128": [
        "assets/textures/m128/Metall_Werkzeuge_a_128.tga",
    ],
    "metall_werkzeuge_b_128": [
        "assets/textures/m128/Metall_Werkzeuge_b_128.tga",
    ],
    "oberw_burg_a": [
        "assets/textures/m128/Oberw_burg_a.tga",
    ],
    "oberw_details_a": [
        "assets/textures/m256/Oberw_details_a.tga",
    ],
    "oberwelt_baum_b": [
        "assets/textures/m256/Oberwelt_Baum_b.tga",
    ],
    "oberwelt_baum_d": [
        "assets/textures/m256/Oberwelt_Baum_d.tga",
    ],
    "obw_4_boden_a": [
        "assets/textures/m256/obw_4_boden_a.tga",
    ],
    "obw_4_boden_b": [
        "assets/textures/m256/obw_4_boden_b.tga",
    ],
    "obw_4_boden_c": [
        "assets/textures/m256/obw_4_boden_c.tga",
    ],
    "obw_berg_a": [
        "assets/textures/m128/obw_berg_a.tga",
    ],
    "obw_berg_b": [
        "assets/textures/m128/obw_berg_b.tga",
    ],
    "obw_berg_c": [
        "assets/textures/m128/obw_berg_c.tga",
    ],
    "obw_berg_d": [
        "assets/textures/m128/obw_berg_d.tga",
    ],
    "obw_berg_e": [
        "assets/textures/m128/obw_berg_e.tga",
    ],
    "obw_berg_f": [
        "assets/textures/m128/obw_berg_f.tga",
    ],
    "obw_wegweiser": [
        "assets/textures/m256/obw_wegweiser.tga",
    ],
    "riesenelfe_koerper?0000": [
        "assets/textures/m256/Riesenelfe_Koerper.tga",
    ],
    "riesenelfen_kopf?0001": [
        "assets/textures/m256/Riesenelfen_Kopf.tga",
    ],
    "riesenelfen_kopf?0002": [
        "assets/textures/m256/Riesenelfen_Kopf.tga",
    ],
    "schatz_a_256": [
        "assets/textures/m256/Schatz_a_256.tga",
    ],
    "schwef_nahtlos": [
        "assets/textures/m128/schwef_nahtlos.tga",
    ],
    "schwef_waende": [
        "assets/textures/m128/schwef_waende.tga",
    ],
    "spielkarten_128": [
        "assets/textures/m128/spielkarten_128.tga",
    ],
    "spinnweben_a": [
        "assets/textures/m256/Spinnweben_a.tga",
    ],
    "spinnweben_b": [
        "assets/textures/m256/Spinnweben_b.tga",
    ],
    "stein_bowlingbahn_a": [
        "assets/textures/m256/Stein_bowlingbahn_a.tga",
    ],
    "stein_glas_a": [
        "assets/textures/m256/Stein_glas_a.tga",
    ],
    "stein_glas_b": [
        "assets/textures/m256/Stein_glas_b.tga",
    ],
    "stein_glas_c": [
        "assets/textures/m256/Stein_glas_c.tga",
    ],
    "stein_kristallreaktor_a": [
        "assets/textures/m256/Stein_kristallreaktor_a.tga",
    ],
    "stein_medusa_a_128": [
        "assets/textures/m128/Stein_Medusa_a_128.tga",
    ],
    "stein_sand_a": [
        "assets/textures/m256/Stein_Sand_a.tga",
    ],
    "stein_standard_a_256": [
        "assets/textures/m256/Stein_Standard_a_256.tga",
    ],
    "stein_standard_b_256": [
        "assets/textures/m256/Stein_Standard_b_256.tga",
    ],
    "stein_standard_c_256": [
        "assets/textures/m256/Stein_Standard_c_256.tga",
    ],
    "stein_standard_d": [
        "assets/textures/m256/Stein_Standard_d.tga",
    ],
    "struktur_bettzeug_a_256": [
        "assets/textures/m256/Struktur_Bettzeug_a_256.tga",
    ],
    "struktur_buehne_a_256": [
        "assets/textures/m256/Struktur_Buehne_a_256.tga",
    ],
    "struktur_buehne_b": [
        "assets/textures/m256/Struktur_Buehne_b.tga",
    ],
    "struktur_leder_a_256": [
        "assets/textures/m256/Struktur_Leder_a_256.tga",
    ],
    "struktur_moebel_a_256": [
        "assets/textures/m256/Struktur_Moebel_a_256.tga",
    ],
    "struktur_moebel_b_256": [
        "assets/textures/m256/Struktur_Moebel_b_256.tga",
    ],
    "struktur_moebel_c_256": [
        "assets/textures/m256/Struktur_Moebel_c_256.tga",
    ],
    "struktur_plakate_a": [
        "assets/textures/m256/Struktur_Plakate_a.tga",
    ],
    "struktur_rohstoffe_a_256": [
        "assets/textures/m256/Struktur_Rohstoffe_a_256.tga",
    ],
    "struktur_rohstoffe_c_256": [
        "assets/textures/m256/Struktur_Rohstoffe_c_256.tga",
    ],
    "strukur_hbett_a_256": [
        "assets/textures/m256/Strukur_Hbett_a_256.tga",
    ],
    "sumpfwasser": [
        "assets/textures/m128/sumpfwasser.tga",
    ],
    "titanic_4_holz": [
        "assets/textures/m256/titanic_4_holz.tga",
    ],
    "titanic_4_holz_a": [
        "assets/textures/m256/titanic_4_holz_a.tga",
    ],
    "titanic_4_metall_a": [
        "assets/textures/m256/titanic_4_metall_a.tga",
    ],
    "titanic_4_metall_b": [
        "assets/textures/m256/titanic_4_metall_b.tga",
    ],
    "titanic_4_metall_c": [
        "assets/textures/m256/titanic_4_metall_c.tga",
    ],
    "titanic_details_b": [
        "assets/textures/m256/titanic_details_b.tga",
    ],
    "titanic_kopf_a": [
        "assets/textures/m256/titanic_kopf_a.tga",
    ],
    "titanic_kopf_b": [
        "assets/textures/m256/titanic_kopf_b.tga",
    ],
    "titanic_kron_a": [
        "assets/textures/m256/titanic_kron_a.tga",
    ],
    "troll001": [
        "assets/textures/m256/Troll001.tga",
    ],
    "troll_kopf001": [
        "assets/textures/m256/Troll_Kopf001.tga",
    ],
    "trollh_4_boden_a": [
        "assets/textures/m256/trollh_4_boden_a.tga",
    ],
    "trollh_4_wand_a": [
        "assets/textures/m256/trollh_4_wand_a.tga",
    ],
    "trollh_4_wand_b": [
        "assets/textures/m256/trollh_4_wand_b.tga",
    ],
    "trollh_4_wand_c": [
        "assets/textures/m256/trollh_4_wand_c.tga",
    ],
    "trollh_4_wand_d": [
        "assets/textures/m256/trollh_4_wand_d.tga",
    ],
    "trollh_4_wand_e": [
        "assets/textures/m256/trollh_4_wand_e.tga",
    ],
    "trollh_boden_b_256": [
        "assets/textures/m256/Trollh_Boden_b_256.tga",
    ],
    "trollh_boden_b_end_256": [
        "assets/textures/m256/Trollh_Boden_b_End_256.tga",
    ],
    "trollh_boden_b_end_b_256": [
        "assets/textures/m256/Trollh_Boden_b_End_b_256.tga",
    ],
    "trollh_bodenkram_a_256": [
        "assets/textures/m256/Trollh_Bodenkram_a_256.tga",
    ],
    "trollh_einrichtung_a_256": [
        "assets/textures/m256/Trollh_Einrichtung_a_256.tga",
    ],
    "trollh_einrichtung_b_256": [
        "assets/textures/m256/Trollh_Einrichtung_b_256.tga",
    ],
    "trollh_folterkammer_a_256": [
        "assets/textures/m256/Trollh_Folterkammer_a_256.tga",
    ],
    "trollh_folterkammer_b_256": [
        "assets/textures/m256/Trollh_Folterkammer_b_256.tga",
    ],
    "trollh_licht_a_256": [
        "assets/textures/m256/Trollh_Licht_a_256.tga",
    ],
    "trollh_tueren_a_256": [
        "assets/textures/m256/Trollh_Tueren_a_256.tga",
    ],
    "trollh_wandkram_a_256": [
        "assets/textures/m256/Trollh_Wandkram_a_256.tga",
    ],
    "trollh_wandschmuck_a_256": [
        "assets/textures/m256/Trollh_Wandschmuck_a_256.tga",
    ],
    "trollh_wandschmuck_c_256": [
        "assets/textures/m256/Trollh_Wandschmuck_c_256.tga",
    ],
    "trollh_wandschmuck_d_256": [
        "assets/textures/m256/Trollh_Wandschmuck_d_256.tga",
    ],
    "trollh_wandschmuck_e_256": [
        "assets/textures/m256/Trollh_Wandschmuck_e_256.tga",
    ],
    "turnier_buehne_a": [
        "assets/textures/m256/turnier_buehne_a.tga",
    ],
    "turnier_buehne_b": [
        "assets/textures/m256/turnier_buehne_b.tga",
    ],
    "turnier_buehne_c": [
        "assets/textures/m256/turnier_buehne_c.tga",
    ],
    "turnier_fahnen_a": [
        "assets/textures/m256/turnier_fahnen_a.tga",
    ],
    "turnier_standarten": [
        "assets/textures/m256/turnier_standarten.tga",
    ],
    "turnier_zelt_a": [
        "assets/textures/m256/turnier_zelt_a.tga",
    ],
    "turnier_zelt_b": [
        "assets/textures/m256/turnier_zelt_b.tga",
    ],
    "turnier_zubehoer_a": [
        "assets/textures/m256/turnier_zubehoer_a.tga",
    ],
    "turnier_zubehoer_b": [
        "assets/textures/m256/turnier_zubehoer_b.tga",
    ],
    "urwald_lianen_a": [
        "assets/textures/m256/Urwald_Lianen_a.tga",
    ],
    "urwald_moos_a_256": [
        "assets/textures/m256/Urwald_Moos_a_256.tga",
    ],
    "urwald_moos_b_256": [
        "assets/textures/m256/Urwald_Moos_b_256.tga",
    ],
    "urwald_pflanzen_a": [
        "assets/textures/m256/Urwald_Pflanzen_a.tga",
    ],
    "urwald_pflanzen_b": [
        "assets/textures/m256/Urwald_Pflanzen_b.tga",
    ],
    "urwald_pflanzen_c": [
        "assets/textures/m256/Urwald_Pflanzen_c.tga",
    ],
    "urwald_pflanzen_d": [
        "assets/textures/m256/Urwald_Pflanzen_d.tga",
    ],
    "urwald_pflanzen_e": [
        "assets/textures/m256/Urwald_Pflanzen_e.tga",
    ],
    "urwald_pilz_a_256": [
        "assets/textures/m256/Urwald_Pilz_a_256.tga",
    ],
    "urwald_rankelwand_a_256": [
        "assets/textures/m256/Urwald_Rankelwand_a_256.tga",
    ],
    "urwald_riesenpilzbaum_a": [
        "assets/textures/m256/Urwald_Riesenpilzbaum_a.tga",
    ],
    "urwald_riesenpilzbaum_b": [
        "assets/textures/m256/Urwald_Riesenpilzbaum_b.tga",
    ],
    "urwald_riesenpilzbaum_c": [
        "assets/textures/m256/Urwald_Riesenpilzbaum_c.tga",
    ],
    "urwald_riesentor": [
        "assets/textures/m256/Urwald_riesentor.tga",
    ],
    "urwald_riesentor_a": [
        "assets/textures/m256/Urwald_riesentor_a.tga",
    ],
    "urwald_schlabber_a": [
        "assets/textures/m256/Urwald_Schlabber_a.tga",
    ],
    "urwald_stein_256": [
        "assets/textures/m256/Urwald_stein_256.tga",
    ],
    "urwald_trolltempel_a_256": [
        "assets/textures/m256/Urwald_Trolltempel_a_256.tga",
    ],
    "urwald_wurzeln_a_256": [
        "assets/textures/m256/Urwald_Wurzeln_a_256.tga",
    ],
    "urwald_wurzeln_b_256": [
        "assets/textures/m256/Urwald_Wurzeln_b_256.tga",
    ],
    "urwald_wurzeln_c_256": [
        "assets/textures/m256/Urwald_Wurzeln_c_256.tga",
    ],
    "urwald_wurzeln_d_256": [
        "assets/textures/m256/Urwald_Wurzeln_d_256.tga",
    ],
    "vulcan_seamless_2": [
        "assets/textures/m128/vulcan_seamless_2.tga",
    ],
    "wasser_128": [
        "assets/textures/m128/wasser_128.tga",
    ],
    "wasser_sumpf_a": [
        "assets/textures/m256/Wasser_Sumpf_a.tga",
    ],
    "wuker01": [
        "assets/textures/m256/wuker01.tga",
    ],
    "zahnraeder": [
        "assets/textures/m256/zahnraeder.tga",
    ],
    "zahnraeder_b": [
        "assets/textures/m256/zahnraeder_b.tga",
    ],
    "zfrau_augen_erstaunt": [
        "assets/textures/m064/ZFrau_Augen_erstaunt.tga",
    ],
    "zfrau_augen_normal": [
        "assets/textures/m064/ZFrau_Augen_normal.tga",
    ],
    "zfrau_augen_sonnenbrille": [
        "assets/textures/m064/ZFrau_Augen_Sonnenbrille.tga",
    ],
    "zfrau_gesicht_a_i": [
        "assets/textures/m128/ZFrau_Gesicht_A_I.tga",
    ],
    "zfrau_gesicht_normal": [
        "assets/textures/m128/ZFrau_Gesicht_normal.tga",
    ],
    "zfrau_gesicht_o_u": [
        "assets/textures/m128/ZFrau_Gesicht_O_U.tga",
    ],
    "zfrau_haar_hip_2": [
        "assets/textures/m064/zfrau_haar_hip_2.tga",
    ],
    "zfrau_haar_red_natural": [
        "assets/textures/m064/zfrau_haar_red_natural.tga",
    ],
    "zfrau_haare": [
        "assets/textures/m128/ZFrau_Haare.tga",
    ],
    "zfrau_koerper_oben": [
        "assets/textures/m128/ZFrau_Koerper_oben.tga",
    ],
    "zfrau_koerper_oben_v1": [
        "assets/textures/m128/ZFrau_Koerper_oben_v1.tga",
    ],
    "zfrau_koerper_oben_v2": [
        "assets/textures/m128/ZFrau_Koerper_oben_v2.tga",
    ],
    "zfrau_koerper_oben_v3": [
        "assets/textures/m128/ZFrau_Koerper_oben_v3.tga",
    ],
    "zfrau_koerper_unten": [
        "assets/textures/m128/ZFrau_Koerper_unten.tga",
    ],
    "zfrau_koerper_unten_v1": [
        "assets/textures/m128/ZFrau_Koerper_unten_v1.tga",
    ],
    "zfrau_koerper_unten_v2": [
        "assets/textures/m128/ZFrau_Koerper_unten_v2.tga",
    ],
    "zfrau_koerper_unten_v3": [
        "assets/textures/m128/ZFrau_Koerper_unten_v3.tga",
    ],
    "zmann_augen_normal": [
        "assets/textures/m064/ZMann_Augen_normal.tga",
    ],
    "zmann_augen_skeptisch": [
        "assets/textures/m064/ZMann_Augen_skeptisch.tga",
    ],
    "zmann_augen_sonnenbrille": [
        "assets/textures/m064/ZMann_Augen_Sonnenbrille.tga",
    ],
    "zmann_gesicht_a_i": [
        "assets/textures/m128/ZMann_Gesicht_A_I.tga",
    ],
    "zmann_gesicht_e": [
        "assets/textures/m128/ZMann_Gesicht_E.tga",
    ],
    "zmann_gesicht_normal": [
        "assets/textures/m128/ZMann_Gesicht_normal.tga",
    ],
    "zmann_haare": [
        "assets/textures/m128/ZMann_Haare.tga",
    ],
    "zmann_koerper_oben": [
        "assets/textures/m128/ZMann_Koerper_oben.tga",
    ],
    "zmann_koerper_oben_v1": [
        "assets/textures/m128/ZMann_Koerper_oben_v1.tga",
    ],
    "zmann_koerper_oben_v2": [
        "assets/textures/m128/ZMann_Koerper_oben_v2.tga",
    ],
    "zmann_koerper_oben_v3": [
        "assets/textures/m128/ZMann_Koerper_oben_v3.tga",
    ],
    "zmann_koerper_unten": [
        "assets/textures/m128/ZMann_Koerper_unten.tga",
    ],
    "zmann_koerper_unten_v1": [
        "assets/textures/m128/ZMann_Koerper_unten_v1.tga",
    ],
    "zmann_koerper_unten_v2": [
        "assets/textures/m128/ZMann_Koerper_unten_v2.tga",
    ],
    "zmann_koerper_unten_v3": [
        "assets/textures/m128/ZMann_Koerper_unten_v3.tga",
    ],
    "zwerge_boden_a": [
        "assets/textures/m256/Zwerge_Boden_a.tga",
    ],
    "zwerge_boden_a_end_a": [
        "assets/textures/m256/Zwerge_Boden_a_End_a.tga",
    ],
    "zwerge_boden_b": [
        "assets/textures/m256/Zwerge_Boden_b.tga",
    ],
    "zwerge_boden_b_end_a": [
        "assets/textures/m256/Zwerge_Boden_b_End_a.tga",
    ],
    "zwerge_boden_c": [
        "assets/textures/m256/Zwerge_Boden_c.tga",
    ],
    "zwerge_boden_c_end_a": [
        "assets/textures/m256/Zwerge_Boden_c_End_a.tga",
    ],
    "zwerge_holz_b_256": [
        "assets/textures/m256/Zwerge_Holz_b_256.tga",
    ],
    "zwerge_holz_c_256": [
        "assets/textures/m256/Zwerge_Holz_c_256.tga",
    ],
    "zwerge_kuech_industr_a": [
        "assets/textures/m256/Zwerge_kuech_industr_a.tga",
    ],
    "zwerge_kuech_industr_b": [
        "assets/textures/m256/Zwerge_kuech_industr_b.tga",
    ],
    "zwerge_mechzeitalter_a_256": [
        "assets/textures/m256/Zwerge_mechZeitalter_a_256.tga",
    ],
    "zwerge_mechzeitalter_b": [
        "assets/textures/m256/Zwerge_mechZeitalter_b.tga",
    ],
    "zwerge_schlaf_gold_a": [
        "assets/textures/m256/Zwerge_schlaf_gold_a.tga",
    ],
    "zwerge_wohn_industr_a": [
        "assets/textures/m256/Zwerge_wohn_industr_a.tga",
    ],
    "zwerge_wohn_industr_b": [
        "assets/textures/m256/Zwerge_wohn_industr_b.tga",
    ],
    "zwerge_wohn_industr_c": [
        "assets/textures/m256/Zwerge_wohn_industr_c.tga",
    ],
}

    unmatched_objects = []
    
    for obj in list(bpy.context.scene.objects):
        if obj.type != 'MESH' or obj == root:
            continue
            
        # Try to extract animation, frame, link, material index and material name from object name
        anim_name, frame_num, link_num, material_index, material_name_from_obj = extract_model_info(obj.name)
        
        if anim_name is not None and frame_num is not None and link_num is not None:
            # Create entry in animations dict
            if anim_name not in animations:
                animations[anim_name] = {}
            
            if frame_num not in animations[anim_name]:
                animations[anim_name][frame_num] = []
                
            # Store original material index and name with object for later use
            obj['original_material_index'] = material_index if material_index >= 0 else -1
            if material_name_from_obj:
                obj['original_material_name'] = material_name_from_obj
            
            # Extract material name from object for texture selection
            material_name = None
            if obj.material_slots and obj.material_slots[0].material:
                material_name = obj.material_slots[0].material.name
            
            # Add this object to the animation with material info
            if 'original_material_index' in obj:
                material_index = obj['original_material_index']
            else:
                material_index = -1
                
            animations[anim_name][frame_num].append((obj, link_num, material_index))
            
            # Check if this is baby.3db model
            model_is_baby = model_name and 'baby' in model_name.lower()
            
            if model_is_baby:
                # Apply hardcoded textures for baby.3db
                if link_num == 0:
                    texture_path = "assets/textures/m128/Character_ZBaby_a.tga" 
                    material_name = "character_zbaby_a"
                elif link_num == 1:
                    texture_path = "assets/textures/m256/helme_huete_a.tga"
                    material_name = "helme_huete_a"
                else:
                    # Find appropriate texture for other links
                    texture_path = get_texture_for_model_part(anim_name, link_num, material_name, textures)
            else:
                # Find appropriate texture
                texture_path = get_texture_for_model_part(anim_name, link_num, material_name, textures)
            
            # Create and apply material with texture
            if texture_path:
                # Check if the object has a material index from the original model
                material_index = obj.get('material_index', -1)
                original_material_info = None
                
                # If we have model material data, try to get the original material info
                if model_name and 'material_index' in obj:
                    material_index = obj['material_index']
                    
                    # Try to find this material in model_material_data
                    material_data = load_model_specific_mappings(model_name)
                    if material_data and 'materials' in material_data:
                        # Search by index
                        for mat_name, mat_info in material_data['materials'].items():
                            if mat_info.get('index') == material_index:
                                original_material_info = mat_info
                                original_material_name = mat_name
                                log(f"Found original material info for index {material_index}: {mat_name}")
                                break
                
                # Generate material name
                if model_is_baby:
                    if link_num == 0:
                        mat_name = "Material_Character_ZBaby_a"
                    elif link_num == 1:
                        mat_name = "Material_helme_huete_a"
                    else:
                        mat_name = f"link{link_num}_material"
                else:
                    # First check if we have an original material name directly from the object
                    if hasattr(obj, 'original_material_name') or 'original_material_name' in obj:
                        # Use exactly the material name from the 3DB file
                        mat_name = obj.get('original_material_name', '')
                        log(f"Using material name directly from object: {mat_name}")
                    
                    # Try to find object name as a material name in 3DB file
                    elif obj.name and '.' in obj.name:
                        # Remove Blender's suffix like .001, .002
                        base_name = obj.name.rsplit('.', 1)[0]
                        if material_data := MODEL_MATERIAL_DATA.get('materials', {}):
                            for mat_name_key, mat_info in material_data.items():
                                clean_mat_name = mat_name_key.replace("b'", "").replace("'", "").strip()
                                if clean_mat_name == base_name:
                                    mat_name = clean_mat_name
                                    log(f"Using object name {obj.name} as material name: {mat_name}")
                                    break
                            else:
                                # Not found in materials - use default
                                mat_name = f"link{link_num}_material_{material_index:02d}"
                        else:
                            mat_name = f"link{link_num}_material_{material_index:02d}"
                    
                    # Check if we have valid material index from GLTF
                    elif material_index >= 0:
                        # Try to find the original material name in the model_material_data
                        original_mat_name = None
                        material_data = MODEL_MATERIAL_DATA.get('materials', {})
                        
                        if material_data:
                            for mat_name_key, mat_info in material_data.items():
                                if 'index' in mat_info and mat_info['index'] == material_index:
                                    # Use material name directly from 3DB file
                                    original_mat_name = mat_name_key.replace("b'", "").replace("'", "").strip()
                                    break
                        
                        if original_mat_name:
                            # Use the original material name
                            mat_name = original_mat_name
                            log(f"Using material name from index {material_index}: {mat_name}")
                        else:
                            # Just use the index
                            mat_name = f"material_{material_index:02d}"
                            
                    # Fallback to material name from object if available
                    elif material_name and material_name.strip():
                        # Try to find this material in mapping
                        found = False
                        if material_data := MODEL_MATERIAL_DATA.get('materials', {}):
                            for mat_name_key in material_data.keys():
                                if mat_name_key.lower().replace("b'", "").replace("'", "").strip() == material_name.lower():
                                    mat_name = mat_name_key.replace("b'", "").replace("'", "").strip()
                                    found = True
                                    log(f"Found matching material in mapping: {mat_name}")
                                    break
                        
                        if not found:
                            clean_mat_name = material_name.replace(" ", "_").replace("'", "").replace('"', '')
                            mat_name = clean_mat_name
                        
                    # Last resort: use link number
                    else:
                        mat_name = f"link{link_num}_material"
                
                # Create/assign the material
                setup_material(obj, mat_name, texture_path)
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
            
            # Check if this is baby.3db model
            model_is_baby = model_name and 'baby' in model_name.lower()
            
            if model_is_baby:
                # Apply hardcoded textures for baby.3db miscellaneous objects
                if i == 0:
                    texture_path = "assets/textures/m128/Character_ZBaby_a.tga" 
                    material_name = "character_zbaby_a"
                elif i == 1:
                    texture_path = "assets/textures/m256/helme_huete_a.tga"
                    material_name = "helme_huete_a"
                else:
                    # Find appropriate texture for other links
                    texture_path = get_texture_for_model_part(misc_anim, i, material_name, textures)
            else:
                # Find appropriate texture
                texture_path = get_texture_for_model_part(misc_anim, i, material_name, textures)
            
            # Create and apply material with texture
            if texture_path:
                # Check if object has original material index
                material_index = obj.get('material_index', -1)
                
                # Use consistent material naming to prevent duplicates
                if model_is_baby:
                    if i == 0:
                        mat_name = "Material_Character_ZBaby_a"
                    elif i == 1:
                        mat_name = "Material_helme_huete_a"
                    else:
                        mat_name = f"link{i}_material"
                else:
                    # First check if we have an original material name directly from the object
                    if hasattr(obj, 'original_material_name') or 'original_material_name' in obj:
                        # Use exactly the material name from the 3DB file
                        mat_name = obj.get('original_material_name', '')
                        log(f"Using material name directly from object: {mat_name}")
                    
                    # Try to find object name as a material name in 3DB file
                    elif obj.name and '.' in obj.name:
                        # Remove Blender's suffix like .001, .002
                        base_name = obj.name.rsplit('.', 1)[0]
                        if material_data := MODEL_MATERIAL_DATA.get('materials', {}):
                            for mat_name_key, mat_info in material_data.items():
                                clean_mat_name = mat_name_key.replace("b'", "").replace("'", "").strip()
                                if clean_mat_name == base_name:
                                    mat_name = clean_mat_name
                                    log(f"Using object name {obj.name} as material name: {mat_name}")
                                    break
                            else:
                                # Not found in materials - use default
                                mat_name = f"misc_material_{i:02d}"
                        else:
                            mat_name = f"misc_material_{i:02d}"
                                
                    # Second priority: use material index if available
                    elif hasattr(obj, 'original_material_index') or 'original_material_index' in obj:
                        # Use the stored material index from the object 
                        material_index = obj.get('original_material_index', -1)
                        
                        # Try to find the original material name in the model_material_data
                        original_mat_name = None
                        material_data = MODEL_MATERIAL_DATA.get('materials', {})
                        
                        if material_data:
                            for mat_name_key, mat_info in material_data.items():
                                if 'index' in mat_info and mat_info['index'] == material_index:
                                    # Use material name directly from 3DB file
                                    original_mat_name = mat_name_key.replace("b'", "").replace("'", "").strip()
                                    break
                        
                        if original_mat_name:
                            # Use the original material name
                            mat_name = original_mat_name
                            log(f"Using material name from index {material_index}: {mat_name}")
                        else:
                            # Just use the index
                            mat_name = f"material_{material_index:02d}"
                            
                    # Second priority: use material name from object if available
                    elif material_name and material_name.strip():
                        # Clean material name for use as identifier
                        clean_mat_name = material_name.lower().replace(" ", "_").replace("'", "").replace('"', '')
                        mat_name = f"material_{clean_mat_name}"
                        
                    # Last resort: use index position
                    else:
                        mat_name = f"misc_material_{i:02d}"
                
                setup_material(obj, mat_name, texture_path)
    
    # Build hierarchy
    log(f"Building hierarchy for {len(animations)} animations")
    
    # Создаем словарь для отслеживания анимаций с одинаковыми именами
    anim_name_counts = {}
    for anim_name in animations.keys():
        if anim_name in anim_name_counts:
            anim_name_counts[anim_name] += 1
        else:
            anim_name_counts[anim_name] = 1
    
    # Выводим список анимаций с одинаковыми именами для отладки
    duplicate_names = [name for name, count in anim_name_counts.items() if count > 1]
    if duplicate_names:
        log(f"WARNING: Found duplicate animation names: {duplicate_names}")
    
    # Используем счетчик для создания уникальных имен анимаций
    anim_name_indexer = {}
    
    for anim_name, frames in animations.items():
        # Создаем уникальное имя для анимации с индексом, если имя не уникально
        if anim_name not in anim_name_indexer:
            anim_name_indexer[anim_name] = 0
        else:
            anim_name_indexer[anim_name] += 1
        
        # Если это анимация с дублирующимся именем, добавляем индекс к имени
        unique_anim_name = anim_name
        if anim_name_counts[anim_name] > 1:
            unique_anim_name = f"{anim_name}_{anim_name_indexer[anim_name]:02d}"
            log(f"Creating unique animation name: {unique_anim_name} for duplicate animation {anim_name}")
            
        # Create animation object with unique name
        anim_obj = bpy.data.objects.new(unique_anim_name, None)
        bpy.context.scene.collection.objects.link(anim_obj)
        anim_obj.parent = root
        
        for frame_num, objects in frames.items():
            # Create frame object with standardized name format
            frame_obj = bpy.data.objects.new(f"frame_{frame_num:03d}", None)
            bpy.context.scene.collection.objects.link(frame_obj)
            frame_obj.parent = anim_obj
            
            # Parent objects to frame object
            for obj, link_num, material_index in objects:
                # Create a unique name that includes material index if available
                if material_index >= 0:
                    base_link_name = f"link_{link_num:02d}_mat_{material_index:02d}"
                else:
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
        os.path.dirname(bpy.data.filepath)]
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
        "Troll_Kopf001.tga"
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

def extract_material_indices_from_gltf(gltf_path):
    """Extract material indices from GLTF file to match with original model."""
    try:
        import json
        with open(gltf_path, 'r') as f:
            gltf_data = json.load(f)
        
        # Create mapping from node name to material index
        material_indices = {}
        
        # Check if we have meshes in the GLTF
        if 'meshes' in gltf_data and 'nodes' in gltf_data:
            # Process nodes to find names and mesh references
            for node_index, node in enumerate(gltf_data['nodes']):
                if 'name' in node and 'mesh' in node:
                    node_name = node['name']
                    mesh_index = node['mesh']
                    
                    # Extract link number and other info from node name
                    if '_link' in node_name:
                        try:
                            link_parts = node_name.split('_link')
                            link_num = int(link_parts[1].split('_')[0])
                            
                            # Get the material index from the mesh primitives
                            if mesh_index < len(gltf_data['meshes']):
                                mesh = gltf_data['meshes'][mesh_index]
                                if 'primitives' in mesh and len(mesh['primitives']) > 0:
                                    # Get material index if available
                                    if 'material' in mesh['primitives'][0]:
                                        material_index = mesh['primitives'][0]['material']
                                        # Store in our mapping
                                        material_indices[node_name] = {
                                            'link': link_num,
                                            'material': material_index,
                                            # Store the material name if available
                                            'material_name': node_name.split('_')[-1] if '_' in node_name else ''
                                        }
                        except Exception as e:
                            log(f"Error parsing node name {node_name}: {e}")
        
        log(f"Extracted {len(material_indices)} material mappings from GLTF")
        return material_indices
    except Exception as e:
        error(f"Failed to extract material indices from GLTF: {e}")
        return {}

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
        material_mapping = {}
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    if 'model_name' in config:
                        model_name = config['model_name']
                        log(f"Using model name from config: {model_name}")
                    
                    # Load material to texture map from config
                    if 'material_texture_map' in config:
                        material_mapping = config['material_texture_map']
                        log(f"Loaded {len(material_mapping)} material mappings from config")
            except Exception as e:
                error(f"Error loading config: {str(e)}")
        
        # Also check environment variable for model name
        if not model_name and 'MODEL_NAME' in os.environ:
            model_name = os.environ['MODEL_NAME']
            log(f"Using model name from environment: {model_name}")
        
        # Load model-specific material mappings if available
        model_material_data = {}
        if model_name:
            model_material_data = load_model_specific_mappings(model_name)
            if model_material_data and 'materials' in model_material_data:
                log(f"Model {model_name}: Found {len(model_material_data.get('materials', {}))} materials in mapping")
                # Store global variable for use in material naming
                global MODEL_MATERIAL_DATA
                MODEL_MATERIAL_DATA = model_material_data
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_fbx)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        # Create textures directory and copy all textures
        textures_dir = os.path.join(output_dir, 'textures')
        force_copy_textures(textures_dir)
        
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
        export_result = bpy.ops.export_scene.fbx(
            filepath=output_fbx,
            use_selection=False,  # Export all objects, not just selected
            object_types={'ARMATURE', 'MESH', 'EMPTY'},
            use_mesh_modifiers=True,
            mesh_smooth_type='FACE',
            use_tspace=True,
            use_custom_props=True,
            path_mode='COPY',
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
if "--" in sys.argv:
    main()
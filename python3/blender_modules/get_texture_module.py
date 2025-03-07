"""
Module for getting textures for model parts.
"""

import os
import re
from .logger import log, error
from .config import (
    PRIORITIZE_MAPPINGS, MATERIAL_TEXTURE_MAPPINGS, MODEL_MATERIAL_DATA,
    DIRECT_MATERIAL_MAPPINGS, BASE_MATERIAL_MAPPINGS, MODEL_TEXTURES_DIR,
    PROBLEM_MATERIAL_MAPPINGS
)

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
    
    # Use our new texture matcher for improved matching
    from .texture_matcher import find_best_texture_match
    
    # First try with base material name (without suffixes)
    if base_material_name:
        texture_path = find_best_texture_match(base_material_name, textures)
        if texture_path:
            log(f"Found texture using advanced matcher for base name: {base_material_name} -> {texture_path}")
            return texture_path
    
    # If that fails, try with the full material name
    if material_clean and material_clean != base_material_name:
        texture_path = find_best_texture_match(material_clean, textures)
        if texture_path:
            log(f"Found texture using advanced matcher for full name: {material_clean} -> {texture_path}")
            return texture_path
    
    # Fall back to direct mappings if available
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
    
    # Check model-specific material data from mapping file
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
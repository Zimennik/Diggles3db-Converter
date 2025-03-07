"""
Material manager module for creating and managing materials.
"""

import os
import bpy
import re
from .logger import log, error
from .material_cache import get_cached_material, add_material_to_cache, get_base_material_name
from .get_texture_module import get_texture_for_model_part

def setup_material(obj, material_name, texture_path, suffix=None):
    """Create material with texture for an object."""
    if not texture_path or not os.path.exists(texture_path):
        error(f"Texture not found: {texture_path}")
        return None
    
    # First check if this is a direct 3DB material name
    is_direct_material = False
    from .config import MODEL_MATERIAL_DATA
    
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
    
    # Check if we have this material in our cache
    cached_mat = get_cached_material(actual_material_name, texture_path)
    if cached_mat:
        log(f"Reusing cached material {actual_material_name} with texture {os.path.basename(texture_path)}")
        # Assign material to object
        if len(obj.material_slots) == 0:
            obj.data.materials.append(cached_mat)
        else:
            obj.material_slots[0].material = cached_mat
        return cached_mat
    
    # Check if material with this name already exists in Blender
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
            # Add to our cache
            add_material_to_cache(actual_material_name, texture_path, mat)
            return mat
        else:
            # Material exists but has different texture - create new unique name
            log(f"Material {actual_material_name} exists but with different texture, creating unique name")
            base_name = get_base_material_name(actual_material_name)
            counter = 1
            while f"{base_name}_{counter:03d}" in bpy.data.materials:
                counter += 1
            actual_material_name = f"{base_name}_{counter:03d}"
            log(f"Using new unique material name: {actual_material_name}")
    
    # Create new material with unique name
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
    
    # Add to our cache
    add_material_to_cache(actual_material_name, texture_path, mat)
        
    log(f"Created material {material_name} with texture {os.path.basename(texture_path)}")
    return mat

def update_material_texture(mat, texture_path):
    """Update texture in existing material."""
    if not mat.use_nodes:
        mat.use_nodes = True
    
    node_tree = mat.node_tree
    
    # Find existing texture node or create a new one
    tex_image = None
    for node in node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            tex_image = node
            break
    
    if not tex_image:
        tex_image = node_tree.nodes.new('ShaderNodeTexImage')
        
        # Connect to principled BSDF if available
        bsdf = None
        for node in node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf = node
                break
        
        if bsdf:
            node_tree.links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])
    
    # Load the image
    try:
        image = None
        for img in bpy.data.images:
            if img.filepath == texture_path:
                image = img
                break
                
        if not image:
            image = bpy.data.images.load(texture_path)
        
        tex_image.image = image
        
        # Update material properties
        mat.original_texture = texture_path
        
        # Set transparency if needed
        if image.depth == 32:
            mat.blend_method = 'BLEND'
            
            # Connect alpha if principled BSDF found
            for node in node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    node_tree.links.new(tex_image.outputs['Alpha'], node.inputs['Alpha'])
                    break
        
        log(f"Updated material {mat.name} with texture {os.path.basename(texture_path)}")
        return True
    except Exception as e:
        error(f"Error updating texture {texture_path}: {str(e)}")
        return False
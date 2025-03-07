"""
Module for building object hierarchies in Blender
"""

import bpy
import os
from .logger import log, error
from .texture_finder import find_texture_files
from .material_manager import get_texture_for_model_part, setup_material
from .object_processor import extract_model_info, extract_material_indices_from_gltf
from .mesh_consolidator import preprocess_objects, get_base_object_name, get_base_material_name

def create_root_object(model_name):
    """Create root object for the model."""
    root = bpy.data.objects.new(model_name, None)
    bpy.context.scene.collection.objects.link(root)
    return root

def create_animation_object(anim_name, root):
    """Create animation object and parent it to root."""
    anim_obj = bpy.data.objects.new(anim_name, None)
    bpy.context.scene.collection.objects.link(anim_obj)
    anim_obj.parent = root
    return anim_obj

def create_frame_object(frame_num, anim_obj):
    """Create frame object and parent it to animation object."""
    frame_obj = bpy.data.objects.new(f"frame_{frame_num:03d}", None)
    bpy.context.scene.collection.objects.link(frame_obj)
    frame_obj.parent = anim_obj
    return frame_obj

def create_link_object(obj, link_num, material_index, frame_obj):
    """Create link object with unique name."""
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
    log(f"Added {link_name} to {frame_obj.name} in {frame_obj.parent.name}")
    
    # Create a links dictionary for the frame if not already created
    if not hasattr(frame_obj, "links_dict"):
        frame_obj["links_dict"] = {str(link_num): obj.name}
    else:
        # Add to existing dictionary
        links_data = frame_obj["links_dict"]
        links_data[str(link_num)] = obj.name

def process_matched_objects(matched_objects, model_name, textures, animations):
    """Process objects that match naming pattern."""
    for obj, anim_name, frame_num, link_num, material_index, material_name_from_obj in matched_objects:
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
                from .config import MODEL_MATERIAL_DATA
                material_data = MODEL_MATERIAL_DATA
                
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
                    from .config import MODEL_MATERIAL_DATA
                    material_data = MODEL_MATERIAL_DATA
                    
                    if material_data and 'materials' in material_data:
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
                    from .config import MODEL_MATERIAL_DATA
                    material_data = MODEL_MATERIAL_DATA
                    
                    if material_data and 'materials' in material_data:
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
                    from .config import MODEL_MATERIAL_DATA
                    material_data = MODEL_MATERIAL_DATA
                    
                    if material_data and 'materials' in material_data:
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

def process_unmatched_objects(unmatched_objects, model_name, textures, animations):
    """Process objects that don't match standard naming pattern."""
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
                        from .config import MODEL_MATERIAL_DATA
                        material_data = MODEL_MATERIAL_DATA
                        
                        if material_data and 'materials' in material_data:
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
                        from .config import MODEL_MATERIAL_DATA
                        material_data = MODEL_MATERIAL_DATA
                        
                        if material_data and 'materials' in material_data:
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
            else:
                log(f"No texture found for unmatched object {obj.name}")

def build_hierarchy(animations, root):
    """Build hierarchy of animation, frame, and link objects."""
    log(f"Building hierarchy for {len(animations)} animations")
    
    # Create a dictionary to track animations with the same names
    anim_name_counts = {}
    for anim_name in animations.keys():
        if anim_name in anim_name_counts:
            anim_name_counts[anim_name] += 1
        else:
            anim_name_counts[anim_name] = 1
    
    # Output the list of animations with the same names for debugging
    duplicate_names = [name for name, count in anim_name_counts.items() if count > 1]
    if duplicate_names:
        log(f"WARNING: Found duplicate animation names: {duplicate_names}")
    
    # Use a counter to create unique animation names
    anim_name_indexer = {}
    
    for anim_name, frames in animations.items():
        # Create a unique name for the animation with an index if the name is not unique
        if anim_name not in anim_name_indexer:
            anim_name_indexer[anim_name] = 0
        else:
            anim_name_indexer[anim_name] += 1
        
        # If this is an animation with a duplicate name, add an index to the name
        unique_anim_name = anim_name
        if anim_name_counts[anim_name] > 1:
            unique_anim_name = f"{anim_name}_{anim_name_indexer[anim_name]:02d}"
            log(f"Creating unique animation name: {unique_anim_name} for duplicate animation {anim_name}")
        
        # Create animation object with unique name
        anim_obj = create_animation_object(unique_anim_name, root)
        
        for frame_num, objects in frames.items():
            # Create frame object
            frame_obj = create_frame_object(frame_num, anim_obj)
            
            # Parent objects to frame object
            for obj, link_num, material_index in objects:
                create_link_object(obj, link_num, material_index, frame_obj)

def process_gltf_structure(gltf_path, model_name=None):
    """Organize imported GLTF into proper hierarchy."""
    # Extract material mappings from GLTF to use for naming
    material_indices = extract_material_indices_from_gltf(gltf_path)
    log(f"Found {len(material_indices)} material indices to use for naming")
    
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
    
    # IMPORTANT: Preprocess objects to handle duplicates and fix material issues
    # This significantly reduces the number of materials and improves texture assignment        
    preprocess_objects()
            
    # Store material information for later use
    # We'll add material indices to object custom properties
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and '_link' in obj.name:
            # Get the base name (without Blender suffixes)
            base_obj_name = get_base_object_name(obj.name)
            
            # Extract material index from our mapping if available
            if base_obj_name in material_indices:
                material_info = material_indices[base_obj_name]
                obj['material_index'] = material_info['material']
                log(f"Set material index {material_info['material']} for {obj.name}")
            elif obj.name in material_indices:
                material_info = material_indices[obj.name]
                obj['material_index'] = material_info['material']
                log(f"Set material index {material_info['material']} for {obj.name}")
            elif 'materials' in MODEL_MATERIAL_DATA:
                # Try to find material index by looking at link position
                try:
                    link_parts = obj.name.split('_link')
                    link_num = int(link_parts[1].split('_')[0])
                    
                    # Check each material in mapping to see which ones use this link position
                    for mat_name, mat_info in MODEL_MATERIAL_DATA['materials'].items():
                        if 'links' in mat_info and link_num in mat_info['links']:
                            obj['material_index'] = mat_info['index']
                            # Also store the original material name for better texture matching
                            clean_mat_name = mat_name.replace("b'", "").replace("'", "").strip()
                            obj['original_material_name'] = clean_mat_name
                            log(f"Set material index {mat_info['index']} for {obj.name} based on link position {link_num}")
                            break
                except Exception as e:
                    log(f"Error finding material for {obj.name}: {e}")
    
    # If no model name provided, get from filename
    if not model_name:
        model_name = os.path.splitext(os.path.basename(gltf_path))[0]
        log(f"Using model name from filename: {model_name}")
        
    # Create root object
    root = create_root_object(model_name)
    
    # Find textures
    textures = find_texture_files()
    
    # Extract animation, frame, and link information from object names
    animations = {}
    
    # Track objects that match and don't match naming pattern
    matched_objects = []
    unmatched_objects = []
    
    for obj in list(bpy.context.scene.objects):
        if obj.type != 'MESH' or obj == root:
            continue
            
        # Try to extract animation, frame, link, material index and material name from object name
        anim_name, frame_num, link_num, material_index, material_name_from_obj = extract_model_info(obj.name)
        
        if anim_name is not None and frame_num is not None and link_num is not None:
            matched_objects.append((obj, anim_name, frame_num, link_num, material_index, material_name_from_obj))
        else:
            log(f"Object name doesn't match pattern: {obj.name}")
            unmatched_objects.append(obj)
    
    # Process matched objects
    process_matched_objects(matched_objects, model_name, textures, animations)
    
    # Handle unmatched objects if any
    process_unmatched_objects(unmatched_objects, model_name, textures, animations)
    
    # Build hierarchy
    build_hierarchy(animations, root)
    
    # Select all objects for export
    bpy.ops.object.select_all(action='SELECT')
    bpy.context.view_layer.objects.active = root
    
    log("Hierarchy building complete")
    return True
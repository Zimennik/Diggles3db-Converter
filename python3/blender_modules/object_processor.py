"""
Module for processing object names and model information
"""

import re
import json
import os
from .logger import log, error

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
    from .config import MODEL_MATERIAL_DATA
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
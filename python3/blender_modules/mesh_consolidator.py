"""
Module for consolidating duplicate meshes and fixing material issues.

This module helps solve two key problems:
1. Blender creates duplicate meshes with suffixes (.001, .002, etc.) during import
2. These duplicate meshes get different materials, causing texture assignment problems
"""

import bpy
import re
from .logger import log, error
from .config import MODEL_MATERIAL_DATA

def get_base_object_name(obj_name):
    """
    Extracts the base object name by removing Blender's numeric suffixes.
    
    Blender adds suffixes like .001, .002 to ensure unique object names,
    but these suffixes cause problems with material assignment. This function
    strips those suffixes while preserving material-specific suffixes.
    """
    obj_name_str = str(obj_name)
    
    # Check if this has a Blender-style numeric suffix (.001, .002, etc.)
    if '.' in obj_name_str:
        parts = obj_name_str.split('.')
        # If the last part is a 3-digit number, it's likely a Blender suffix
        if parts[-1].isdigit() and len(parts[-1]) == 3:
            # Remove the Blender suffix
            base_name = '.'.join(parts[:-1])
            return base_name
    
    # No Blender suffix found, return as is
    return obj_name_str

def get_base_material_name(material_name):
    """
    Extract base material name without Blender's numeric suffixes.
    
    For example: 'material.001' -> 'material'
    But preserves real material indices like 'kris_4_burg_a.022'
    """
    if not material_name:
        return ""
        
    # Check if it has a standard Blender suffix pattern
    match = re.match(r'^(.+)\.(\d{3})$', material_name)
    if match:
        return match.group(1)
    
    return material_name

def analyze_duplicate_objects():
    """
    Analyzes the scene to find objects with the same base name.
    Returns a dict mapping base names to lists of objects.
    """
    # Group objects by their base name
    object_groups = {}
    
    # First pass: collect all objects by their base name
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            base_name = get_base_object_name(obj.name)
            if base_name not in object_groups:
                object_groups[base_name] = []
            object_groups[base_name].append(obj)
    
    return object_groups

def analyze_duplicate_materials():
    """
    Analyzes materials to find duplicates based on base name.
    Returns a dict mapping base names to lists of materials.
    """
    # Group materials by their base name
    material_groups = {}
    
    for mat in bpy.data.materials:
        base_name = get_base_material_name(mat.name)
        if base_name not in material_groups:
            material_groups[base_name] = []
        material_groups[base_name].append(mat)
    
    return material_groups

def consolidate_materials():
    """
    Consolidates duplicate materials by keeping only one material per base name.
    Returns the number of materials consolidated.
    """
    log("Analyzing materials for consolidation...")
    material_groups = analyze_duplicate_materials()
    
    changes_made = 0
    for base_name, materials in material_groups.items():
        if len(materials) > 1:
            # Sort materials to ensure consistent selection (the one without a suffix comes first)
            materials.sort(key=lambda mat: mat.name)
            
            # Use the first material as the primary
            primary_mat = materials[0]
            
            # Replace all other materials with the primary
            for duplicate in materials[1:]:
                # Find all objects using this duplicate material and replace with primary
                for obj in bpy.data.objects:
                    if obj.type == 'MESH':
                        for slot in obj.material_slots:
                            if slot.material == duplicate:
                                log(f"Replacing material {duplicate.name} with {primary_mat.name} on {obj.name}")
                                slot.material = primary_mat
                                changes_made += 1
                
                # Once we've replaced all references to the duplicate, we can remove it
                # (Blender will prevent removal if there are still references)
                try:
                    bpy.data.materials.remove(duplicate)
                except Exception as e:
                    error(f"Could not remove material {duplicate.name}: {str(e)}")
    
    log(f"Consolidated {changes_made} material references")
    return changes_made

def transfer_material_data(source_obj, target_obj):
    """
    Transfers material-related metadata from source to target object.
    """
    # Transfer material index and material name if present
    if 'material_index' in source_obj:
        target_obj['material_index'] = source_obj['material_index']
        
    if 'original_material_name' in source_obj:
        target_obj['original_material_name'] = source_obj['original_material_name']
        
    # Transfer material slots if possible
    if len(source_obj.material_slots) > 0 and len(target_obj.material_slots) > 0:
        target_obj.material_slots[0].material = source_obj.material_slots[0].material

def find_material_by_index(index):
    """
    Searches for a material name using its index in MODEL_MATERIAL_DATA.
    """
    if not MODEL_MATERIAL_DATA or 'materials' not in MODEL_MATERIAL_DATA:
        return None
        
    for mat_name, mat_info in MODEL_MATERIAL_DATA['materials'].items():
        if 'index' in mat_info and mat_info['index'] == index:
            clean_name = mat_name.replace("b'", "").replace("'", "").strip()
            return clean_name
            
    return None

def preprocess_objects():
    """
    Main function to run all preprocessing steps for objects before creating hierarchy.
    """
    log("Starting object preprocessing...")
    
    # First, consolidate materials to reduce duplicates
    consolidated_materials = consolidate_materials()
    
    # Then analyze object structure
    object_groups = analyze_duplicate_objects()
    
    # Identify duplicate objects that need special handling
    duplicate_count = sum(1 for group in object_groups.values() if len(group) > 1)
    log(f"Found {duplicate_count} groups of duplicate objects")
    
    # For objects with duplicates, enhance them with material metadata
    for base_name, objects in object_groups.items():
        if len(objects) > 1:
            # Enhance object data with material info from model data
            enhanced = False
            
            # First try to find material data from object names
            for obj in objects:
                # If object name might be a material name
                if 'material_index' not in obj:
                    # Try to find material in mapping data
                    for mat_name, mat_info in MODEL_MATERIAL_DATA.get('materials', {}).items():
                        clean_name = mat_name.replace("b'", "").replace("'", "").strip()
                        if clean_name == base_name:
                            obj['material_index'] = mat_info['index']
                            obj['original_material_name'] = clean_name
                            enhanced = True
                            log(f"Enhanced object {obj.name} with material data: index={mat_info['index']}, name={clean_name}")
                            break
    
    # We don't actually remove duplicates here because that would disrupt 
    # the frame/animation structure. Instead, we've enhanced objects with
    # material data which will be used during hierarchy building.
    
    log("Preprocessing complete")
    return duplicate_count
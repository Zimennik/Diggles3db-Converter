"""
Configuration module for Blender script.
"""

import os
import json
import sys
from .logger import log, error

# Global configuration variables
PRIORITIZE_MAPPINGS = True  # Set to True to force texture assignments from mappings
MATERIAL_TEXTURE_MAPPINGS = {}
MODEL_MATERIAL_DATA = {}
DIRECT_MATERIAL_MAPPINGS = {}
BASE_MATERIAL_MAPPINGS = {}
MODEL_TEXTURES_DIR = ""

# Explicit problem material mappings that need special handling
PROBLEM_MATERIAL_MAPPINGS = {
    "kris_4_burg_a": "kris_4_burg_a.tga",
    "kris_4_burg_b": "kris_4_burg_b.tga", 
    "kris_4_burg_bc": "kris_4_burg_bc.tga",
    "kris_4_brain_a": "kris_4_brain_a.tga"
}

def load_global_mappings():
    """Load the global material texture mappings from mappings.json file."""
    global MATERIAL_TEXTURE_MAPPINGS
    
    mappings_file = os.path.join(os.getcwd(), "mappings.json")
    if os.path.exists(mappings_file):
        try:
            with open(mappings_file, 'r') as f:
                MATERIAL_TEXTURE_MAPPINGS = json.load(f)
            log(f"Loaded {len(MATERIAL_TEXTURE_MAPPINGS)} mappings from mappings.json")
        except Exception as e:
            error(f"Error loading mappings.json: {str(e)}")
    else:
        log("No mappings.json file found, using built-in defaults")

def load_model_specific_mappings(model_name):
    """Load model-specific material mappings from the exports/fbx directory."""
    global DIRECT_MATERIAL_MAPPINGS, BASE_MATERIAL_MAPPINGS, MODEL_TEXTURES_DIR, MODEL_MATERIAL_DATA
    
    # Regular material mapping
    mapping_path = os.path.join(os.getcwd(), "exports", "fbx", f"materials_{model_name}.json")
    material_data = {}
    
    try:
        if os.path.exists(mapping_path):
            log(f"Found model-specific mapping file: {mapping_path}")
            with open(mapping_path, 'r') as f:
                material_data = json.load(f)
            log(f"Loaded material mapping for {model_name} with {len(material_data.get('materials', {}))} materials")
            
            # Set the global variable
            MODEL_MATERIAL_DATA = material_data
    except Exception as e:
        error(f"Error loading model material mapping: {str(e)}")
    
    # Also check for direct material mapping file (new approach)
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
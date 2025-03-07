"""
Module for improved texture matching algorithms and diagnostics.

This module provides advanced functionality for matching material names to textures,
with special handling for known problematic cases and fuzzy matching algorithms.
"""

import os
import re
from difflib import SequenceMatcher
from .logger import log, error
from .config import PROBLEM_MATERIAL_MAPPINGS

def calculate_string_similarity(a, b):
    """
    Calculate similarity ratio between two strings using SequenceMatcher.
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        Similarity ratio between 0.0 and 1.0
    """
    return SequenceMatcher(None, a, b).ratio()

def is_likely_match(material_name, texture_name, min_ratio=0.8):
    """
    Determine if material name and texture name are likely to match.
    
    Args:
        material_name: Material name to check
        texture_name: Texture name to check
        min_ratio: Minimum similarity ratio required for a match
        
    Returns:
        True if names match according to our criteria, False otherwise
    """
    # Extract base names without extensions
    mat_base = material_name.lower()
    tex_base = os.path.splitext(texture_name.lower())[0]
    
    # Special handling for known problem cases - kris_ and kristall_
    if "kris_" in mat_base and "kristall" in tex_base:
        # Ensure it's really a mistaken match by checking string length
        if len(mat_base) > 5 and len(tex_base) > 8:
            log(f"BLOCKED MATCH: '{mat_base}' should not match '{tex_base}' (kris_/kristall_ conflict)")
            return False
    
    # Calculate basic similarity
    similarity = calculate_string_similarity(mat_base, tex_base)
    
    # More specific test for prefix matches
    if mat_base.startswith(tex_base) or tex_base.startswith(mat_base):
        min_length = min(len(mat_base), len(tex_base))
        required_chars = int(min_length * 0.8)
        
        # If prefix match with enough characters, it's likely a match
        if min_length >= 5 and required_chars >= 4:
            log(f"PREFIX MATCH: '{mat_base}' and '{tex_base}' match with prefix ({similarity:.2f})")
            return True
    
    # Log the overall similarity for debugging
    if similarity >= min_ratio:
        log(f"SIMILARITY MATCH: '{mat_base}' and '{tex_base}' match with ratio {similarity:.2f}")
        return True
    
    # Log when we reject a potential match
    if similarity > 0.5 and similarity < min_ratio:
        log(f"REJECTED MATCH: '{mat_base}' and '{tex_base}' with ratio {similarity:.2f} (below threshold)")
        
    return False

def find_best_texture_match(material_name, textures):
    """
    Find the best matching texture for a given material name.
    
    Args:
        material_name: Name of the material to match
        textures: Dictionary of available textures {name: path}
        
    Returns:
        Path to best matching texture or None if no good match found
    """
    # First handle known problem mappings
    if material_name in PROBLEM_MATERIAL_MAPPINGS:
        texture_name = PROBLEM_MATERIAL_MAPPINGS[material_name]
        log(f"Using problem material mapping for {material_name} -> {texture_name}")
        
        # Look for this texture in available textures
        for tex_name, tex_path in textures.items():
            if os.path.basename(tex_path).lower() == texture_name.lower():
                log(f"PROBLEM MATERIAL: Found exact texture for {material_name} -> {tex_path}")
                return tex_path
    
    # Try exact match first
    for tex_name, tex_path in textures.items():
        tex_base = os.path.splitext(os.path.basename(tex_path))[0].lower()
        if material_name.lower() == tex_base:
            log(f"EXACT MATCH: {material_name} -> {tex_path}")
            return tex_path
    
    # Then try fuzzy matching with similarity threshold
    matches = []
    for tex_name, tex_path in textures.items():
        if is_likely_match(material_name, os.path.basename(tex_path)):
            similarity = calculate_string_similarity(
                material_name.lower(), 
                os.path.splitext(os.path.basename(tex_path))[0].lower()
            )
            matches.append((similarity, tex_path))
    
    # Sort by similarity (highest first)
    if matches:
        matches.sort(reverse=True, key=lambda x: x[0])
        best_match = matches[0]
        log(f"BEST FUZZY MATCH: {material_name} -> {os.path.basename(best_match[1])} (score: {best_match[0]:.2f})")
        return best_match[1]
    
    # If no good match found
    log(f"NO TEXTURE MATCH: Could not find suitable texture for {material_name}")
    return None

def diagnose_texture_matches(materials, textures):
    """
    Analyze and diagnose texture matching for a set of materials.
    
    Args:
        materials: List of material names
        textures: Dictionary of available textures {name: path}
        
    Returns:
        Dictionary with diagnosis results
    """
    results = {
        "exact_matches": [],
        "fuzzy_matches": [],
        "no_matches": [],
        "problem_materials": []
    }
    
    for material in materials:
        if material in PROBLEM_MATERIAL_MAPPINGS:
            # Check if the problem mapping exists
            texture_name = PROBLEM_MATERIAL_MAPPINGS[material]
            found = False
            for tex_path in textures.values():
                if os.path.basename(tex_path).lower() == texture_name.lower():
                    found = True
                    results["problem_materials"].append({
                        "material": material,
                        "texture": texture_name,
                        "path": tex_path
                    })
                    break
            
            if not found:
                results["no_matches"].append(material)
            continue
        
        # Try exact match
        exact_match = None
        for tex_name, tex_path in textures.items():
            tex_base = os.path.splitext(os.path.basename(tex_path))[0].lower()
            if material.lower() == tex_base:
                exact_match = tex_path
                results["exact_matches"].append({
                    "material": material,
                    "texture": os.path.basename(tex_path),
                    "path": tex_path
                })
                break
        
        if exact_match:
            continue
        
        # Try fuzzy matching
        matches = []
        for tex_name, tex_path in textures.items():
            similarity = calculate_string_similarity(
                material.lower(), 
                os.path.splitext(os.path.basename(tex_path))[0].lower()
            )
            if similarity >= 0.7:
                matches.append((similarity, tex_path))
        
        if matches:
            matches.sort(reverse=True, key=lambda x: x[0])
            best_match = matches[0]
            results["fuzzy_matches"].append({
                "material": material,
                "texture": os.path.basename(best_match[1]),
                "similarity": best_match[0],
                "path": best_match[1]
            })
        else:
            results["no_matches"].append(material)
    
    return results
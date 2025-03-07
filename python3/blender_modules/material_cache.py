"""
Material cache module to prevent duplicate materials.
"""

# Global dictionary to cache materials
MATERIAL_CACHE = {}

def get_cached_material(material_name, texture_path):
    """
    Get a material from the cache if it exists.
    
    Args:
        material_name: The name of the material
        texture_path: Path to the texture file
        
    Returns:
        Cached material or None if not found
    """
    cache_key = f"{material_name}|{texture_path}"
    return MATERIAL_CACHE.get(cache_key)

def add_material_to_cache(material_name, texture_path, material):
    """
    Add a material to the cache.
    
    Args:
        material_name: The name of the material
        texture_path: Path to the texture file
        material: The material object to cache
    
    Returns:
        The material that was cached
    """
    cache_key = f"{material_name}|{texture_path}"
    MATERIAL_CACHE[cache_key] = material
    return material

def get_base_material_name(material_name):
    """
    Extract base material name without numeric suffix.
    
    Args:
        material_name: Original material name that might contain .001, .002 etc.
        
    Returns:
        Base material name without suffix
    """
    import re
    
    # Match only numeric suffixes with dots (.001, .002)
    # not numbers in the material name (like kris_4_burg_a)
    base_match = re.match(r'([a-zA-Z0-9_]+(?:_[a-zA-Z0-9_]+)*)(?:\.\d{3,})?$', material_name)
    
    if base_match:
        return base_match.group(1)
    return material_name

def get_materials_by_base_name(base_name):
    """
    Find all materials in the cache with a given base name.
    
    Args:
        base_name: Base name of the material to find
        
    Returns:
        List of (key, material) pairs with matching base name
    """
    results = []
    for key, material in MATERIAL_CACHE.items():
        material_name = key.split('|')[0]
        if get_base_material_name(material_name) == base_name:
            results.append((key, material))
    return results

def clear_cache():
    """Clear the material cache."""
    MATERIAL_CACHE.clear()
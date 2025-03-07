"""
Configuration options for the 3db export process.
"""

# Material settings
MATERIAL_SPECULAR = 0.1  # Specular intensity (0.0 - 1.0)
MATERIAL_ROUGHNESS = 0.8  # Surface roughness (0.0 - 1.0) - higher values reduce unwanted shine

# Export settings
EMBED_TEXTURES = False  # Whether to embed textures in the FBX file (false keeps file size smaller)
BLENDER_TIMEOUT = 600  # Maximum time in seconds to wait for Blender processing (10 minutes)
BLENDER_SCRIPT = "blender_script_fixed.py"  # Path to custom Blender script (relative to python3 dir)

# Model structure settings
MODEL_HIERARCHY = {
    "USE_MODEL_NAME_ROOT": True,  # Create root node with model name
    "FRAME_FORMAT": "frame_{:03d}",  # Format for frame names (3 digits with leading zeros)
    "LINK_FORMAT": "link_{:02d}"  # Format for mesh part names (2 digits with leading zeros)
}

# Texture settings
TEXTURE_SETTINGS = {
    "SEARCH_SUBDIRS": ["m256", "m128", "m064", "Gray", "ClassIcons", "Misc"],  # Subdirectories to search for textures
    "DEFAULT_EXTENSION": ".tga",  # Default texture extension when none specified
    "COLOR_SPACE": "sRGB"  # Color space for textures
}
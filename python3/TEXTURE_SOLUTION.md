# Diggles3DB Texture Assignment Solution

## Problem Description

The Diggles model converter was experiencing texture assignment issues where materials would
get assigned incorrect textures in the final FBX file. Specifically:

1. Materials with numeric suffixes (like `kris_4_burg_a.248`) would be assigned incorrect textures
   (like `kristall_details_a_kristall_details_a.tga.1029`) instead of the correct texture
   (`kris_4_burg_a.tga`).

2. The same model converted multiple times would sometimes get different texture assignments.

3. Some materials would always receive incorrect textures, regardless of how many times the
   conversion was run.

## Root Causes

After extensive investigation, we identified these key issues:

### Primary Root Cause

The fundamental issue was identified in `python3/lib/export.py` in the `copy_textures_for_export()` function.
During the GLTF export phase (which happens before the FBX export), textures were being copied with 
filenames that included both the material name and the texture name:

```python
# Original problematic code
target_filename = f"{material_name_clean}_{os.path.basename(source_path)}"
```

This created texture files with confusing names like `kristall_details_a_kristall_details_a.tga`, which
led to all of the subsequent issues during texture lookup and assignment.

### Secondary Contributing Factors

1. **Multiple Texture Directories**: The converter was maintaining textures in several locations:
   - `exports/fbx/<model_name>.fbm/` (correct textures)
   - `exports/gltf/textures/` (incorrect duplicate textures with names like `texture_name_texture_name.tga`)
   - `exports/fbx/textures/` (another potential location for incorrect textures)

2. **Material Suffix Handling**: Blender was not properly handling material names with numeric
   suffixes (like `.001`, `.248`, etc.) when matching them to textures.

3. **Texture Directory Priority**: Even though we were trying to only use the `.fbm` directory,
   Blender was still finding and using textures from other directories when the exact match
   wasn't found in `.fbm`.

## Solution Implemented

We've implemented a comprehensive solution with these key changes:

### 1. Fixed the Root Cause

- Modified `export.py` to correctly name texture files during export:
  ```python
  # Changed from this problematic code
  target_filename = f"{material_name_clean}_{os.path.basename(source_path)}"
  
  # To this fixed version
  target_filename = os.path.basename(source_path)
  ```
  This prevents the creation of duplicate textures with confusing names.

### 2. Directory Cleanup

- Created a `clean_texture_directories.py` script to remove ALL texture directories except
  for the `.fbm` directory, ensuring no conflicting textures remain.
- Modified `material_mapper.py` to delete multiple texture directories, not just the
  main `exports/fbx/textures` directory.

### 3. Material Name Matching Enhancement

- Improved the material name handling in `blender_script.py` to correctly extract base material
  names without numeric suffixes.
- Added support for matching both the full material name and the base name without suffixes.

### 4. Enforcing FBM Directory Usage

- Updated `blender_script.py` to STRICTLY use only textures from the `.fbm` directory
  when it exists, completely ignoring all other texture locations.
- Added clear logging indicating when only `.fbm` textures are being used.

### 5. Improved Mapping File Integration

- Enhanced the model-specific material mapping checks to handle base material names
  when matching to textures.
- Added better material-to-texture lookup mechanisms that prioritize exact matches.

### 6. Logging Improvements

- Added detailed logging for every stage of texture lookup and assignment.
- Enhanced diagnostic information for tracking troublesome textures and materials.

## How to Use the Solution

1. First, clean all texture directories to prevent any conflicts:
   ```
   python python3/clean_texture_directories.py
   ```

2. Then run the converter with mapping as usual:
   ```
   python python3/run_with_mapping.py path/to/model.3db
   ```

3. If you're still having issues, check the `blender_log.txt` file for detailed information
   about texture assignment decisions.

## Technical Details

### Key Changes in `blender_script.py`:

1. **Base Material Name Extraction**:
   ```python
   import re
   base_match = re.match(r'([a-zA-Z0-9_]+(?:_[a-zA-Z0-9_]+)*)(?:\.\d+)?$', material_clean)
   if base_match:
       base_material_name = base_match.group(1)
   ```

2. **Strict FBM-Only Mode**:
   ```python
   if texture_files:
       log("CRITICAL: Using ONLY textures from .fbm directory, ignoring all other directories")
       return texture_files
   ```

3. **Enhanced Matching Logic**:
   ```python
   if clean_mat_name == material_clean or (base_material_name and clean_mat_name == base_material_name):
       # Match found with either full name or base name
   ```

### Key Changes in `material_mapper.py`:

```python
texture_dirs_to_clear = [
    os.path.join("exports", "fbx", "textures"),    # FBX textures dir (deprecated)
    os.path.join("exports", "gltf", "textures"),   # GLTF textures dir (may contain wrong duplicates)
    os.path.join("textures")                       # Root textures dir (if exists)
]
```

## Conclusion

This solution eliminates the root causes of incorrect texture assignments by ensuring that:

1. Only one authoritative source of textures exists (the `.fbm` directory)
2. Material names are properly matched regardless of numeric suffixes
3. The texture assignment process is clearly logged and traceable

These changes maintain all existing functionality while fixing the texture assignment issues
that were occurring before.
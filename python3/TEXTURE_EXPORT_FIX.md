# Fixing Texture Export Issues in Diggles 3DB Converter

## Root Cause Identified

We identified the fundamental issue that was causing texture assignment problems in the FBX export:

The problem occurred in `python3/lib/export.py` where incorrect texture filenames were being generated
during the GLTF export phase, which is a precursor to the FBX export.

Specifically, in the `copy_textures_for_export()` function (lines 348-535), textures were being copied with names that
included both the material name and the texture name, like this:

```python
# Original problematic code
target_filename = f"{material_name_clean}_{os.path.basename(source_path)}"
```

This resulted in texture files with names such as:
- `kristall_details_a_kristall_details_a.tga` 
- `kris_4_burg_b_kris_4_burg_b.tga`

These duplicate-looking names caused confusion during the Blender texture assignment phase, resulting
in the wrong textures being assigned to materials, especially for materials with numeric suffixes
like `kris_4_burg_a.248`.

## Solution Implemented

We fixed this issue by modifying the texture filename generation to use just the original texture
filename without prepending the material name:

```python
# Fixed code
target_filename = os.path.basename(source_path)
```

This ensures that:

1. The texture files have their original, clean names (e.g., `kris_4_burg_a.tga`)
2. There's no confusion during texture lookup in the Blender phase
3. The material-to-texture mapping is clearer and more predictable

## Additional Cleanup

We also implemented several other improvements to ensure texture assignment works correctly:

1. We created a `clean_texture_directories.py` script to remove all the problematic texture directories
   that might contain textures with incorrect names.

2. We modified `material_mapper.py` to clean up additional texture directories, not just 
   `exports/fbx/textures` but also `exports/gltf/textures`.

3. We improved `blender_script.py` to properly handle material names with numeric suffixes and to
   strictly use only textures from the .fbm directory.

## How to Use

1. First, run the texture cleanup script to remove problematic texture directories:
   ```
   python python3/clean_texture_directories.py
   ```

2. Then run the converter with the fixed texture export logic:
   ```
   python python3/run_with_mapping.py path/to/model.3db
   ```

The resulting FBX model should now have correctly assigned textures, as the root cause of the
texture name confusion has been eliminated.

---

This solution provides a fundamental fix to the texture assignment issues by addressing the problem
at its source - the initial creation of incorrectly named texture files during the GLTF export phase.
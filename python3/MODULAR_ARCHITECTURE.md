# Modular Blender Script Architecture 

## Overview

The modular architecture for the Blender script provides a more organized, maintainable, and extensible solution for texture assignment in the Diggles 3DB converter. It specifically addresses issues with incorrect texture assignments and duplicate materials.

## Module Structure

The new architecture is organized into the following modules:

1. **logger.py** - Centralized logging system with timestamp and log levels
2. **config.py** - Configuration management including material-texture mappings
3. **material_cache.py** - Material caching to prevent duplicate materials
4. **material_manager.py** - Material creation and management
5. **get_texture_module.py** - Main texture matching algorithm
6. **texture_matcher.py** - Improved texture matching algorithms with fuzzy matching
7. **texture_finder.py** - File system searching for textures
8. **object_processor.py** - Object name parsing and information extraction
9. **hierarchy_builder.py** - Building proper FBX hierarchy

## Key Improvements

### 1. Texture Matching

The most significant problem was incorrect texture matching. The new architecture implements:

- Stricter string matching requiring 80% similarity threshold
- Special handling for known problematic cases (kris_/kristall_)
- Direct texture mappings for known problematic materials
- Fuzzy string matching with improved algorithm

### 2. Material Caching

To prevent the creation of duplicate materials, we've implemented:

- Global material cache keyed by material name and texture path
- Base material name extraction to handle numeric suffixes
- Reuse of existing materials when the same texture is applied

### 3. Diagnostic Tools

New diagnostic tools help identify and fix texture issues:

- **texture_matcher.py** - Tests material-to-texture matching
- **kris_texture_analyzer.py** - Specifically analyzes kris_/kristall_ conflicts

## Usage

The current system supports both the old and new Blender scripts:

- The original `blender_script.py` is still available
- The new script is in `new_blender_script.py` 
- `export_fbx_binary.py` detects and uses the new script automatically if available

## Implementation Details

### Texture Matching Algorithm

The new texture matching algorithm works in this order:

1. Check for special case materials using PROBLEM_MATERIAL_MAPPINGS
2. Try exact text match between material name and texture name
3. Apply fuzzy matching with a similarity threshold of 0.8
4. Check for strong prefix matches
5. Fall back to model-specific matches based on link position
6. Use model name matching for generic parts

### Material Caching

The material cache prevents creating duplicate materials by:

1. Creating a unique key for each material-texture combination
2. Checking the cache before creating new materials
3. Extracting base material names to handle .001, .002 suffixes
4. Defining a proper equality test for materials

## Testing and Verification

To test the new implementation:

1. Run the diagnostic tool on problematic models:
   ```
   python python3/texture_matcher.py --material kris_4_burg_a
   ```

2. Analyze specific issues with kris_ vs kristall_ textures:
   ```
   python python3/kris_texture_analyzer.py --test kris_4_burg_a
   ```

3. Convert models using both the old and new systems:
   ```
   # Old system
   python python3/run_with_mapping.py path/to/model.3db
   
   # New system (automatically selected)
   python python3/run_with_mapping.py path/to/model.3db 
   ```

## Further Development

Future improvements could include:

1. Expanding the PROBLEM_MATERIAL_MAPPINGS with additional problematic cases
2. Implementing machine learning for better texture matching
3. Creating a user interface for manual texture assignment
4. Adding material preview rendering for verification
5. Creating an automated test suite for all models

## How It Works

1. When you run `run_with_mapping.py`, it calls `export_fbx_binary.py`
2. `export_fbx_binary.py` automatically detects and uses `new_blender_script.py` if available
3. `new_blender_script.py` loads modules from the `blender_modules` directory
4. The modular system processes the model with improved texture matching
5. The resulting FBX contains the correct textures mapped to the right materials
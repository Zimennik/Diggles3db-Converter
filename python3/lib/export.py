import os
import struct
import operator
import shutil
from gltflib import (
    GLTF, GLTFModel, Asset, Scene, Node, Mesh, Primitive, Attributes, Buffer, BufferView, Accessor, AccessorType,
    BufferTarget, ComponentType, GLBResource, FileResource)

from lib.parse_3db import Model
from typing import List, Dict, Tuple, Optional

def transform_point(p: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Transform a point from the .3db coordinate system to a more standard one."""
    scale = 100
    result = ((p[0] - 0.5) * scale, (p[1] - 0.5) * scale, (p[2] - 0.5) * scale)
    return result

def extract_texture_filename(texture_path: str) -> str:
    """Extract just the filename from a texture path."""
    # Ensure texture_path is a string
    if not isinstance(texture_path, str):
        try:
            texture_path = texture_path.decode('utf-8')
        except (AttributeError, UnicodeDecodeError):
            print(f"Warning: Could not decode texture path: {texture_path}")
            return ""
    
    return os.path.basename(texture_path)

def get_texture_path(texture_name: str) -> Optional[str]:
    """Get the full path to a texture file."""
    # Ensure texture_name is a string
    if not isinstance(texture_name, str):
        try:
            texture_name = texture_name.decode('utf-8')
        except (AttributeError, UnicodeDecodeError):
            print(f"Warning: Could not decode texture name: {texture_name}")
            return None
    
    # Print debug information
    print(f"Looking for texture: {texture_name}")
    
    # Try common case-specific filenames first before any general search
    if texture_name.lower().endswith("character_zbaby_a.tga") or texture_name.lower() == "character_zbaby_a.tga":
        # Direct check for known baby texture locations
        specific_baby_paths = [
            os.path.join('assets', 'textures', 'm128', 'Character_ZBaby_a.tga'),
            os.path.join('assets', 'textures', 'm064', 'Character_ZBaby_a.tga'),
            os.path.join('assets', 'textures', 'Gray', 'Character_ZBaby_a.tga')
        ]
        
        for path in specific_baby_paths:
            if os.path.exists(path):
                print(f"Found baby texture at hardcoded path: {path}")
                return path
    
    # Extract just the filename without path
    texture_name = os.path.basename(texture_name)
    base_name = os.path.splitext(texture_name)[0]
    
    # Build a list of all potential search directories
    search_dirs = [
        # Core asset directories
        os.path.join('assets', 'textures', 'm256'),
        os.path.join('assets', 'textures', 'm128'),
        os.path.join('assets', 'textures', 'm064'),
        os.path.join('assets', 'textures', 'm032'),
        os.path.join('assets', 'textures', 'ClassIcons'),
        os.path.join('assets', 'textures', 'Gray'),
        os.path.join('assets', 'textures', 'Misc'),
        os.path.join('assets', 'textures'),
        
        # Parent directories (for different working directory cases)
        os.path.join('..', 'assets', 'textures', 'm256'),
        os.path.join('..', 'assets', 'textures', 'm128'),
        os.path.join('..', 'assets', 'textures', 'm064'),
        os.path.join('..', 'assets', 'textures', 'm032'),
        os.path.join('..', 'assets', 'textures', 'ClassIcons'),
        os.path.join('..', 'assets', 'textures', 'Gray'),
        os.path.join('..', 'assets', 'textures', 'Misc'),
        os.path.join('..', 'assets', 'textures'),
        
        # Export directories
        os.path.join('exports', 'fbx', 'textures'),
        os.path.join('exports', 'gltf', 'textures')
    ]
    
    # Extensions to try
    extensions = ['.tga', '.png', '.jpg', '.jpeg', '.bmp']
    
    # Get the extension of the original file (if any)
    original_ext = os.path.splitext(texture_name)[1].lower()
    if original_ext:
        # Put the original extension first in the list to try
        extensions = [original_ext] + [ext for ext in extensions if ext != original_ext]
    
    # Try to find the texture in any of the search directories with any extension
    for dir_path in search_dirs:
        if not os.path.exists(dir_path):
            continue
            
        # Check if the directory exists and list all files to check case-insensitive
        try:
            dir_contents = os.listdir(dir_path)
            # Check if any file in the directory matches (case-insensitive)
            for file in dir_contents:
                if file.lower() == texture_name.lower():
                    full_path = os.path.join(dir_path, file)
                    print(f"Found texture with exact match (case-insensitive): {full_path}")
                    return full_path
                
                # Also check for basename match with any extension
                if os.path.splitext(file)[0].lower() == base_name.lower():
                    full_path = os.path.join(dir_path, file)
                    print(f"Found texture with basename match: {full_path}")
                    return full_path
        except Exception as e:
            print(f"Error listing directory {dir_path}: {str(e)}")
            
        # First try the exact filename
        full_path = os.path.join(dir_path, texture_name)
        if os.path.exists(full_path):
            print(f"Found texture with exact path: {full_path}")
            return full_path
            
        # Try base name with different extensions
        for ext in extensions:
            # Try with original case
            alt_path = os.path.join(dir_path, base_name + ext)
            if os.path.exists(alt_path):
                print(f"Found texture with extension: {alt_path}")
                return alt_path
            
            # Try with capital first letter (Character_ZBaby_a.tga)
            if not base_name[0].isupper() and len(base_name) > 1:
                cap_path = os.path.join(dir_path, base_name[0].upper() + base_name[1:] + ext)
                if os.path.exists(cap_path):
                    print(f"Found texture with capital first letter: {cap_path}")
                    return cap_path
            
            # Try with lowercase
            alt_path_lower = os.path.join(dir_path, base_name.lower() + ext)
            if os.path.exists(alt_path_lower) and alt_path_lower != alt_path:
                print(f"Found texture with lowercase: {alt_path_lower}")
                return alt_path_lower
                
            # Try with uppercase
            alt_path_upper = os.path.join(dir_path, base_name.upper() + ext)
            if os.path.exists(alt_path_upper) and alt_path_upper != alt_path:
                print(f"Found texture with uppercase: {alt_path_upper}")
                return alt_path_upper
                
            # Also try with 'Character_' prefix for character textures
            if "zbaby" in base_name.lower() and not base_name.lower().startswith("character_"):
                # Try both Character_ZBaby and Character_zbaby
                variations = [
                    f"Character_{base_name}",
                    f"Character_{base_name.lower()}",
                    f"character_{base_name}",
                    f"character_{base_name.lower()}"
                ]
                
                for var in variations:
                    char_path = os.path.join(dir_path, var + ext)
                    if os.path.exists(char_path):
                        print(f"Found texture with Character_ prefix: {char_path}")
                        return char_path
                    
            # Try without 'Character_' prefix
            if base_name.lower().startswith("character_"):
                no_prefix = base_name[len("Character_"):]
                variations = [
                    no_prefix,
                    no_prefix.lower(),
                    no_prefix[0].upper() + no_prefix[1:] if len(no_prefix) > 1 else no_prefix.upper()
                ]
                
                for var in variations:
                    no_prefix_path = os.path.join(dir_path, var + ext)
                    if os.path.exists(no_prefix_path):
                        print(f"Found texture without Character_ prefix: {no_prefix_path}")
                        return no_prefix_path
    
    # If we get here, the texture wasn't found, report error with search paths
    print(f"Warning: Texture not found for {texture_name}")
    print(f"Searched in: {search_dirs}")
    return None

def clean_material_name(name):
    """
    Clean up material names by removing bytes prefixes and other unwanted characters.
    This ensures texture paths are properly formatted.
    """
    # Convert to string if it's bytes
    if isinstance(name, bytes):
        try:
            name = name.decode('utf-8', errors='ignore')
        except:
            name = str(name)
    else:
        name = str(name)
    
    # Remove the bytes prefix notation if present
    if name.startswith("b'") and name.endswith("'"):
        name = name[2:-1]
    
    # Remove any remaining quotes
    name = name.replace("'", "").replace('"', "")
    
    return name

def find_matching_textures(search_term: str, exact=False) -> list:
    """Find textures that match a search term in assets/textures directories."""
    matching_textures = []
    
    # Order matters - higher resolution first
    search_directories = [
        # High resolution textures first
        os.path.join('assets', 'textures', 'm256'),
        
        # Medium resolution textures next
        os.path.join('assets', 'textures', 'm128'),
        
        # Low resolution textures
        os.path.join('assets', 'textures', 'm064'),
        os.path.join('assets', 'textures', 'm032'),
        
        # Special directories
        os.path.join('assets', 'textures', 'Gray'),
        os.path.join('assets', 'textures', 'ClassIcons'),
        
        # Main texture directory last
        os.path.join('assets', 'textures'),
    ]
    
    # Ensure search_term is lowercase for case-insensitive comparison
    search_term = search_term.lower()
    
    # Process each directory in order
    textures_by_resolution = {
        'm256': [],
        'm128': [],
        'm064': [],
        'other': []
    }
    
    for directory in search_directories:
        if not os.path.exists(directory):
            continue
            
        try:
            for filename in os.listdir(directory):
                if not filename.lower().endswith(('.tga', '.png', '.jpg')):
                    continue
                    
                filepath = os.path.join(directory, filename)
                filename_lower = filename.lower()
                
                # Check if the filename matches the search criteria
                matches = False
                if exact and search_term == filename_lower.split('.')[0]:
                    # Exact match with the filename without extension
                    matches = True
                elif not exact and search_term in filename_lower:
                    # Partial match anywhere in the filename
                    matches = True
                
                if matches:
                    # Determine resolution category
                    if 'm256' in directory:
                        textures_by_resolution['m256'].append(filepath)
                    elif 'm128' in directory:
                        textures_by_resolution['m128'].append(filepath)
                    elif 'm064' in directory:
                        textures_by_resolution['m064'].append(filepath)
                    else:
                        textures_by_resolution['other'].append(filepath)
        except Exception as e:
            print(f"Error reading directory {directory}: {str(e)}")
    
    # Combine results in order of resolution priority
    for res in ['m256', 'm128', 'm064', 'other']:
        # Sort by filename length (shorter names are often better matches)
        textures_by_resolution[res].sort(key=lambda x: len(os.path.basename(x)))
        matching_textures.extend(textures_by_resolution[res])
    
    return matching_textures

def analyze_material_usage(model: Model) -> Dict[int, Dict]:
    """
    Analyze how materials are used across mesh links in the model.
    
    Returns a dictionary mapping material indices to dictionaries with usage information:
    - mesh_links: set of (mesh_index, link_index) tuples
    - link_positions: set of link positions where the material is used
    - animations: set of animation indices using this material
    """
    material_usage = {}
    
    # Initialize dictionaries for each material
    for i in range(len(model.materials)):
        material_usage[i] = {
            "mesh_links": set(),
            "link_positions": set(), 
            "animations": set()
        }
    
    # Scan all meshes and links
    for mesh_idx, mesh in enumerate(model.meshes):
        for link_idx, link in enumerate(mesh.links):
            # Add this mesh and link to the set for this material
            if link.material < len(model.materials):
                material_usage[link.material]["mesh_links"].add((mesh_idx, link_idx))
                material_usage[link.material]["link_positions"].add(link_idx)
            else:
                print(f"Warning: Mesh {mesh_idx}, Link {link_idx} references invalid material {link.material}")
    
    # Track which animations use which materials
    for anim_idx, anim in enumerate(model.animations):
        for mesh_idx in anim.meshes:
            if mesh_idx < len(model.meshes):
                mesh = model.meshes[mesh_idx]
                for link_idx, link in enumerate(mesh.links):
                    if link.material < len(model.materials):
                        material_usage[link.material]["animations"].add(anim_idx)
    
    # Print summary of material usage
    print("\nMaterial usage summary:")
    for mat_idx, usage in material_usage.items():
        if mat_idx < len(model.materials):
            mat_name = model.materials[mat_idx].name
            if isinstance(mat_name, bytes):
                try:
                    mat_name = mat_name.decode('utf-8', errors='ignore')
                except:
                    mat_name = str(mat_name)
            
            mesh_links_count = len(usage["mesh_links"])
            link_positions = sorted(list(usage["link_positions"]))
            anims_count = len(usage["animations"])
            
            print(f"Material {mat_idx}: {mat_name}")
            print(f"  Used in {mesh_links_count} mesh links at positions {link_positions}")
            print(f"  Used by {anims_count} animations")
    
    return material_usage

def copy_textures_for_export(model: Model, export_dir: str) -> Dict[str, str]:
    """Copy textures to the export directory and return a mapping of material names to texture paths."""
    texture_export_dir = os.path.join(export_dir, 'textures')
    os.makedirs(texture_export_dir, exist_ok=True)
    
    # Debug information
    print(f"Copying textures to: {texture_export_dir}")
    
    # Create a set to track processed textures to avoid duplication
    processed_textures = set()
    
    # Extract model name for better material matching
    model_name = ""
    if model.name:
        if isinstance(model.name, bytes):
            try:
                model_name = model.name.decode('utf-8', errors='ignore').lower()
            except:
                model_name = str(model.name).lower()
        else:
            model_name = str(model.name).lower()
    
    # Remove file extension and path from model name
    model_basename = os.path.splitext(os.path.basename(model_name))[0].lower()
    print(f"Using model basename for texture matching: {model_basename}")
    
    # Analyze how materials are used across the model
    # This gives us information about which link positions typically use which materials
    material_usage = analyze_material_usage(model)
    
    # Create a mapping from link positions to typical material usage
    # This helps us make smarter decisions for more complex models
    link_position_map = {}
    for mat_idx, usage in material_usage.items():
        if mat_idx < len(model.materials):
            for link_pos in usage["link_positions"]:
                if link_pos not in link_position_map:
                    link_position_map[link_pos] = []
                link_position_map[link_pos].append(mat_idx)
    
    # Print link position mapping for debugging
    print("\nLink position to material mapping:")
    for link_pos, mat_indices in sorted(link_position_map.items()):
        material_names = []
        for idx in mat_indices[:3]:  # Limit to first 3 materials per position
            mat_name = model.materials[idx].name
            if isinstance(mat_name, bytes):
                try:
                    mat_name = mat_name.decode('utf-8', errors='ignore')
                except:
                    mat_name = str(mat_name)
            material_names.append(mat_name)
        
        print(f"  Link position {link_pos}: {', '.join(material_names)}{' and more...' if len(mat_indices) > 3 else ''}")
    
    # Now we'll use both material usage and link position information to make smarter texture assignments
    
    texture_map = {}
    for i, material in enumerate(model.materials):
        # Debug the material info
        print(f"Processing material {i}: {material.name}, path: {material.path}")
        
        # Get texture name from material path
        texture_name = extract_texture_filename(material.path)
        
        # Clean material name for use in filenames
        material_name_clean = clean_material_name(material.name)
        material_name_lower = material_name_clean.lower()
        
        # Generate a material name for the map (keep original for the key)
        material_name_str = ""
        if isinstance(material.name, bytes):
            try:
                material_name_str = material.name.decode('utf-8', errors='ignore')
            except Exception:
                material_name_str = str(material.name)
        else:
            material_name_str = str(material.name)
        
        # Try to find textures based on material and model information
        # This is a prioritized list of search strategies
        source_path = None
        
        # Strategy 1: Look for the exact texture mentioned in the material path
        if texture_name:
            direct_path = get_texture_path(texture_name)
            if direct_path and os.path.exists(direct_path):
                source_path = direct_path
                print(f"Found texture referenced by material path: {source_path}")
        
        # Strategy 2: Try to find exact match for the material name
        if not source_path:
            # First try to find an exact match for the material name
            exact_matches = find_matching_textures(material_name_lower, exact=True)
            if exact_matches:
                source_path = exact_matches[0]
                # If this is a Gray texture, but we can find a higher-res version in other directories
                if 'Gray' in source_path or 'm064' in source_path or 'm032' in source_path:
                    # Try to find a better version
                    higher_res_matches = find_matching_textures(material_name_lower, exact=True)
                    if higher_res_matches and higher_res_matches[0] != source_path:
                        # Found a potentially higher resolution version
                        if ('m256' in higher_res_matches[0] or 'm128' in higher_res_matches[0]):
                            source_path = higher_res_matches[0]
                            print(f"Found higher quality exact match: {source_path}")
                        
                print(f"Found exact match for material name: {source_path}")
        
        # Strategy 3: Try to find textures that match both model name and material name 
        if not source_path and model_basename:
            combined_search = f"{model_basename}_{material_name_lower}"
            matching_textures = find_matching_textures(combined_search)
            if matching_textures:
                source_path = matching_textures[0]
                print(f"Found texture matching model+material: {source_path}")
        
        # Strategy 4: Try character textures with model name
        if not source_path and model_basename:
            character_search = f"character_{model_basename}"
            matching_textures = find_matching_textures(character_search)
            if matching_textures:
                source_path = matching_textures[0]
                print(f"Found character texture with model name: {source_path}")

        # Strategy 5: Try for material name in textures
        if not source_path:
            partial_matches = find_matching_textures(material_name_lower)
            if partial_matches:
                source_path = partial_matches[0]
                print(f"Found partial match for material name: {source_path}")
                
        # Strategy 6: As a last resort, try the model name alone
        if not source_path and model_basename:
            model_matches = find_matching_textures(model_basename)
            if model_matches:
                source_path = model_matches[0]
                print(f"Found texture matching model name: {source_path}")
                
        # If we still don't have a texture but we have a path, log it clearly
        if not source_path and texture_name:
            print(f"WARNING: Could not find texture for material {material.name} with path {texture_name}")
            print(f"This material is used in {len(material_usage[i])} mesh links")
            
            # Try using another texture from the same model as a fallback
            for other_mat_idx, other_mat in enumerate(model.materials):
                if other_mat_idx != i and other_mat_idx in texture_map:
                    source_path = texture_map[other_mat.name].replace('textures/', '')
                    source_path = os.path.join('textures', source_path)
                    print(f"Using another material's texture as fallback: {source_path}")
                    break
        
        if source_path and os.path.exists(source_path):
            # Use cleaned material name for the target filename
            target_filename = os.path.basename(source_path)
            target_path = os.path.join(texture_export_dir, target_filename)
            
            # Check if we've already processed this texture to avoid duplicates
            if source_path not in processed_textures:
                print(f"Copying texture: {source_path} -> {target_path}")
                shutil.copy2(source_path, target_path)
                processed_textures.add(source_path)
            else:
                print(f"Skipping already copied texture: {source_path}")
            
            # Store path that will be used for material referencing
            texture_map[material.name] = os.path.join('textures', target_filename)
            print(f"Added to texture map: {material.name} -> {texture_map[material.name]}")
        else:
            print(f"Warning: Texture not found for material {material.name}: {texture_name}")
            
            # Try search by material name if texture name search failed
            if not source_path and material.name:
                alt_source_path = get_texture_path(material_name_clean)
                if alt_source_path and os.path.exists(alt_source_path):
                    target_filename = os.path.basename(alt_source_path)
                    target_path = os.path.join(texture_export_dir, target_filename)
                    
                    # Check if we've already processed this texture
                    if alt_source_path not in processed_textures:
                        print(f"Found texture by material name: {alt_source_path} -> {target_path}")
                        shutil.copy2(alt_source_path, target_path)
                        processed_textures.add(alt_source_path)
                    else:
                        print(f"Skipping already copied texture by material name: {alt_source_path}")
                    
                    texture_map[material.name] = os.path.join('textures', target_filename)
    
    return texture_map

def build_vertices_array(triangles: List[int], points: List[Tuple[float, float, float]]) -> List[Tuple[float, float, float]]:
    """Build an array of vertices from triangles and points."""
    vertices = [points[index] for index in triangles]
    return vertices

def export_to_gltf(model: Model, output_path: str = 'exports/gltf/model.gltf'):
    """Export the model to glTF format with animations."""
    # Create export directory if it doesn't exist
    export_dir = os.path.dirname(output_path)
    os.makedirs(export_dir, exist_ok=True)
    
    # Copy textures for export
    texture_map = copy_textures_for_export(model, export_dir)
    
    nodes = []
    meshes = []
    accessors = []
    animations = []
    animation_channels = []
    animation_samplers = []
    materials = []  # We'll store materials here
    
    # Create a material for each material in the model
    for i, material in enumerate(model.materials):
        material_name = ""
        if isinstance(material.name, bytes):
            try:
                material_name = material.name.decode('utf-8', errors='ignore')
            except:
                material_name = str(material.name)
        else:
            material_name = str(material.name)
        
        # Create a material with extras for the original index
        materials.append({
            "name": f"material_{i:02d}_{material_name}",
            "extras": {
                "original_index": i,
                "original_name": material_name
            }
        })

    vertex_byte_array = bytearray()
    index_byte_array = bytearray()
    
    # Process all animations
    # Создаем словарь для отслеживания анимаций с одинаковыми именами
    anim_name_counts = {}
    for animation in model.animations:
        anim_name = animation.name
        if isinstance(anim_name, bytes):
            try:
                anim_name = anim_name.decode('utf-8', errors='ignore')
            except:
                anim_name = str(anim_name)
        
        if anim_name in anim_name_counts:
            anim_name_counts[anim_name] += 1
        else:
            anim_name_counts[anim_name] = 1
    
    # Выводим список анимаций с одинаковыми именами для отладки
    duplicate_names = [name for name, count in anim_name_counts.items() if count > 1]
    if duplicate_names:
        print(f"WARNING: Found duplicate animation names: {duplicate_names}")
    
    # Используем счетчик для уникализации имен
    anim_name_indexer = {}
    
    # Process all animations
    for anim_idx, animation in enumerate(model.animations):
        # Обновляем счетчик для текущего имени анимации
        anim_name = animation.name
        if isinstance(anim_name, bytes):
            try:
                anim_name = anim_name.decode('utf-8', errors='ignore')
            except:
                anim_name = str(anim_name)
                
        if anim_name not in anim_name_indexer:
            anim_name_indexer[anim_name] = 0
        else:
            anim_name_indexer[anim_name] += 1
        # For each mesh in the animation
        for frame_idx, mesh_idx in enumerate(animation.meshes):
            if mesh_idx >= len(model.meshes):
                print(f"Warning: Mesh index {mesh_idx} out of range in animation {animation.name}")
                continue
            
            mesh = model.meshes[mesh_idx]
            
            # Process each mesh link
            for link_idx, mesh_link in enumerate(mesh.links):
                try:
                    triangles = model.triangle_data[mesh_link.triangles]
                    points = model.points_data[mesh_link.points]
                    texture_coordinates = model.texture_coordinates_data[mesh_link.texture_coordinates]
                    
                    # Проверяем наличие данных
                    if not points:
                        print(f"Warning: Empty points data in {animation.name}_frame{frame_idx}_link{link_idx}")
                        continue
                    
                    if not triangles:
                        print(f"Warning: Empty triangles data in {animation.name}_frame{frame_idx}_link{link_idx}")
                        continue
                    
                    vertices = [transform_point(p) for p in points]
                    
                    # Проверяем соответствие UV координат и вершин
                    if len(texture_coordinates) != len(vertices):
                        print(f"Warning: Texture coordinates count ({len(texture_coordinates)}) doesn't match vertices count ({len(vertices)}) in {animation.name}_frame{frame_idx}_link{link_idx}")
                        # Создаем заглушку для текстурных координат, если их недостаточно
                        if len(texture_coordinates) < len(vertices):
                            texture_coordinates.extend([(0.0, 0.0)] * (len(vertices) - len(texture_coordinates)))
                        else:
                            texture_coordinates = texture_coordinates[:len(vertices)]
                    
                    vertex_data_start = len(vertex_byte_array)
                    
                    # Финальная проверка на пустые данные
                    if not vertices:
                        print(f"Warning: Empty mesh found in {animation.name}_frame{frame_idx}_link{link_idx}")
                        # Пропускаем создание этого меша
                        continue
                except Exception as e:
                    print(f"Error processing mesh: {animation.name}_frame{frame_idx}_link{link_idx}: {str(e)}")
                    continue
                
                for vertex in vertices:
                    for value in vertex:
                        vertex_byte_array.extend(struct.pack('f', value))

                mins = [min([operator.itemgetter(i)(vertex) for vertex in vertices]) for i in range(3)]
                maxs = [max([operator.itemgetter(i)(vertex) for vertex in vertices]) for i in range(3)]

                texture_coords_start = len(vertex_byte_array)
                for t in texture_coordinates:
                    for value in t:
                        vertex_byte_array.extend(struct.pack('f', value))

                indices_start = len(index_byte_array)
                for index in triangles:
                    index_byte_array.extend(struct.pack('I', index))

                position_index = len(accessors)
                accessors.append(Accessor(
                    bufferView=0, 
                    byteOffset=vertex_data_start, 
                    componentType=ComponentType.FLOAT.value, 
                    count=len(vertices),
                    type=AccessorType.VEC3.value, 
                    min=mins, 
                    max=maxs
                ))

                texture_coords_index = len(accessors)
                accessors.append(Accessor(
                    bufferView=0, 
                    byteOffset=texture_coords_start, 
                    componentType=ComponentType.FLOAT.value, 
                    count=len(texture_coordinates),
                    type=AccessorType.VEC2.value
                ))

                indices_index = len(accessors)
                accessors.append(Accessor(
                    bufferView=1, 
                    byteOffset=indices_start, 
                    componentType=ComponentType.UNSIGNED_INT.value, 
                    count=len(triangles),
                    type=AccessorType.SCALAR.value
                ))

                # Get material index for this link
                material_index = mesh_link.material
                if material_index >= len(model.materials):
                    print(f"Warning: Invalid material index {material_index} in {animation.name}_frame{frame_idx}_link{link_idx}")
                    material_index = 0  # Fallback to first material
                
                mesh_index = len(meshes)
                meshes.append(Mesh(primitives=[
                    Primitive(
                        attributes=Attributes(
                            POSITION=position_index, 
                            TEXCOORD_0=texture_coords_index
                        ), 
                        indices=indices_index,
                        material=material_index  # Add material reference here
                    )
                ]))
                
                # Get material name for this material index
                material_name = ""
                if material_index < len(model.materials):
                    material = model.materials[material_index]
                    if isinstance(material.name, bytes):
                        try:
                            material_name = material.name.decode('utf-8', errors='ignore')
                        except:
                            material_name = str(material.name)
                    else:
                        material_name = str(material.name)
                    
                    # Clean up the material name
                    material_name = material_name.replace("b'", "").replace("'", "").strip()
                
                # Create a node with both animation structure and material name
                node_index = len(nodes)
                # Combine animation structure with material name to preserve both
                # Format: animation_name_frameXX_linkYY_MaterialName
                # This preserves the animation structure while also including material info
                anim_name = animation.name
                if isinstance(anim_name, bytes):
                    try:
                        anim_name = anim_name.decode('utf-8', errors='ignore')
                    except:
                        anim_name = str(anim_name)
                
                # Сохраняем структуру anim_name/frame_XX/material_name
                # Добавляем индекс анимации к имени, чтобы избежать дублирования
                node_name = f"{anim_name}_{anim_idx:02d}_frame{frame_idx:02d}_{material_name}"
                
                
                # Clean up the name to avoid any problematic characters
                node_name = node_name.replace("b'", "").replace("'", "").strip()
                nodes.append(Node(mesh=mesh_index, name=node_name))
    
    # Create the glTF model
    vertices_bin_path = 'vertices.bin'
    indices_bin_path = 'indices.bin'
    
    gltf_model = GLTFModel(
        asset=Asset(version='2.0'),
        scenes=[Scene(nodes=[i for i in range(len(nodes))])],
        nodes=nodes,
        buffers=[
            Buffer(byteLength=len(vertex_byte_array), uri=vertices_bin_path), 
            Buffer(byteLength=len(index_byte_array), uri=indices_bin_path)
        ],
        bufferViews=[
            BufferView(buffer=0, byteOffset=0, byteLength=len(vertex_byte_array), target=BufferTarget.ARRAY_BUFFER.value),
            BufferView(buffer=1, byteOffset=0, byteLength=len(index_byte_array), target=BufferTarget.ELEMENT_ARRAY_BUFFER.value)
        ],
        accessors=accessors,
        meshes=meshes,
        materials=materials  # Add materials to the model
    )

    # Create the glTF object with resources
    vertices_bin_full_path = os.path.join(export_dir, vertices_bin_path)
    indices_bin_full_path = os.path.join(export_dir, indices_bin_path)
    
    gltf = GLTF(
        model=gltf_model, 
        resources=[
            FileResource(vertices_bin_path, data=vertex_byte_array),
            FileResource(indices_bin_path, data=index_byte_array)
        ]
    )
    
    # Export the glTF file
    gltf.export(output_path)
    print(f'Exported glTF model to {output_path}')
    print(f'Exported vertex data to {os.path.join(export_dir, vertices_bin_path)}')
    print(f'Exported index data to {os.path.join(export_dir, indices_bin_path)}')

import os
import shutil
import struct
import numpy as np
from typing import List, Dict, Tuple, Optional
from PIL import Image
from lib.parse_3db import Model, Animation, Mesh, MeshLink

def transform_point(p: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Transform a point from the .3db coordinate system to a more standard one."""
    scale = 100
    result = ((p[0] - 0.5) * scale, (p[1] - 0.5) * scale, (p[2] - 0.5) * scale)
    return result

def extract_texture_filename(texture_path):
    """Extract just the filename from a texture path."""
    # Handle bytes paths
    if isinstance(texture_path, bytes):
        try:
            # Split on backslashes and get the last part
            parts = texture_path.split(b'\\')
            if parts and parts[-1]:
                return parts[-1].decode('utf-8', errors='replace')
            return ""
        except Exception as e:
            print(f"Error extracting filename from bytes: {e}")
            return ""
    
    # Handle string paths
    if isinstance(texture_path, str):
        parts = texture_path.replace('\\\\', '\\').split('\\')
        return parts[-1] if parts else ""
    
    return ""

def get_texture_path(texture_name):
    """Get the full path to a texture file."""
    # Handle bytes paths
    if isinstance(texture_name, bytes):
        try:
            filename = extract_texture_filename(texture_name)
        except Exception as e:
            print(f"Warning: Could not decode texture name: {texture_name}, Error: {e}")
            return None
    else:
        filename = texture_name
    
    # Try to find the texture file with different extensions
    base_name = os.path.splitext(filename)[0]
    
    # Check in the specified texture directories
    search_dirs = [
        os.path.join('assets', 'textures', 'm256'),
        os.path.join('assets', 'textures'),
        os.path.join('..', 'assets', 'textures', 'm256'),
        os.path.join('..', 'assets', 'textures')
    ]
    
    # Try different extensions
    extensions = ['.tga', '.png', '.jpg', '.jpeg']
    
    # First try original filename
    for search_dir in search_dirs:
        path = os.path.join(search_dir, filename)
        if os.path.exists(path):
            return path
            
    # Then try with different extensions
    for search_dir in search_dirs:
        for ext in extensions:
            path = os.path.join(search_dir, base_name + ext)
            if os.path.exists(path):
                return path
    
    # If texture not found, return None
    print(f"Warning: Texture not found for {filename}")
    return None

def copy_textures_for_export(model, export_dir):
    """Copy textures to the export directory and return a mapping of material names to texture paths."""
    texture_export_dir = os.path.join(export_dir, 'textures')
    os.makedirs(texture_export_dir, exist_ok=True)
    
    texture_map = {}
    for i, material in enumerate(model.materials):
        # Улучшенное извлечение имени файла
        if isinstance(material.path, bytes):
            parts = material.path.split(b'\\')
            texture_name = parts[-1].decode('utf-8', errors='replace') if parts else ""
        else:
            texture_name = os.path.basename(material.path)
        
        # Ищем текстуру в нескольких местах и с разными расширениями
        base_name = os.path.splitext(texture_name)[0]
        source_path = None
        
        # Проверяем разные папки и расширения
        search_dirs = [
            os.path.join('assets', 'textures', 'm256'),
            os.path.join('assets', 'textures'),
            os.path.join('..', 'assets', 'textures', 'm256'),
            os.path.join('..', 'assets', 'textures')
        ]
        extensions = ['.tga', '.png', '.jpg', '.jpeg']
        
        # Сначала пробуем оригинальное имя
        for dir_path in search_dirs:
            path = os.path.join(dir_path, texture_name)
            if os.path.exists(path):
                source_path = path
                break
        
        # Если не нашли, пробуем с разными расширениями
        if not source_path:
            for dir_path in search_dirs:
                for ext in extensions:
                    path = os.path.join(dir_path, base_name + ext)
                    if os.path.exists(path):
                        source_path = path
                        break
                if source_path:
                    break
        
        if source_path and os.path.exists(source_path):
            # Создаем уникальное имя в target
            material_name = material.name.decode('utf-8', errors='replace') if isinstance(material.name, bytes) else material.name
            # Use only original filename to prevent issues with duplicate names
            target_filename = os.path.basename(source_path)
            target_path = os.path.join(texture_export_dir, target_filename)
            
            # Копируем файл и добавляем в map
            print(f"Copying texture: {source_path} -> {target_path}")
            shutil.copy2(source_path, target_path)
            texture_map[material_name] = os.path.join('textures', target_filename)
        else:
            print(f"Warning: Texture not found for material {material.name}: {texture_name}")
            print(f"Searched in: {search_dirs}")
    
    return texture_map

def create_fbx_ascii(model: Model, output_path: str) -> None:
    """
    Create an FBX ASCII file from the model.
    
    This is a simplified implementation that creates a basic FBX ASCII file.
    For a more complete implementation, you would need to use the FBX SDK.
    """
    # Create export directory if it doesn't exist
    export_dir = os.path.dirname(output_path)
    os.makedirs(export_dir, exist_ok=True)
    
    # Copy textures and get texture mapping
    texture_map = copy_textures_for_export(model, export_dir)
    
    # Open the output file
    with open(output_path, 'w') as f:
        # Write FBX header
        f.write("; FBX 7.3.0 project file\n")
        f.write("; Created by Python 3db to FBX converter\n\n")
        
        # Write FBX version info
        f.write("FBXHeaderExtension:  {\n")
        f.write("    FBXHeaderVersion: 1003\n")
        f.write("    FBXVersion: 7300\n")
        f.write("}\n\n")
        
        # Write global settings
        f.write("GlobalSettings:  {\n")
        f.write("    Version: 1000\n")
        f.write("    Properties70:  {\n")
        f.write("        P: \"UpAxis\", \"int\", \"Integer\", \"\", 1\n")
        f.write("        P: \"UpAxisSign\", \"int\", \"Integer\", \"\", 1\n")
        f.write("        P: \"FrontAxis\", \"int\", \"Integer\", \"\", 2\n")
        f.write("        P: \"FrontAxisSign\", \"int\", \"Integer\", \"\", 1\n")
        f.write("        P: \"CoordAxis\", \"int\", \"Integer\", \"\", 0\n")
        f.write("        P: \"CoordAxisSign\", \"int\", \"Integer\", \"\", 1\n")
        f.write("        P: \"OriginalUpAxis\", \"int\", \"Integer\", \"\", 1\n")
        f.write("        P: \"OriginalUpAxisSign\", \"int\", \"Integer\", \"\", 1\n")
        f.write("    }\n")
        f.write("}\n\n")
        
        # Write objects section
        f.write("Objects:  {\n")
        
        # Write materials
        for i, material in enumerate(model.materials):
            f.write(f"    Material: {1000 + i}, \"{material.name}\", \"\" {{\n")
            f.write("        Version: 102\n")
            f.write("        ShadingModel: \"phong\"\n")
            f.write("        MultiLayer: 0\n")
            f.write("        Properties70:  {\n")
            f.write("            P: \"DiffuseColor\", \"Color\", \"\", \"A\", 0.8, 0.8, 0.8\n")
            f.write("            P: \"SpecularColor\", \"Color\", \"\", \"A\", 0.2, 0.2, 0.2\n")
            f.write("            P: \"Emissive\", \"Vector3D\", \"Vector\", \"\", 0, 0, 0\n")
            f.write("            P: \"Ambient\", \"Vector3D\", \"Vector\", \"\", 0.2, 0.2, 0.2\n")
            f.write("            P: \"Diffuse\", \"Vector3D\", \"Vector\", \"\", 0.8, 0.8, 0.8\n")
            f.write("            P: \"Specular\", \"Vector3D\", \"Vector\", \"\", 0.2, 0.2, 0.2\n")
            f.write("            P: \"Shininess\", \"double\", \"Number\", \"\", 20\n")
            f.write("            P: \"Opacity\", \"double\", \"Number\", \"\", 1\n")
            f.write("            P: \"Reflectivity\", \"double\", \"Number\", \"\", 0\n")
            f.write("        }\n")
            f.write("    }\n")
            
            # Write texture if available
            if material.name in texture_map:
                texture_path = texture_map[material.name]
                f.write(f"    Texture: {2000 + i}, \"{material.name}_texture\", \"\" {{\n")
                f.write("        Type: \"TextureVideoClip\"\n")
                f.write("        Version: 202\n")
                f.write(f"        TextureName: \"{material.name}_texture\"\n")
                f.write(f"        FileName: \"{texture_path}\"\n")
                f.write("        Media: \"\"\n")
                f.write("        RelativeFilename: \"\"\n")
                f.write("        ModelUVTranslation: 0, 0\n")
                f.write("        ModelUVScaling: 1, 1\n")
                f.write("        Texture_Alpha_Source: \"None\"\n")
                f.write("        Cropping: 0, 0, 0, 0\n")
                f.write("    }\n")
        
        # Process each animation
        for anim_idx, animation in enumerate(model.animations):
            # For each mesh in the animation
            for frame_idx, mesh_idx in enumerate(animation.meshes):
                if mesh_idx >= len(model.meshes):
                    print(f"Warning: Mesh index {mesh_idx} out of range in animation {animation.name}")
                    continue
                
                mesh = model.meshes[mesh_idx]
                
                # Create a geometry for each mesh link
                for link_idx, link in enumerate(mesh.links):
                    # Get the data for this link
                    triangles = model.triangle_data[link.triangles]
                    points = model.points_data[link.points]
                    texture_coordinates = model.texture_coordinates_data[link.texture_coordinates]
                    
                    # Transform points
                    transformed_points = [transform_point(p) for p in points]
                    
                    # Generate a unique ID for this geometry
                    geom_id = 3000 + anim_idx * 1000 + frame_idx * 100 + link_idx
                    
                    # Write geometry
                    f.write(f"    Geometry: {geom_id}, \"Geometry::{animation.name}_frame{frame_idx}_link{link_idx}\", \"Mesh\" {{\n")
                    f.write("        Properties70:  {\n")
                    f.write("            P: \"Color\", \"ColorRGB\", \"Color\", \"\", 0.8, 0.8, 0.8\n")
                    f.write("        }\n")
                    f.write("        Vertices: *{} {{\n".format(len(transformed_points) * 3))
                    f.write("            a: ")
                    for i, p in enumerate(transformed_points):
                        f.write("{},{},{},".format(p[0], p[1], p[2]))
                    f.write("\n        }\n")
                    
                    # Write polygon vertex indices
                    f.write("        PolygonVertexIndex: *{} {{\n".format(len(triangles)))
                    f.write("            a: ")
                    for i in range(0, len(triangles), 3):
                        if i + 2 < len(triangles):
                            # FBX uses negative indices to mark the end of a polygon
                            f.write("{},{},{}".format(
                                triangles[i], 
                                triangles[i+1], 
                                -(triangles[i+2] + 1)  # Negative to mark end of polygon
                            ))
                            if i + 3 < len(triangles):
                                f.write(",")
                    f.write("\n        }\n")
                    
                    # Write UV coordinates
                    f.write("        GeometryVersion: 124\n")
                    f.write("        LayerElementNormal: 0 {\n")
                    f.write("            Version: 101\n")
                    f.write("            Name: \"\"\n")
                    f.write("            MappingInformationType: \"ByPolygonVertex\"\n")
                    f.write("            ReferenceInformationType: \"Direct\"\n")
                    f.write("            Normals: *{} {{\n".format(len(triangles) * 3))
                    f.write("                a: ")
                    for i in range(len(triangles)):
                        f.write("0,1,0,")  # Simplified: just use up vector for all normals
                    f.write("\n            }\n")
                    f.write("        }\n")
                    
                    # Write UV coordinates
                    f.write("        LayerElementUV: 0 {\n")
                    f.write("            Version: 101\n")
                    f.write("            Name: \"UVChannel_1\"\n")
                    f.write("            MappingInformationType: \"ByPolygonVertex\"\n")
                    f.write("            ReferenceInformationType: \"IndexToDirect\"\n")
                    f.write("            UV: *{} {{\n".format(len(texture_coordinates) * 2))
                    f.write("                a: ")
                    for tc in texture_coordinates:
                        f.write("{},{},".format(tc[0], tc[1]))
                    f.write("\n            }\n")
                    f.write("            UVIndex: *{} {{\n".format(len(triangles)))
                    f.write("                a: ")
                    for i in range(len(triangles)):
                        f.write("{},".format(triangles[i]))
                    f.write("\n            }\n")
                    f.write("        }\n")
                    
                    # Write material references
                    f.write("        LayerElementMaterial: 0 {\n")
                    f.write("            Version: 101\n")
                    f.write("            Name: \"\"\n")
                    f.write("            MappingInformationType: \"AllSame\"\n")
                    f.write("            ReferenceInformationType: \"IndexToDirect\"\n")
                    f.write("            Materials: *1 {\n")
                    f.write("                a: 0\n")
                    f.write("            }\n")
                    f.write("        }\n")
                    
                    # Write layer
                    f.write("        Layer: 0 {\n")
                    f.write("            Version: 100\n")
                    f.write("            LayerElement:  {\n")
                    f.write("                Type: \"LayerElementNormal\"\n")
                    f.write("                TypedIndex: 0\n")
                    f.write("            }\n")
                    f.write("            LayerElement:  {\n")
                    f.write("                Type: \"LayerElementMaterial\"\n")
                    f.write("                TypedIndex: 0\n")
                    f.write("            }\n")
                    f.write("            LayerElement:  {\n")
                    f.write("                Type: \"LayerElementUV\"\n")
                    f.write("                TypedIndex: 0\n")
                    f.write("            }\n")
                    f.write("        }\n")
                    f.write("    }\n")
                    
                    # Create a model (node) for this geometry
                    model_id = 4000 + anim_idx * 1000 + frame_idx * 100 + link_idx
                    f.write(f"    Model: {model_id}, \"{animation.name}_frame{frame_idx}_link{link_idx}\", \"Mesh\" {{\n")
                    f.write("        Version: 232\n")
                    f.write("        Properties70:  {\n")
                    f.write("            P: \"RotationActive\", \"bool\", \"\", \"\", 1\n")
                    f.write("            P: \"InheritType\", \"enum\", \"\", \"\", 1\n")
                    f.write("            P: \"ScalingMax\", \"Vector3D\", \"Vector\", \"\", 0, 0, 0\n")
                    f.write("            P: \"DefaultAttributeIndex\", \"int\", \"Integer\", \"\", 0\n")
                    f.write("        }\n")
                    f.write("        Shading: T\n")
                    f.write("        Culling: \"CullingOff\"\n")
                    f.write("    }\n")
                    
                    # Create material connections
                    f.write(f"    Material: {1000 + link.material}, \"{model.materials[link.material].name}\", \"\" {{\n")
                    f.write("        Version: 102\n")
                    f.write("        ShadingModel: \"phong\"\n")
                    f.write("        MultiLayer: 0\n")
                    f.write("        Properties70:  {\n")
                    f.write("            P: \"DiffuseColor\", \"Color\", \"\", \"A\", 0.8, 0.8, 0.8\n")
                    f.write("            P: \"SpecularColor\", \"Color\", \"\", \"A\", 0.2, 0.2, 0.2\n")
                    f.write("            P: \"Emissive\", \"Vector3D\", \"Vector\", \"\", 0, 0, 0\n")
                    f.write("            P: \"Ambient\", \"Vector3D\", \"Vector\", \"\", 0.2, 0.2, 0.2\n")
                    f.write("            P: \"Diffuse\", \"Vector3D\", \"Vector\", \"\", 0.8, 0.8, 0.8\n")
                    f.write("            P: \"Specular\", \"Vector3D\", \"Vector\", \"\", 0.2, 0.2, 0.2\n")
                    f.write("            P: \"Shininess\", \"double\", \"Number\", \"\", 20\n")
                    f.write("            P: \"Opacity\", \"double\", \"Number\", \"\", 1\n")
                    f.write("            P: \"Reflectivity\", \"double\", \"Number\", \"\", 0\n")
                    f.write("        }\n")
                    f.write("    }\n")
        
        # Write connections section
        f.write("}\n\n")
        f.write("Connections:  {\n")
        
        # Connect materials to textures
        for i, material in enumerate(model.materials):
            if material.name in texture_map:
                f.write(f"    C: \"OP\", {2000 + i}, {1000 + i}, \"DiffuseColor\"\n")
        
        # Connect geometries to models and materials
        for anim_idx, animation in enumerate(model.animations):
            for frame_idx, mesh_idx in enumerate(animation.meshes):
                if mesh_idx >= len(model.meshes):
                    continue
                
                mesh = model.meshes[mesh_idx]
                
                for link_idx, link in enumerate(mesh.links):
                    geom_id = 3000 + anim_idx * 1000 + frame_idx * 100 + link_idx
                    model_id = 4000 + anim_idx * 1000 + frame_idx * 100 + link_idx
                    
                    # Connect geometry to model
                    f.write(f"    C: \"OO\", {geom_id}, {model_id}\n")
                    
                    # Connect material to model
                    f.write(f"    C: \"OO\", {1000 + link.material}, {model_id}\n")
        
        f.write("}\n")
    
    print(f"FBX ASCII file written to {output_path}")

def export_to_fbx(model: Model, output_path: str = 'exports/fbx/model.fbx') -> None:
    """Export the model to FBX format."""
    # Create directories for export if they don't exist
    export_dir = os.path.dirname(output_path)
    os.makedirs(export_dir, exist_ok=True)
    
    # Create FBX ASCII file
    create_fbx_ascii(model, output_path)
    
    print(f"Model exported to {output_path}")
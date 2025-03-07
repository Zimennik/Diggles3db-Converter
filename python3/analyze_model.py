import os
import sys
from lib.parse_3db import parse_3db_file

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_model.py <model_file>")
        return
    
    model_path = sys.argv[1]
    if not os.path.exists(model_path):
        print(f"Error: Model file not found: {model_path}")
        return
    
    print(f'Loading model from {model_path}')
    with open(model_path, 'rb') as f:
        file_data = f.read()
        model = parse_3db_file(file_data)
        
        model_name = model.name
        if isinstance(model_name, bytes):
            model_name = model_name.decode('utf-8', errors='ignore')
        
        print(f"\nModel: {model_name}")
        print(f"Materials: {len(model.materials)}")
        for i, material in enumerate(model.materials):
            mat_name = material.name
            if isinstance(mat_name, bytes):
                mat_name = mat_name.decode('utf-8', errors='ignore')
                
            mat_path = material.path
            if isinstance(mat_path, bytes):
                mat_path = mat_path.decode('utf-8', errors='ignore')
                
            print(f"  {i}: {mat_name} - {mat_path}")
        
        print(f"\nMeshes: {len(model.meshes)}")
        
        # Analyze material usage by link position
        material_usage = {}
        for i in range(len(model.materials)):
            material_usage[i] = {"link_positions": set(), "mesh_count": 0}
        
        # Track link positions (0, 1, 2, etc.) where each material is used
        for mesh_idx, mesh in enumerate(model.meshes):
            for link_idx, link in enumerate(mesh.links):
                if link.material < len(model.materials):
                    material_usage[link.material]["link_positions"].add(link_idx)
                    material_usage[link.material]["mesh_count"] += 1
        
        print("\nMaterial usage analysis:")
        for mat_idx, usage in material_usage.items():
            if mat_idx < len(model.materials):
                mat_name = model.materials[mat_idx].name
                if isinstance(mat_name, bytes):
                    mat_name = mat_name.decode('utf-8', errors='ignore')
                
                link_positions = sorted(list(usage["link_positions"]))
                print(f"  Material {mat_idx}: {mat_name}")
                print(f"    Used in {usage['mesh_count']} meshes")
                print(f"    Found at link positions: {link_positions}")
        
        print("\nMesh link samples:")
        for i in range(min(5, len(model.meshes))):
            print(f"  Mesh {i}:")
            for j, link in enumerate(model.meshes[i].links):
                mat_name = "Unknown"
                if link.material < len(model.materials):
                    mat_name = model.materials[link.material].name
                    if isinstance(mat_name, bytes):
                        mat_name = mat_name.decode('utf-8', errors='ignore')
                
                print(f"    Link {j}: Material {link.material} ({mat_name})")
        
        print(f"\nAnimations: {len(model.animations)}")
        for i, anim in enumerate(model.animations):
            if i < 10:  # Show only first 10 animations
                anim_name = anim.name
                if isinstance(anim_name, bytes):
                    anim_name = anim_name.decode('utf-8', errors='ignore')
                
                print(f"  {i}: {anim_name} - {len(anim.meshes)} frames")

if __name__ == "__main__":
    main()

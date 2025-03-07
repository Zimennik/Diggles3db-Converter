import os
import sys
from lib.parse_3db import parse_3db_file

def main():
    model_path = 'assets/models/baby.3db'
    
    # Use provided model path if specified
    if len(sys.argv) > 1:
        model_path = sys.argv[1]
    elif not os.path.exists(model_path):
        model_path = '../assets/models/baby.3db'
    
    if not os.path.exists(model_path):
        print(f"Error: Could not find model at {model_path}")
        return
    
    print(f'Loading model from {model_path}')
    with open(model_path, 'rb') as f:
        file_data = f.read()
        model = parse_3db_file(file_data)
        
        print('\nMaterials:')
        for i, material in enumerate(model.materials):
            print(f'  {i}: {material.name} - {material.path}')
        
        print('\nMesh Links:')
        for i, mesh in enumerate(model.meshes):
            if i < 5:  # Just print the first few meshes
                print(f'  Mesh {i}:')
                for j, link in enumerate(mesh.links):
                    print(f'    Link {j}: Material {link.material}')

if __name__ == "__main__":
    main()
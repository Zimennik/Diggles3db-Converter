import sys
from lib.parse_3db import parse_3db_file

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_animations.py <model_file>")
        return
    
    model_path = sys.argv[1]
    
    with open(model_path, 'rb') as f:
        model = parse_3db_file(f.read())
    
    print(f"Model: {model.name}")
    print(f"Materials: {len(model.materials)}")
    for i, material in enumerate(model.materials):
        print(f"  {i}: {material.name} - {material.path}")
    
    print(f"\nMeshes: {len(model.meshes)}")
    
    print(f"\nAnimations: {len(model.animations)}")
    for i, anim in enumerate(model.animations):
        print(f"  {i}: {anim.name} - {len(anim.meshes)} frames")
        print(f"    Mesh indices: {anim.meshes}")

if __name__ == "__main__":
    main()

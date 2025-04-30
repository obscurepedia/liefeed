import os
import ast

def get_imports_and_usage(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=file_path)

    imports = set()
    used_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])
        elif isinstance(node, ast.Name):
            used_names.add(node.id)

    return imports, used_names

def check_file(file_path):
    imports, used_names = get_imports_and_usage(file_path)
    unused = imports - used_names
    if unused:
        print(f"\n❌ Unused imports in {file_path}:")
        for item in unused:
            print(f"   - {item}")
    else:
        print(f"✅ {file_path}: All imports are used.")

def scan_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                check_file(os.path.join(root, file))

# ✅ Scan the current directory or change the path below
if __name__ == "__main__":
    scan_directory(".")

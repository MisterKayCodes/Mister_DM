import os
import ast

def get_endpoints(directory):
    endpoints = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            for dec in node.decorator_list:
                                if isinstance(dec, ast.Call) and hasattr(dec.func, 'attr'):
                                    if dec.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                                        if dec.args and isinstance(dec.args[0], ast.Constant):
                                            endpoints.append(f"{dec.func.attr.upper()} {dec.args[0].value} ({file})")
                except Exception as e:
                    pass
    return endpoints

for ep in get_endpoints('api'):
    print(ep)

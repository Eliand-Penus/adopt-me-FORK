import os
from flask import Flask
from app import create_app
from jinja2 import Environment, FileSystemLoader

app = create_app()
env = Environment(loader=FileSystemLoader('app/templates'))

def check_templates():
    error_count = 0
    for root, dirs, files in os.walk('app/templates'):
        for file in files:
            if file.endswith('.html'):
                rel_path = os.path.relpath(os.path.join(root, file), 'app/templates').replace('\\', '/')
                try:
                    env.parse(env.loader.get_source(env, rel_path)[0])
                    # print(f"OK: {rel_path}")
                except Exception as e:
                    print(f"ERROR in {rel_path}: {e}")
                    error_count += 1
    print(f"Finished checking templates. Errors found: {error_count}")

if __name__ == "__main__":
    check_templates()

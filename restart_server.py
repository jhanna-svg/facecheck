#!/usr/bin/env python3
"""
Clear Python cache and restart Flask server
"""
import os
import shutil
import sys

def clear_cache():
    """Remove Python cache files"""
    for root, dirs, files in os.walk('.'):
        for d in dirs[:]:
            if d == '__pycache__':
                print(f"Removing {os.path.join(root, d)}")
                shutil.rmtree(os.path.join(root, d))
                dirs.remove(d)
        for f in files:
            if f.endswith('.pyc'):
                print(f"Removing {os.path.join(root, f)}")
                os.remove(os.path.join(root, f))

if __name__ == "__main__":
    print("Clearing Python cache...")
    clear_cache()
    print("Cache cleared!")
    
    print("Starting Flask server...")
    os.system("python app.py")
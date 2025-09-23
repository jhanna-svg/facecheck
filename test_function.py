#!/usr/bin/env python3
"""Test script to verify process_and_save_image function works"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import process_and_save_image
    print("✅ Function imported successfully!")
    print(f"Function location: {process_and_save_image}")
    print(f"Function docstring: {process_and_save_image.__doc__}")
except ImportError as e:
    print(f"❌ Import error: {e}")
except NameError as e:
    print(f"❌ Name error: {e}")
except Exception as e:
    print(f"❌ Other error: {e}")
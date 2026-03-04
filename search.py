#!/usr/bin/env python3
"""
Lensix — search.py
Thin entry point. All logic lives in src/.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import main

if __name__ == "__main__":
    main()
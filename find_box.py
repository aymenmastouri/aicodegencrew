#!/usr/bin/env python
"""Find Unicode box drawing characters in Python files."""
import os
import re

box_char = chr(0x2500)  # ─

for root, dirs, files in os.walk('src'):
    for fname in files:
        if fname.endswith('.py'):
            fpath = os.path.join(root, fname)
            try:
                content = open(fpath, encoding='utf-8', errors='ignore').read()
                count = content.count(box_char)
                if count > 0:
                    print(f"{fpath}: {count}")
                    # Find context
                    for i, line in enumerate(content.split('\n'), 1):
                        if box_char in line:
                            print(f"  Line {i}: {line[:80]}")
            except:
                pass

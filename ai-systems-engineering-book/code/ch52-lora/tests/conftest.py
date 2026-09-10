"""自举：src 加入 sys.path，使裸跑 pytest 也能工作。"""
import os
import sys

_HERE = os.path.dirname(__file__)
_ROOT = os.path.dirname(_HERE)

for p in (os.path.join(_ROOT, "src"),):
    if p not in sys.path:
        sys.path.insert(0, p)

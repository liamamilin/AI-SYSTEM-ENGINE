"""自举：src 与 ch11 sibling 加入 sys.path，使裸跑 pytest 也能工作。"""
import os
import sys

_HERE = os.path.dirname(__file__)
_ROOT = os.path.dirname(_HERE)
_CODE = os.path.dirname(_ROOT)

for p in (
    os.path.join(_ROOT, "src"),
    os.path.join(_CODE, "ch11-model-gateway", "src"),
):
    if p not in sys.path:
        sys.path.insert(0, p)

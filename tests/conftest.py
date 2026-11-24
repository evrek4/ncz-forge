import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

EXAMPLES = os.path.join(ROOT, "examples")
SAMPLE_NCZ = os.path.join(EXAMPLES, "103_11.NCZ")
SAMPLE_DXF = os.path.join(EXAMPLES, "103_11.dxf")

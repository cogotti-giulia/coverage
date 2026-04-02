import os
from enum import Enum

from utils.lte_specs import Operator

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DOC_ROOT = os.path.join(BASE_DIR, 'docs')

# TODO find a way to handle newer files, potrei fare com inbox e archivio nei telegrammi? bohh

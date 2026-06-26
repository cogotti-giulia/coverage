import os
from dataclasses import dataclass
from enum import Enum, IntEnum
from pathlib import Path

from utils.style import Logger


# ============================================
# LTE band used
# Ref. https://lteitaly.it/it/spectrum.php
# Ref. https://wiki.lteitaly.it/frequenze/
# ============================================
class LTEBand(str, Enum):
  # Format: (Band String, Frequency in MHz)
  B28 = ("B28", 700)
  B20 = ("B20", 800)
  B8 = ("B8", 900)
  B32 = ("B32", 1500)
  B3 = ("B3", 1800)
  B1 = ("B1", 2100)
  B7 = ("B7", 2600)
  B38 = ("B38", 2600)

  def __new__(cls, value, frequency):
    # This intercepts the tuple creation.
    # It assigns the first item as the string value, and the second as the frequency attribute!
    obj = str.__new__(cls, value)
    obj._value_ = value
    obj.frequency = frequency
    return obj


# ============================================
# Bandwidth expressed as MHz
# Ref. https://lteitaly.it/it/spectrum.php
# Ref. https://wiki.lteitaly.it/frequenze/
# ============================================
class Bandwidth(IntEnum):
  MHZ_5 = 5
  MHZ_10 = 10
  MHZ_15 = 15
  MHZ_20 = 20


# ============================================
# Spec that locks bandwidth and speed together
# Ref. https://lteitaly.it/it/spectrum.php
# Ref. https://wiki.lteitaly.it/frequenze/
# ============================================
@dataclass
class Spec:
  """Lock band, bandwidth and speed together"""
  band: LTEBand
  bandwidth: Bandwidth

  @property
  def speed(self) -> int:
    """
    Automatically applies the LTE Italy Wiki rule (1 MHz = 10 Mbps)
    :return: The speed (in Mbps) of the bandwidth
    """
    return self.bandwidth * 10


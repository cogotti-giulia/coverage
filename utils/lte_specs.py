from dataclasses import dataclass
from enum import Enum, IntEnum


# ===========================================
# Supported Italian mobile Operators
# ===========================================
class Operator(str, Enum):
  TIM = "TIM"
  VODAFONE = "Vodafone"
  ILIAD = "Iliad"
  WINDTRE = "WindTre"


# ============================================
# LTE band used
# Ref. https://lteitaly.it/it/spectrum.php
# Ref. https://wiki.lteitaly.it/frequenze/
# ============================================
class LTEBand(str, Enum):
  B28 = "B28"
  B20 = "B20"
  B8 = "B8"
  B32 = "B32"
  B3 = "B3"
  B1 = "B1"
  B7 = "B7"
  B38 = "B38"


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
  """Lock bandwidth and speed together"""
  bandwidth: Bandwidth

  @property
  def speed(self) -> int:
    """
    Automatically applies the LTE Italy Wiki rule (1 MHz = 10 Mbps)
    :return: The speed (in Mbps) of the bandwidth
    """
    return self.bandwidth * 10


# ============================================
# Identify operator by their MNC (Mobile Network Code in Italy)
# Ref. https://en.wikipedia.org/wiki/Mobile_network_codes_in_ITU_region_2xx_(Europe)#Italy_%E2%80%93_IT
# ============================================
MNC_MAP = {
  "01": Operator.TIM,
  "10": Operator.VODAFONE,
  "50": Operator.ILIAD,
  "88": Operator.WINDTRE,
  "99": Operator.WINDTRE
}

# =============================================
# Maps operator with band and specs for that band
# =============================================
OPERATOR_SPECS = {
  Operator.VODAFONE: {
    LTEBand.B28: Spec(Bandwidth.MHZ_10),
    LTEBand.B20: Spec(Bandwidth.MHZ_10),
    LTEBand.B8: Spec(Bandwidth.MHZ_5),
    LTEBand.B32: Spec(Bandwidth.MHZ_20),
    LTEBand.B3: Spec(Bandwidth.MHZ_20),
    LTEBand.B1: Spec(Bandwidth.MHZ_15),
    LTEBand.B7: Spec(Bandwidth.MHZ_15),
  },
  Operator.WINDTRE: {
    LTEBand.B20: Spec(Bandwidth.MHZ_10),
    LTEBand.B3: Spec(Bandwidth.MHZ_20),
    LTEBand.B1: Spec(Bandwidth.MHZ_20),
    LTEBand.B7: Spec(Bandwidth.MHZ_20),
  },
  Operator.TIM: {
    LTEBand.B28: Spec(Bandwidth.MHZ_10),
    LTEBand.B20: Spec(Bandwidth.MHZ_10),
    LTEBand.B8: Spec(Bandwidth.MHZ_5),
    LTEBand.B32: Spec(Bandwidth.MHZ_20),
    LTEBand.B3: Spec(Bandwidth.MHZ_20),
    LTEBand.B1: Spec(Bandwidth.MHZ_15),
    LTEBand.B7: Spec(Bandwidth.MHZ_15),
  },
  Operator.ILIAD: {
    LTEBand.B28: Spec(Bandwidth.MHZ_10),
    LTEBand.B3: Spec(Bandwidth.MHZ_10),
    LTEBand.B1: Spec(Bandwidth.MHZ_10),
    LTEBand.B7: Spec(Bandwidth.MHZ_10),
  }
}

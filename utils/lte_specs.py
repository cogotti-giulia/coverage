from dataclasses import dataclass
from enum import Enum, IntEnum


class Operator(str, Enum):
  TIM = "TIM"
  VODAFONE = "Vodafone"
  ILIAD = "Iliad"
  WINDTRE = "WindTre"

class LTEBand(str, Enum):
  B28 = "B28"
  B20 = "B20"
  B8 = "B8"
  B32 = "B32"
  B3 = "B3"
  B1 = "B1"
  B7 = "B7"
  B38 = "B38"

class Bandwidth(IntEnum):
  MHZ_5 = 5
  MHZ_10 = 10
  MHZ_15 = 15
  MHZ_20 = 20

# Use a Dataclass to lock Bandwidth and Speed together
@dataclass
class Spec:
  bandwidth: Bandwidth

  @property
  def speed(self) -> int:
    # Automatically applies the LTE Italy Wiki rule (1 MHz = 10 Mbps)
    return self.bandwidth * 10

# boh altre ma penso siano irrilevanti

# Identify operator by their MNC (Mobile Network Code in Italy)
MNC_MAP = {
  "01": Operator.TIM,
  "10": Operator.VODAFONE,
  "50": Operator.ILIAD,
  "88": Operator.WINDTRE,
  "99": Operator.WINDTRE
}

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

# operator: {band_id: speed (Mbps)} speed is based on https://wiki.lteitaly.it/frequenze/ and mostly on https://lteitaly.it/it/spectrum.php
# ref to the LTE
# ampiezza di 10 MHz = 100 Mbps di velocità

from dataclasses import dataclass
from enum import Enum, IntEnum


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


# ===========================================
# Supported Italian mobile Operators
# For each operator are defined
# - name (e.g. Vodafone)
# - mncs (e.g. 10)
# - specs (A list of operator specs)
#
# The MNC (Mobile Network Code in Italy) identify the operator
# Ref. https://en.wikipedia.org/wiki/Mobile_network_codes_in_ITU_region_2xx_(Europe)#Italy_%E2%80%93_IT
# ============================================
class Operator(str, Enum):
  TIM = ("TIM", ("01",), [
    Spec(band=LTEBand.B28, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B20, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B8, bandwidth=Bandwidth.MHZ_5),
    Spec(band=LTEBand.B32, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B3, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B1, bandwidth=Bandwidth.MHZ_15),
    Spec(band=LTEBand.B7, bandwidth=Bandwidth.MHZ_15),
  ])
  VODAFONE = ("Vodafone", ("10",), [
    Spec(band=LTEBand.B28, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B20, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B8, bandwidth=Bandwidth.MHZ_5),
    Spec(band=LTEBand.B32, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B3, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B1, bandwidth=Bandwidth.MHZ_15),
    Spec(band=LTEBand.B7, bandwidth=Bandwidth.MHZ_15),
  ])
  ILIAD = ("Iliad", ("50",), [
    Spec(band=LTEBand.B28, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B3, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B1, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B7, bandwidth=Bandwidth.MHZ_10),
  ])
  WINDTRE = ("WindTre", ("88", "99"), [
    Spec(band=LTEBand.B20, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B3, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B1, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B7, bandwidth=Bandwidth.MHZ_20),
  ])

  def __new__(cls, value, mncs, specs_list):
    """
    called before the __init__ method
    :param value:
    :param specs_list:
    """
    obj = str.__new__(cls, value)
    obj._value_ = value
    obj.mncs = mncs
    # Automatically converts the list into a lightning-fast dictionary
    obj.specs = {spec.band: spec for spec in specs_list}
    return obj

  @classmethod
  def from_mnsc(cls, mnc_code: str):
    for operator in cls:
      if mnc_code in operator.mncs:
        return operator
    return None  # no operator found

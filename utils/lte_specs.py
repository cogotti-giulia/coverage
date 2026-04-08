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


# ===========================================
# Default database table names
# ===========================================
DEFAULT_UPDATE_TABLE_NAME = "check_coverage_coverageupdate"
DEFAULT_MNCS_TABLE_NAME = "check_coverage_coveragemncs"

# ===========================================
# Default database columns for standard operators
# ===========================================
DEFAULT_DB_COLUMNS = [
  'latitude',
  'longitude',
  'arfcn',
  'site_name',
  'band_id',
  'loss',  # should  be called "sector"
  'technology',
  'speed',
  'bandwidth',  # it's the frequency
]


# ===========================================
# Supported Italian mobile Operators
# For each operator are defined
# - name (e.g. VODAFONE)
# - value (e.g. Vodafone)
# - mncs (e.g. 10)
# - specs (A list of operator specs)
# - db_columns (A list of DB columns for the operator)
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
  ], DEFAULT_DB_COLUMNS)
  VODAFONE = ("Vodafone", ("10",), [
    Spec(band=LTEBand.B28, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B20, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B8, bandwidth=Bandwidth.MHZ_5),
    Spec(band=LTEBand.B32, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B3, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B1, bandwidth=Bandwidth.MHZ_15),
    Spec(band=LTEBand.B7, bandwidth=Bandwidth.MHZ_15),
  ], DEFAULT_DB_COLUMNS)
  ILIAD = ("Iliad", ("50",), [
    Spec(band=LTEBand.B28, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B3, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B1, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B7, bandwidth=Bandwidth.MHZ_10),
  ], DEFAULT_DB_COLUMNS)
  WINDTRE = ("WindTre", ("88", "99"), [
    Spec(band=LTEBand.B20, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B3, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B1, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B7, bandwidth=Bandwidth.MHZ_20),
  ], DEFAULT_DB_COLUMNS)

  def __new__(cls, value, mncs, specs_list, db_columns):
    obj = str.__new__(cls, value)
    obj._value_ = value
    obj.mncs = mncs
    # Automatically converts the list into a lightning-fast dictionary
    obj.specs = {spec.band: spec for spec in specs_list}
    obj.db_columns = db_columns
    return obj

  @property
  def base_table(self) -> str:
    """DB table name"""
    return f"{os.getenv('DB_NAME')}_{self.value.lower()}coveragerow"

  @property
  def tmp_table(self) -> str:
    """DB tmp table name"""
    return f"{self.base_table}_tmp"

  @property
  def old_table(self) -> str:
    """DB old table name"""
    return f"{self.base_table}_old"

  @property
  def base_path(self) -> str:
    base_dir = Path(__file__).resolve().parent.parent
    return os.path.join(base_dir, "data", str(self.value))

  @property
  def inbox_path(self) -> str:
    return os.path.join(self.base_path, "inbox")

  @property
  def archive_path(self) -> str:
    return os.path.join(self.base_path, "archive")

  @property
  def log_path(self) -> str:
    return os.path.join(self.base_path, "log")

  @classmethod
  def from_mnsc(cls, mnc_code: str):
    """
    Returns the operator name corresponding to the given mnc code
    :param mnc_code: a mnc code
    :return: the operator name
    """
    for operator in cls:
      if mnc_code in operator.mncs:
        return operator
    return None  # no operator found

  @classmethod
  def from_identifier(cls, identifier):
    """
    Safely resolves a string or Operator instance into a valid Operator enum.
    :param identifier: an Operator instance or a string representing the operator name or value (e.g., 'Vodafone', 'VODAFONE', 'VoDaFOne').
    :return: Operator instance
    """
    # If it's already an Operator, just return it
    if isinstance(identifier, cls):
      return identifier

    # If it's a string, perform the lookup by the Enum name (e.g., 'VODAFONE') or value (e.g., 'Vodafone')
    if isinstance(identifier, str):
      identifier_upper = identifier.upper()
      for op in cls:
        if op.name.upper() == identifier_upper or op.value.upper() == identifier_upper:
          return op

    # Handle the case where it's not found
    logger = Logger()
    logger.error(f"Could not find operator matching: {identifier}")

    raise ValueError(f"'{identifier}' is not a valid Operator")

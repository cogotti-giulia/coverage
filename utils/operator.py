import os
from enum import Enum
from pathlib import Path

from utils.database.config import DEFAULT_MOBILE_DB_COLUMNS, DEFAULT_FASTWEB_FTTO_LIKE_DB_COLUMNS
from utils.lte_specs import LTEBand, Spec, Bandwidth
from utils.style import Logger

# ===========================================
# Represents an operator
# Handles shared logic for
# - operator inbox/archive/log path resolver
# - table base/old/tmp resolver
# - resolve a string into the Operator instance
# ===========================================
class BaseOperator(str, Enum):

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
  def category_folder(self) -> str:
    """To be overridden by subclasses (e.g., 'mobile', 'simple')"""
    raise NotImplementedError("Subclasses must define a category_folder")

  @property
  def base_path(self) -> str:
    base_dir = Path(__file__).resolve().parent.parent
    return os.path.join(base_dir, "data", self.category_folder(), str(self.value))

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
      classes_to_search = [cls] + cls.__subclasses__()

      for enum_class in classes_to_search:
        for op in enum_class:
          if op.name.upper() == identifier_upper or op.value.upper() == identifier_upper:
            return op

    # Handle the case where it's not found
    logger = Logger()
    logger.error(f"Could not find operator matching: {identifier}")

    raise ValueError(f"'{identifier}' is not a valid Operator")


# ===========================================
# Supported Italian mobile Operators
# For each operator are defined
# - name (e.g. WINDTRE)
# - value (e.g. windtre)
# - display_name (e.g. WindTre)
# - mncs (e.g. 10)
# - specs (A list of operator specs)
# - db_columns (A list of DB columns for the operator)
#
# The MNC (Mobile Network Code in Italy) identify the operator
# Ref. https://en.wikipedia.org/wiki/Mobile_network_codes_in_ITU_region_2xx_(Europe)#Italy_%E2%80%93_IT
# ============================================
class MobileOperator(BaseOperator):
  def category_folder(self):
    return "mobile"

  TIM = ("TIM", "TIM", ("01",), [
    Spec(band=LTEBand.B28, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B20, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B8, bandwidth=Bandwidth.MHZ_5),
    Spec(band=LTEBand.B32, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B3, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B1, bandwidth=Bandwidth.MHZ_15),
    Spec(band=LTEBand.B7, bandwidth=Bandwidth.MHZ_15),
  ], DEFAULT_MOBILE_DB_COLUMNS)
  VODAFONE = ("vodafone", "Vodafone", ("10",), [
    Spec(band=LTEBand.B28, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B20, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B8, bandwidth=Bandwidth.MHZ_5),
    Spec(band=LTEBand.B32, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B3, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B1, bandwidth=Bandwidth.MHZ_15),
    Spec(band=LTEBand.B7, bandwidth=Bandwidth.MHZ_15),
  ], DEFAULT_MOBILE_DB_COLUMNS)
  ILIAD = ("iliad", "Iliad", ("50",), [
    Spec(band=LTEBand.B28, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B3, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B1, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B7, bandwidth=Bandwidth.MHZ_10),
  ], DEFAULT_MOBILE_DB_COLUMNS)
  WINDTRE = ("windtre", "WindTre", ("88", "99"), [
    Spec(band=LTEBand.B20, bandwidth=Bandwidth.MHZ_10),
    Spec(band=LTEBand.B3, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B1, bandwidth=Bandwidth.MHZ_20),
    Spec(band=LTEBand.B7, bandwidth=Bandwidth.MHZ_20),
  ], DEFAULT_MOBILE_DB_COLUMNS)

  def __new__(cls, value, display_name, mncs, specs_list, db_columns):
    obj = str.__new__(cls, value)
    obj._value_ = value
    obj.display_name = display_name
    obj.mncs = mncs
    # Automatically converts the list into a lightning-fast dictionary
    obj.specs = {spec.band: spec for spec in specs_list}
    obj.db_columns = db_columns
    return obj

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


# ===========================================
# NON-mobile operators
#
# For each operator are defined
# - name (e.g. FASTWEB_ONNET)
# - value (e.g. fastweb_onnet)
# - display_name (e.g. Fastweb ONNET)
# - db_columns (A list of DB columns for the operator)
# # ===========================================
class SimpleOperator(BaseOperator):
  def category_folder(self):
    return "simple"

  FASTWEB_ONNET = ("fastweb_onnet", "Fastweb ONNET", DEFAULT_FASTWEB_FTTO_LIKE_DB_COLUMNS)
  FASTWEB_MIDNET = ("fastweb_midnet", "Fastweb MIDNET", DEFAULT_FASTWEB_FTTO_LIKE_DB_COLUMNS)

  def __new__(cls, value, display_name, db_columns):
    obj = str.__new__(cls, value)
    obj._value_ = value
    obj.display_name = display_name
    obj.db_columns = db_columns
    return obj
import csv
import datetime
import os
from collections import OrderedDict
from pathlib import Path

import openpyxl
import pandas as pd

from utils.database.sql import SqlHelper
from utils.style import Logger


class BaseExporter(object):
  """
  Pandas exporter helper to make easier the exports, so your brain shouldn't remember how to write those lines every time :)
  """

  BASE_DIR = Path(__file__).resolve().parent.parent
  STATIC_DOC_ROOT = BASE_DIR / 'docs'

  def __init__(self, default_filename=None):
    self._logger = Logger()
    # Store a default filename at the base level to fix the inheritance bug
    self.default_filename = default_filename or "export"

  def _compose_path(self, filepath=None, extension="csv", use_export_folder=False) -> str:
    """
    Composes the file path safely and creates necessary directories.
    """
    # Fallback to the class's default filename if none is provided
    target_name = filepath or self.default_filename

    # Strip any accidental dots from the extension
    extension = extension.lstrip('.')

    if use_export_folder:
      today = datetime.date.today()
      # pathlib handles all OS-specific slashes automatically
      final_path = (
          self.STATIC_DOC_ROOT /
          'export' /
          today.strftime('%Y') /
          today.strftime('%m') /
          today.strftime('%d') /
          f"{target_name}.{extension}"
      )
    else:
      final_path = Path(target_name)
      # Ensure it has the right extension if one wasn't in the filepath
      if not final_path.suffix:
        final_path = final_path.with_suffix(f".{extension}")

    # exist_ok=True avoids errors if the folder exists, parents=True creates intermediate folders
    final_path.parent.mkdir(parents=True, exist_ok=True)

    # Pandas and openpyxl generally prefer string paths, so we cast it back to string
    return str(final_path)


class BaseDataFrameExporter(BaseExporter):
  """
  Pandas exporter helper to create single export files
  """

  def __init__(self, data, columns=None):
    """
    :param data: Can be a QuerySet, a List of Dicts, or an existing DataFrame.
    :param columns: List of columns to export or None, if none automatically use the one passed from the data object
    """
    super(BaseDataFrameExporter, self).__init__()

    # Normalize input to a DataFrame
    if isinstance(data, pd.DataFrame):
      self.df = data
    else:
      # If it's a QuerySet, convert to list to force evaluation
      # If it's a list of dicts, pandas handles it automatically
      self.df = pd.DataFrame(list(data), columns=columns)

  def to_excel(self, filepath, index=False) -> str:
    """
    create the file and save it in the export path, adding the xls extension to the filename
    :param filepath:
    :param index: True if should be added a column index, else False
    :return: The export filepath
    """
    filepath = self._compose_path(filepath, extension='xlsx')

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
      self.df.to_excel(writer, index=index)
    return filepath

  def to_csv(self, filepath, index=False) -> str:
    """
    create the file and save it in the export path, adding the csv extension to the filename
    :param index: True if should be added a column index, else False
    :return: The export filepath
    """
    filepath = self._compose_path(filepath, extension='csv')
    self.df.to_csv(filepath, index=index, encoding='utf-8')
    return filepath

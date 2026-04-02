import csv
import datetime
import os
from collections import OrderedDict

import openpyxl
import pandas as pd

from utils.config import STATIC_DOC_ROOT
from utils.database.sql import SqlHelper
from utils.style import Logger


class BaseExporter(object):
  """
  Pandas exporter helper to make easier the exports, so your brain shouldn't remember how to write those lines every time :)
  P.S.: every export will be saved under the folder export/<year>/<month>/<filename>.<extension> in the STATIC_DOC_ROOT
  """
  SEPARATOR = '/'
  YEAR = '%Y'
  MONTH = '%m'
  DAY = '%d'

  def __init__(self, filename):
    self.filename = filename
    self._logger = Logger()

  def _compose_export_file_path(self, filename, extension='txt'):
    date_path = datetime.date.today().strftime(
      self.SEPARATOR + self.YEAR + self.SEPARATOR + self.MONTH + self.SEPARATOR + self.DAY + self.SEPARATOR)

    folder = 'export'
    return folder + date_path + filename + '.' + extension

  def _compose_path(self, extension='txt') -> str:
    filepath = os.path.join(STATIC_DOC_ROOT, self._compose_export_file_path(self.filename, extension))

    # Python 3: exist_ok=True replaces the need to check os.path.exists()
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    return str(filepath)


class BaseDataFrameExporter(BaseExporter):
  """
  Pandas exporter helper to create single export files
  """

  def __init__(self, data, filename, columns=None):
    """
    :param data: Can be a QuerySet, a List of Dicts, or an existing DataFrame.
    :param filename: Filename of the exported file
    :param columns: List of columns to export or None, if none automatically use the one passed from the data object
    """
    super(BaseDataFrameExporter, self).__init__(filename)

    # Normalize input to a DataFrame
    if isinstance(data, pd.DataFrame):
      self.df = data
    else:
      # If it's a QuerySet, convert to list to force evaluation
      # If it's a list of dicts, pandas handles it automatically
      self.df = pd.DataFrame(list(data), columns=columns)

  def to_excel(self, index=False) -> str:
    """
    create the file and save it in the export path, adding the xls extension to the filename
    :param index: True if should be added a column index, else False
    :return: The export filepath
    """
    filepath = self._compose_path(extension='xlxs')

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
      self.df.to_excel(writer, index=False)
    return filepath

  def to_csv(self, index=False) -> str:
    """
    create the file and save it in the export path, adding the csv extension to the filename
    :param index: True if should be added a column index, else False
    :return: The export filepath
    """
    filepath = self._compose_path(extension='csv')
    self.df.to_csv(filepath, index=index, encoding='utf-8')
    return filepath


class MultiSheetsExporter(BaseExporter):
  """
  Pandas exporter helper to export multiple sheets (basically for Excel)
  """

  def __init__(self, data, filename):
    """
    data: should be a dict of QuerySet, a List of Dicts, or an existing DataFrame
      where the keys are used as sheet names.
    :param data:
    :param filename:
    """
    super(MultiSheetsExporter, self).__init__(filename)
    self.sheets = OrderedDict()  # keeps original data order!

    for sheet_name, sheet_data in data.items():
      if isinstance(sheet_data, pd.DataFrame):
        df = sheet_data
      else:
        df = pd.DataFrame(list(sheet_data))

      self.sheets[sheet_name] = df

  def to_excel(self, index=False):
    """
    create the file with all sheets and save it in the export path, adding the xls extension to the filename
    TODO: maybe let the user choose sheet index, instead of a global one
    :param index: True if should be added a column index, else False
    """
    filepath = self._compose_path(extension='xlxs')

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
      for sheet_name, df in self.sheets.items():
        df.to_excel(
          writer,
          sheet_name=sheet_name[:31],  # Excel sheet name limit
          index=index
        )

  class BaseSqlExporter(BaseExporter):
    def __init__(self, conn, filename):
      self._conn = conn
      self._sql_helper = SqlHelper(conn)
      super().__init__(filename)

    def to_csv(self, query):
      filepath = self._compose_path(extension='csv')

      def save_to_file(cursor):
        # Python 3 requirement: use 'w' mode with newline='' for CSVs to prevent blank rows
        with open(filepath, "w", newline="", encoding="utf-8") as f:
          writer = csv.writer(f)

          # no header
          while True:
            rows = cursor.fetchmany(1000)
            if not rows:
              break

            # No need to encode strings in Py3, writerows handles the entire chunk at once
            writer.writerows(rows)

      self._sql_helper.execute(query, func=save_to_file)
      self._logger.info(f"Exported data into {filepath}")
      return filepath

    def to_excel(self, query):
      filepath = self._compose_path(extension='xlsx')

      def save_to_file(cursor):
        # Replaced xlwt with openpyxl logic
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = 'Sheet1'

        # header row
        headers = [col[0] for col in cursor.description]
        sheet.append(headers)

        # data rows
        while True:
          rows = cursor.fetchmany(1000)
          if not rows:
            break

          for row in rows:
            # In Py3 with openpyxl, just pass the tuple. No encoding loop necessary!
            sheet.append(row)

        workbook.save(filepath)

      self._sql_helper.execute(query, func=save_to_file)
      self._logger.info(f"Exported data into {filepath}")
      return filepath

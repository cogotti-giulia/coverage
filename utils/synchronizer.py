import os
import datetime

import pandas as pd

from utils.database.sql import SqlHelper
from utils.exporter import BaseDataFrameExporter
from utils.lte_specs import Operator, DEFAULT_UPDATE_TABLE_NAME, DEFAULT_MNCS_TABLE_NAME
from utils.style import Logger


class CoverageDbSynchronizer(object):
  """Handles the safe swapping and loading of operator coverage data."""

  def __init__(self, conn, debug_mode=False):
    self._sql_helper = SqlHelper(conn)
    self._DEBUG = debug_mode
    self._logger = Logger()

  def replace_operator_coverage(self, operator: Operator, df: pd.DataFrame):
    """
    Safely replaces the old coverage table with the newly parsed data.
    How does it work? (happy case, when everything works as expected)
    1. drop existing `check_coverage_<operator>_old` and `check_coverage_<operator>_tmp` table (`_tmp` shouldn't exist, but who knows)
    2. create the `check_coverage_<operator>_tmp` empty table copying the schema from the `check_coverage_<operator>`
    3. export the dataframe into a temporary csv file
    4. load csv in the `check_coverage_<operator>_tmp` table
    5. atomic swap:
       - rename `check_coverage_<operator>` to `_old` (keep backup)
       -rename `check_coverage_<operator>_tmp` into `check_coverage_<operator>`
    6. Update `check_coverage_coverageupdate` table to track data update
    7. delete the temporary csv file
    :param operator: the operator to use
    :param df: the dataframe to replace the old coverage table with
    """
    if self._DEBUG:
      self._logger.info(f"Starting coverage sync for {operator.name}")

    # Initialize filepath so the 'finally' block doesn't crash if an early error occurs
    filepath = None

    try:
      # 1. drop existing tables
      self._sql_helper.drop_tables([operator.tmp_table, operator.old_table])
      # 2. create _tmp table
      self._sql_helper.copy_table(old_table_name=operator.base_table, new_table_name=operator.tmp_table)
      # 3. export data to a temporary csv
      today = datetime.datetime.now().strftime("%Y%m%d")
      path = os.path.join("../data", f"{operator.value}", "inbox", f"{operator.base_table}_{today}")
      exporter = BaseDataFrameExporter(df, columns=operator.db_columns)
      filepath = exporter.to_csv(path)
      # 4. load csv data into _tmp table
      self._sql_helper.load_file_data(operator.tmp_table, filepath, operator.db_columns)

      # --- UNCOMMENT TO SIMULATE DB CRASH ---
      # import mysql.connector
      # raise mysql.connector.Error("Simulated DB connection lost!")
      # --------------------------------------

      # 5. ATOMIC SWAP: The live table becomes old, and the tmp table becomes live instantly.
      self._sql_helper.swap_tables_atomically(
        current_table=operator.base_table,
        backup_table=operator.old_table,
        new_table=operator.tmp_table
      )

      # 6. Update check_coverage_coverageupdate table to track data update
      if self._DEBUG:
        self._logger.info(f"Updating coverage info data for {operator.name}")
      placeholders = SqlHelper.build_in_placeholders(operator.mncs)
      # 6.1 Get the supplier id by operator mncs
      select_supplier_id_sql = f"""SELECT DISTINCT supplier_id FROM {DEFAULT_MNCS_TABLE_NAME} WHERE mnc IN ({placeholders});"""
      res = self._sql_helper.execute(select_supplier_id_sql, params=operator.mncs)
      if not res:
        self._logger.warning(f"Operator with MNCs {operator.mncs} not found. Needs insertion. TO BE IMPLEMENTED.")
      else:
        # 6.2 Update the info data by supplier id
        res_list = SqlHelper.extract_column(res, 0)
        update_sql = f"""UPDATE {DEFAULT_UPDATE_TABLE_NAME} SET last_update = %s WHERE id = %s;"""
        self._sql_helper.execute(update_sql, params=(df.last_data_update, res_list[0]), commit=True)
        if self._DEBUG:
          self._logger.info(f"Successfully updated coverage info data for {operator.name}")

    except Exception as e:
      self._logger.error(f"Sync failed for {operator.name}. Cleaning up temporary data...")

      # "Rollback" the table creation by dropping the tmp table
      try:
        self._sql_helper.drop_tables([operator.tmp_table])
        if self._DEBUG:
          self._logger.info(f"Dropped orphaned temp table: {operator.tmp_table}")
      except Exception as drop_err:
        # We just log this, we don't want to hide the original error
        self._logger.error(f"Failed to drop temp table during cleanup: {drop_err}")
      # Re-raise the error so the Orchestrator knows it failed!
      raise
    finally:
      # 7. Cleanup the temporary csv file (This runs whether it succeeds OR fails!)
      if filepath and os.path.exists(filepath):
        os.remove(filepath)
        if self._DEBUG:
          self._logger.info(f"Removed temporary CSV file: {filepath}")

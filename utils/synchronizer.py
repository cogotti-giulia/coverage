import os
import datetime

import pandas as pd

from utils.database.config import DEFAULT_UPDATE_TABLE_NAME
from utils.database.sql import SqlHelper
from utils.exporter import BaseDataFrameExporter
from utils.operator import BaseOperator
from utils.style import Logger


class CoverageDbSynchronizer(object):
  """Handles the safe swapping and loading of operator coverage data."""

  def __init__(self, conn, debug_mode=False, dry_run_mode=False):
    self._sql_helper = SqlHelper(conn)
    self._DEBUG = debug_mode
    self._DRY_RUN = dry_run_mode
    self._logger = Logger()


  def replace_operator_coverage(self, operator: BaseOperator, df: pd.DataFrame):
    """
    Safely replaces the old coverage table with the newly parsed data.
    How does it work? (happy case, when everything works as expected)
    1. drop existing `check_coverage_<operator>_old` and `check_coverage_<operator>_tmp` table (`_tmp` shouldn't exist, but who knows)
    2. create the `check_coverage_<operator>_tmp` empty table copying the schema from the `check_coverage_<operator>`
    3. export the dataframe into a temporary csv file
    4. load csv in the `check_coverage_<operator>_tmp` table
    5. atomic swap:
       - rename `check_coverage_<operator>` to `_old` (keep backup)
       - rename `check_coverage_<operator>_tmp` into `check_coverage_<operator>`
    6. Update `check_coverage_coverageupdate` table to track data update
    7. delete the temporary csv file
    :param operator: the operator to use
    :param df: the dataframe to replace the old coverage table with
    """
    if self._DEBUG:
      self._logger.info(f"Starting coverage sync for {operator.name}")

    # Initialize filepath so the 'finally' block doesn't crash if an early error occurs
    filepath = None
    today = datetime.datetime.now().strftime("%Y%m%d")
    path = os.path.join("../data", f"{operator.value}", "inbox", f"{operator.base_table}_{today}")

    if self._DRY_RUN:
      self._logger.warning(f"DRY RUN mode is ON, skipping real sync")
      self._logger.log(f"[DRY RUN] 1. Dropping tables {operator.tmp_table} and {operator.old_table}")
      self._logger.log(f"[DRY RUN] 2. Creating _tmp table {operator.tmp_table}")
      self._logger.log(f"[DRY RUN] 3. Exporting dataframe into a temporary csv file in the path {path}")
      self._logger.log(f"[DRY RUN] 4. Loading exported csv file into the _tmp table {operator.tmp_table}")
      self._logger.log(f"[DRY RUN] 5. Atomic swap:\n- rename {operator.base_table} to {operator.old_table} (to keep backup)\n- rename {operator.tmp_table} to {operator.base_table}\nin a single step, so the operation couldn't crash in the middle of it!")
      self._logger.log(f"[DRY RUN] 6. Updating {DEFAULT_UPDATE_TABLE_NAME} to track last data update for {operator.name}")
      self._logger.log(f"[DRY RUN] 7. Delete the temporary csv file (this runs whether it succeeds OR fails above)")
      return
    try:
      # 1. drop existing tables
      self._sql_helper.drop_tables([operator.tmp_table, operator.old_table])
      # 2. create _tmp table
      self._sql_helper.copy_table(old_table_name=operator.base_table, new_table_name=operator.tmp_table)
      # 3. export data to a temporary csv
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

      # Verify supplier exists by name (adjust 'supplier_name')
      select_supplier_sql = f"""SELECT id FROM {DEFAULT_UPDATE_TABLE_NAME} WHERE supplier = %s;"""
      res = self._sql_helper.execute(select_supplier_sql, params=(operator.display_name,))

      if not res:
        self._logger.warning(
          f"Operator '{operator.display_name}' not found in {DEFAULT_UPDATE_TABLE_NAME}. Please, add the supplier first!")
      else:
        update_sql = f"""UPDATE {DEFAULT_UPDATE_TABLE_NAME} SET last_update = %s WHERE supplier = %s;"""
        self._sql_helper.execute(update_sql, params=(df.last_data_update, operator.display_name), commit=True)
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

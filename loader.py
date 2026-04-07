import datetime
import glob
import os.path
import shutil
import mysql.connector

import pandas as pd

from utils.exporter import BaseDataFrameExporter
from utils.database.sql import SqlHelper
from utils.lte_specs import Operator
from utils.style import Logger


class NetmonsterParser(object):
  """Parses Netmonster (.ntm) files and normalizes coverage data."""

  def __init__(self):
    self._logger = Logger()

  def _normalize_technology(self, df: pd.DataFrame) -> pd.DataFrame:
    mask_4g = df['technology'].str.contains('4G', case=False, na=False)
    df.loc[mask_4g, 'technology'] = 'LTE'
    # 1. Look for DSS
    mask_dss = df['site_name'].str.contains('DSS', case=False, na=False)
    df.loc[mask_dss, 'technology'] = '5G'  # DSS is both 4G/5G so it will be a 5G for us

    # 2. Look for true 5G (Make sure it doesn't overwrite DSS by accident)
    mask_5g = df['site_name'].str.contains('5G', case=False, na=False)  # & ~mask_dss
    df.loc[mask_5g, 'technology'] = '5G'

    return df

  def _lookup_band_specs(self, row: pd.Series) -> tuple[str | None, str | None]:
    """Helper function to fetch speed and frequency based on mnc and band_id"""
    try:
      operator = Operator.from_mnsc(row['mnc'])
      spec = operator.specs[row["band_id"]]
      return (spec.speed, str(spec.band.frequency))
    except (KeyError, ValueError, AttributeError):
      # Fallback just in case the band_id or mnc isn't found
      return (None, None)

  def _parse_file(self, filename: str) -> pd.DataFrame:
    column_names = ["technology", "mcc", "mnc", "cid", "tac", "enodeb", "pci", "latitude", "longitude", "description",
                    "earfcn"]

    df = pd.read_csv(filename, sep=";", header=None, names=column_names)
    # n=2 tells pandas to only split on the first two spaces it finds
    df[["band_id", "loss", "site_name"]] = df["description"].str.split(' ', n=2, expand=True)
    df['mnc'] = df['mnc'].astype(str).str.pad(2, fillchar='0')

    df = self._normalize_technology(df)
    # Scrub both words out of the site name so it stays beautiful and clean
    df['site_name'] = df['site_name'].str.replace('5G ', '', regex=False)
    df['site_name'] = df['site_name'].str.replace('DSS ', '', regex=False).str.strip()

    # Find unique mnc/band_id combinations in this chunk to avoid repeated class calls
    unique_combos = df[['mnc', 'band_id']].drop_duplicates()
    # Build a temporary dictionary for lightning-fast mapping
    lookup_dict = {}
    for _, row in unique_combos.iterrows():
      lookup_dict[(row['mnc'], row['band_id'])] = self._lookup_band_specs(row)
    # Map the dictionary back to the millions of rows instantly
    df['speed_freq'] = df.set_index(['mnc', 'band_id']).index.map(lookup_dict)

    # Split the mapped tuple into two columns
    df[['speed', 'bandwidth']] = pd.DataFrame(df['speed_freq'].tolist(), index=df.index)
    # Rename 'earfcn' to match the database column 'arfcn'
    df = df.rename(columns={'earfcn': 'arfcn'})

    first_mnc = df['mnc'].iloc[0]
    operator = Operator.from_mnsc(first_mnc)
    # Filter the DataFrame to ONLY include the columns for the database
    df_db_ready = df[operator.db_columns].copy()

    # Optional: drop duplicates based on unique constraints
    # df_db_ready = df_db_ready.drop_duplicates(subset=['band_id', 'loss', 'site_name'], keep='first')
    return df_db_ready

  def to_dataframe(self, filename) -> pd.DataFrame:
    return self._parse_file(filename)


class CoverageDbSynchronizer(object):
  """Handles the safe swapping and loading of operator coverage data."""

  def __init__(self, conn):
    self._sql_helper = SqlHelper(conn)
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
    6. delete the temporary csv file # TODO maybe keep as log
    :param operator: the operator to use
    :param df: the dataframe to replace the old coverage table with
    """
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
      path = os.path.join("data", f"{operator.value}", "inbox", f"{operator.base_table}_{today}")
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

      self._logger.info(f"Successfully updated coverage data for {operator.name}")

      # TODO forse devo aggiornare la tabella dove ci sono gli operator
    except Exception as e:
      self._logger.error(f"Sync failed for {operator.name}. Cleaning up temporary data...")

      # "Rollback" the table creation by dropping the tmp table
      try:
        self._sql_helper.drop_tables([operator.tmp_table])
        self._logger.info(f"Dropped orphaned temp table: {operator.tmp_table}")
      except Exception as drop_err:
        # We just log this, we don't want to hide the original error
        self._logger.error(f"Failed to drop temp table during cleanup: {drop_err}")
      # Re-raise the error so the Orchestrator knows it failed!
      raise
    finally:
      # 6. Cleanup the temporary csv file (This runs whether it succeeds OR fails!)
      if filepath and os.path.exists(filepath):
        os.remove(filepath)
        self._logger.info(f"Removed temporary CSV file: {filepath}")


class CoveragePipelineOrchestrator:
  """Orchestrates the discovery, parsing, and syncing of coverage data."""

  def __init__(self, db_conn):
    self.db_conn = db_conn
    self._logger = Logger()

  def _get_parser_for_file(self, filepath: str):
    """
    Method to return the correct parser based on file extension.
    """
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()

    if ext == '.ntm':
      return NetmonsterParser()
    elif ext == '.csv':
      raise NotImplementedError("CSV parser not yet implemented.")
    else:
      raise ValueError(f"Unsupported file format: {ext}")

  def _process_operator_files(self, operator: Operator):
    """Finds all files in the operator's inbox and processes them."""
    # Grab ALL files in the inbox, regardless of extension
    inbox_files = glob.glob(os.path.join(operator.inbox_path, "*.*"))

    if not inbox_files:
      self._logger.info(f"No files found in inbox for {operator.value}.")
      return

    for filepath in inbox_files:
      filename = os.path.basename(filepath)
      timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

      try:
        self._logger.info(f"Processing {filename} for {operator.value}...")

        # Get the right parser & load the dataframe
        parser = self._get_parser_for_file(filepath)
        df = parser.to_dataframe(filepath)

        # Stop if empty
        if df.empty:
          raise ValueError(
            f"The file {filename} parsed successfully but contains 0 rows of data. Aborting sync to protect live tables.")

        # Sync to the database
        synchronizer = CoverageDbSynchronizer(self.db_conn)
        synchronizer.replace_operator_coverage(operator, df)

        # Archive the file if successful
        archive_filename = f"{timestamp}_{filename}"
        archive_dest = os.path.join(operator.archive_path, archive_filename)
        shutil.move(filepath, archive_dest)
        self._logger.info(f"Successfully processed and archived {filename}.")


      except mysql.connector.Error as db_err:
        # db error, leave file in inbox to retry later
        self._logger.error(f"FATAL DATABASE ERROR while processing {filename}: {db_err}")
        self._logger.error("Aborting pipeline to prevent data loss.")
        raise

      except Exception as e:
        # The database is fine, but this specific file is corrupted/bad.
        # Move it to the log folder and continue to the next file.
        self._logger.error(f"File parsing error for {filename}: {e}")
        error_dest = os.path.join(operator.log_path, f"{timestamp}_ERROR_{filename}")
        shutil.move(filepath, error_dest)

  def sync_all_operators(self):
    """The main entry point. Iterates over all known operators."""
    self._logger.info("Starting global coverage sync pipeline...")

    for operator in Operator:  # Ensure directories exist before we do anything
      self.sync_operator(operator)

    self._logger.info("Global coverage sync pipeline finished.")

  def sync_operator(self, operator_identifier: Operator | str):
    """
    Runs the pipeline for a single specific operator.
    Accepts either an Operator enum instance or a string name (e.g., 'TIM' or 'Vodafone').
    """
    target_op = None

    # Figure out which operator they want
    if isinstance(operator_identifier, Operator):
      target_op = operator_identifier
    elif isinstance(operator_identifier, str):
      # Look up by the Enum name (e.g., 'VODAFONE') or value (e.g., 'Vodafone')
      for op in Operator:
        if op.name.upper() == operator_identifier.upper() or op.value.upper() == operator_identifier.upper():
          target_op = op
          break

    if not target_op:
      self._logger.error(f"Could not find operator matching: {operator_identifier}")
      raise ValueError(f"Invalid operator identifier: {operator_identifier}")

    # Ensure directories exist to prevent OS Errors (they should)
    os.makedirs(target_op.inbox_path, exist_ok=True)
    os.makedirs(target_op.archive_path, exist_ok=True)
    os.makedirs(target_op.log_path, exist_ok=True)

    # Run the specific pipeline
    self._logger.info(f"Starting specific coverage sync for {target_op.value}...")
    self._process_operator_files(target_op)
    self._logger.info(f"Finished coverage sync for {target_op.value}.")

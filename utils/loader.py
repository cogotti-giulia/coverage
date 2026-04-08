import datetime
import glob
import os.path
import shutil
import mysql.connector

from utils.lte_specs import Operator
from utils.parsers import NetmonsterParser
from utils.style import Logger
from utils.synchronizer import CoverageDbSynchronizer


class CoveragePipelineOrchestrator:
  """Orchestrates the discovery, parsing, and syncing of coverage data."""

  def __init__(self, db_conn, debug_mode=False):
    self.db_conn = db_conn
    self._DEBUG = debug_mode
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

  def _process_operator_files(self, operator: Operator, extension: str = None):
    """
    Finds files in the operator's inbox.
    If extension is provided (e.g., 'ntm'), only those files are processed.
    """
    pattern = f"*.{extension}" if extension else "*.*"
    inbox_files = glob.glob(os.path.join(operator.inbox_path, pattern))

    if not inbox_files:
      self._logger.warning(f"No files found in inbox for {operator.value}.")
      return

    for filepath in inbox_files:
      filename = os.path.basename(filepath)
      timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

      try:
        if self._DEBUG:
          self._logger.info(f"Processing {filename} for {operator.value}...")

        # Get the right parser & load the dataframe
        parser = self._get_parser_for_file(filepath)
        df = parser.to_dataframe(filepath)

        # Stop if empty
        if df.empty:
          raise ValueError(
            f"The file {filename} parsed successfully but contains 0 rows of data. Aborting sync to protect live tables.")

        # Sync to the database
        synchronizer = CoverageDbSynchronizer(self.db_conn, debug_mode=self._DEBUG)
        synchronizer.replace_operator_coverage(operator, df)

        # Archive the file if successful
        archive_filename = f"{timestamp}_{filename}"
        archive_dest = os.path.join(operator.archive_path, archive_filename)
        shutil.move(filepath, archive_dest)
        if self._DEBUG:
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

  def sync_all_operators(self, extension: str = None):
    """The main entry point. Iterates over all known operators."""
    if self._DEBUG:
      self._logger.info("Starting global coverage sync pipeline...")

    for operator in Operator:  # Ensure directories exist before we do anything
      self.sync_operator(operator, extension)
    if self._DEBUG:
      self._logger.info("Global coverage sync pipeline finished.")

  def sync_operator(self, operator_identifier: Operator | str, extension: str = None):
    """
    Runs the pipeline for a single specific operator.
    Accepts either an Operator enum instance or a string name (e.g., 'TIM' or 'Vodafone').
    """
    target_op = Operator.from_identifier(operator_identifier)

    # Ensure directories exist to prevent OS Errors (they should)
    os.makedirs(target_op.inbox_path, exist_ok=True)
    os.makedirs(target_op.archive_path, exist_ok=True)
    os.makedirs(target_op.log_path, exist_ok=True)

    # Run the specific pipeline
    if self._DEBUG:
      self._logger.info(f"Starting specific coverage sync for {target_op.value}...")

    self._process_operator_files(target_op, extension)

    if self._DEBUG:
      self._logger.info(f"Finished coverage sync for {target_op.value}.")

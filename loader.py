import datetime
import os.path

import pandas as pd

from utils.database.exporter import BaseDataFrameExporter
from utils.database.sql import SqlHelper
from utils.lte_specs import Operator, LTEBand, Spec
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

    # Filter the DataFrame to ONLY include the columns for the database
    df_db_ready = df[CoverageDbSynchronizer.DB_COLUMNS].copy()

    # Optional: drop duplicates based on your unique constraints
    # df_db_ready = df_db_ready.drop_duplicates(subset=['band_id', 'loss', 'site_name'], keep='first')

    return df_db_ready

  def to_dataframe(self, filename) -> pd.DataFrame:
    return self._parse_file(filename)


class CoverageDbSynchronizer(object):
  """Handles the safe swapping and loading of operator coverage data."""
  # Updated to reflect your notes: changed loss -> sector, bandwidth -> frequency, added enodeb
  DB_COLUMNS = [
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
    5. rename `check_coverage_<operator>` to `_old` (keep backup)
    6. rename `check_coverage_<operator>_tmp` into `check_coverage_<operator>`
    7. delete the temporary csv file # TODO maybe keep as log
    :param operator: the operator to use
    :param df: the dataframe to replace the old coverage table with
    """

    self._logger.info(f"Starting coverage sync for {operator.name}")
    # 1. drop existing tables
    self._sql_helper.drop_tables([operator.tmp_table, operator.old_table])
    # 2. create _tmp table
    self._sql_helper.copy_table(old_table_name=operator.base_table, new_table_name=operator.tmp_table)
    # 3. export data to a temporary csv
    today = datetime.datetime.now().strftime("%Y%m%d")
    path = os.path.join(f"{operator.value}", "inbox", f"{operator.base_table}_{today}")
    exporter = BaseDataFrameExporter(df, path, columns=self.DB_COLUMNS)
    # TODO rename
    filepath = exporter.to_csv()
    # 4. load csv data into _tmp table
    self._sql_helper.load_file_data(operator.tmp_table, filepath, self.DB_COLUMNS)
    # 5. backup table
    self._sql_helper.rename_table(operator.base_table, operator.old_table)
    # 6. rename _tmp into base
    self._sql_helper.rename_table(operator.tmp_table, operator.base_table)

    self._logger.info(f"Successfully updated coverage data for {operator.name}")

    # TODO forse devo aggiornare la tabella dove ci sono gli operator (???)
    raise NotImplementedError()

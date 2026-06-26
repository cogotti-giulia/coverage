import datetime
import os

import pandas as pd

from utils.operator import MobileOperator
from utils.style import Logger


class NetmonsterParser(object):
  """Parses Netmonster (.ntm) files and normalizes coverage data."""

  def __init__(self):
    self._logger = Logger()

  def _normalize_technology(self, df: pd.DataFrame) -> pd.DataFrame:
    mask_4g = df['technology'].str.contains('4G', case=False, na=False)
    df.loc[mask_4g, 'technology'] = 'LTE'
    # Look for DSS
    mask_dss = df['site_name'].str.contains('DSS', case=False, na=False)
    df.loc[mask_dss, 'technology'] = '5G'  # DSS is both 4G/5G so it will be a 5G for us
    # Look for true 5G (Make sure it doesn't overwrite DSS by accident)
    mask_5g = df['site_name'].str.contains('5G', case=False, na=False)  # & ~mask_dss
    df.loc[mask_5g, 'technology'] = '5G'

    return df

  def _lookup_band_specs(self, row: pd.Series) -> tuple[str | None, str | None]:
    """Helper function to fetch speed and frequency based on mnc and band_id"""
    try:
      operator = MobileOperator.from_mnsc(row['mnc'])
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
    operator = MobileOperator.from_mnsc(first_mnc)
    # Filter the DataFrame to ONLY include the columns for the database
    df_db_ready = df[operator.db_columns].copy()

    # Optional: drop duplicates based on unique constraints
    # df_db_ready = df_db_ready.drop_duplicates(subset=['band_id', 'loss', 'site_name'], keep='first')
    return df_db_ready

  def to_dataframe(self, filename) -> pd.DataFrame:
    df = self._parse_file(filename)
    date_str = os.path.basename(filename).split('_')[1]
    df.last_data_update = datetime.datetime.strptime(date_str, "%Y%m%d").strftime('%Y-%m-%d %H:%M:%S')
    return df

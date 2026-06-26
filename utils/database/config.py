
# ===========================================
# Default database table names
# ===========================================
DEFAULT_UPDATE_TABLE_NAME = "check_coverage_coverageupdate"

# ===========================================
# Default database columns for standard operators
# ===========================================
DEFAULT_MOBILE_DB_COLUMNS = [
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

DEFAULT_FASTWEB_FTTO_LIKE_DB_COLUMNS = [
  'id_egon_civico',
  'provincia',
  'comune',
  'particella_toponomastica',
  'nome_via',
  'civico_toponomastico'
]


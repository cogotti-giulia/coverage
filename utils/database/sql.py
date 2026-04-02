from utils.database.db_connect import get_connection_cursor
from utils.style import Logger


class SqlHelper:
  """Just a SQL helper class to perform simple operations"""

  def __init__(self, conn):
    self._conn = conn
    self._logger = Logger()

  def execute(self, query, params=None, commit=False, func=None):
    """
    Executes a SQL query, optionally commits the transaction, and returns the fetched results.
    Automatically handles cursor creation, list-to-tuple parameter conversion, and error rollbacks.

    :param query: The SQL query string to execute.
    :param params: A tuple or list of parameters to inject safely into the query (avoids SQL injection).
    :param commit: Boolean indicating whether to commit the transaction (True for DML like INSERT/UPDATE).
    :param func: An optional callback function to execute on the active cursor before fetching results.
    :return: A list of tuples containing the fetched rows.
    :raises Exception: If the query fails, rolls back the transaction and re-raises the error.
    """
    try:
      with get_connection_cursor(self._conn, commit) as cursor:
        if isinstance(params, list):
          params = tuple(params)
        self._logger.log(f"Executing\n{query}")
        cursor.execute(query, params)
        self._logger.log(".....yey")
        if func:
          func(cursor)
        return cursor.fetchall()
    except Exception as e:
      self._conn.rollback()
      self._logger.error("Error executing query. Rolled back changes.", error_detail=e)
      raise

  def copy_table(self, old_table_name, new_table_name):
    """
    Creates a new table as an exact structural clone of an existing table.
    Note: This only copies the schema (columns, types, and indexes), not the data.

    :param old_table_name: The name of the existing table to clone.
    :param new_table_name: The name of the new table to be created.
    """
    sql = f"CREATE TABLE {new_table_name} LIKE {old_table_name};"
    self.execute(sql)

  def rename_table(self, old_table_name, new_table_name):
    """
    Renames an existing table in the database.

    :param old_table_name: The current name of the table.
    :param new_table_name: The new name for the table.
    """
    sql = f"ALTER TABLE {old_table_name} RENAME TO {new_table_name};"
    self.execute(sql)

  def create_table(self, table_name, columns):
    """
    Creates the table with the given name and columns.
    Raises an exception if something goes wrong in the db operation and rollback.

    :param table_name: Name of the table
    :param columns: A list of column tuples in the format (column_name, column_type, options).
      Example:
        [("dialprefix", "bigint", "DEFAULT NULL"),
        ("destination", "text"),
        ("buyrate", "double", "DEFAULT NULL")]
    :return:
    """

    columns_sql = ",\n  ".join(
      f"`{name}` {col_type} {opts}".strip()
      for name, col_type, opts in columns
    )
    sql = f"""
     CREATE TABLE IF NOT EXISTS `{table_name}` (
      {columns_sql}
    ) ENGINE=MyISAM DEFAULT CHARSET=latin1;
    """

    self.execute(sql)

  def drop_tables(self, tables):
    """
    Drops the tables from the given list of tables, if they exist.
    Raises an exception if something goes wrong in the db operation and rollback.
    :param tables: list of table names, or just a single str table name
    """
    if isinstance(tables, str):
      tables = [tables]
    for table_name in tables:
      sql = f"""
      DROP TABLE IF EXISTS {table_name};
      """
      self.execute(sql)

  def create_index(self, idx, table, column):
    """
    Creates an index, doesn't check if it exists at the moment.
    Raises an exception if something goes wrong in the db operation and rollback.
    :param idx: index name
    :param table: table name
    :param column: column name to apply the index to
    """
    sql = f"""
           CREATE INDEX `{idx}` ON {table} ({column})
           """
    self.execute(sql)

  def load_file_data(self, table_name, filename, columns, ignore_rows=1):
    """
    Loads data from a local CSV file into the specified table using LOAD DATA LOCAL INFILE.
    Raises an exception if something goes wrong and rolls back.

    :param table_name: Name of the destination table
    :param filename: Path to the local CSV file
    :param columns: List of column names mapping the CSV fields to DB columns
                    Example: ['name', 'age', 'status']
    :param ignore_rows: Number of header rows to ignore (default 1)
    """
    import os

    # Ensure it's an absolute paths
    absolute_path = os.path.abspath(filename)

    # Safely format the columns list into a SQL string: (`col1`, `col2`)
    columns_string = ", ".join(f"`{col}`" for col in columns)

    sql = f"""
      LOAD DATA LOCAL INFILE %s
      INTO TABLE `{table_name}`
      FIELDS TERMINATED BY ',' 
      ENCLOSED BY '"'
      LINES TERMINATED BY '\\n'
      IGNORE {ignore_rows} ROWS
      ({columns_string});
    """

    self._logger.info(f"Loading data from {filename} into {table_name}...")
    self.execute(sql, params=[absolute_path], commit=True)

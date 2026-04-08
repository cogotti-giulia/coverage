import os

import mysql.connector
from contextlib import contextmanager

from utils.style import Logger


db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'allow_local_infile': True
}

@contextmanager
def get_db_connection():
  """
  Context manager that creates a database connection.
  Whatever happens it happens, but at the end it closes the connection (even in case of errors).
  :return:
  """
  logger = Logger()
  conn = None
  try:
    # connect to DB
    conn = mysql.connector.connect(**db_config)

    # give control back to the main script
    yield conn

  except mysql.connector.Error as e:
    logger.error("Database error", error_detail=e)
    raise

  finally:
    # this runs no matter what happens (even on errors)
    if conn and conn.is_connected():
      conn.close()
      # logger.log("Database connection closed")

from contextlib import contextmanager

@contextmanager
def get_connection_cursor(conn, commit=False):
  """
  Context manager for a MySQL cursor.
  Whatever happens it happens, but at the end it closes the cursor (even in case of errors).

  :param conn: MySQL connection
  :param commit: if True, commits changes on exit
  """
  cursor = conn.cursor()
  try:
    yield cursor
    if commit:
      conn.commit()
  except Exception:
    conn.rollback()
    raise
  finally:
    # Python 3 safe cleanup to prevent "InternalError: Unread result found"
    try:
      # First, try to clear any un-fetched rows in the current result set
      cursor.fetchall()
    except Exception:
      pass

    try:
      # Then, cycle through any remaining result sets (e.g., from stored procs)
      while cursor.nextset():
        try:
          cursor.fetchall()
        except Exception:
          pass
    except Exception:  # Py3: Never use a bare 'except:'
      pass

    cursor.close()


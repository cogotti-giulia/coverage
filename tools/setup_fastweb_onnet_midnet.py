import argparse
import datetime
import sys
from dotenv import load_dotenv

from utils.database.config import DEFAULT_UPDATE_TABLE_NAME
from utils.operator import SimpleOperator

load_dotenv(".env")

import mysql.connector

from utils.database.db_connect import get_db_connection
from utils.database.sql import SqlHelper
from utils.style import Logger


def main(args):
  try:
    with get_db_connection() as conn:
      sql_helper = SqlHelper(conn)

      for op in [SimpleOperator.FASTWEB_ONNET, SimpleOperator.FASTWEB_MIDNET]:
        columns = [("id_egon_civico", "varchar(80)", ""),
         ("provincia", "varchar(30)", ""),
         ("comune", "varchar(60)", ""),
         ("particella_toponomastica", "varchar(28)", ""),
         ("nome_via", "varchar(80)", ""),
         ("civico_toponomastico", "varchar(15)", ""),]

        sql_helper.create_table(op.base_table, columns)

        sql_helper.insert(table=DEFAULT_UPDATE_TABLE_NAME,
                          data={"last_update": datetime.datetime.today(), "supplier": op.display_name, "data_type": "Database"})

  except mysql.connector.Error as db_err:
    logger.error(f"FATAL: Database connection failed: {db_err}")
    sys.exit(1)
  except Exception as e:
    logger.error(f"FATAL: Unexpected pipeline error: {e}")
    sys.exit(1)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description="Setup Fastweb ONNET and Fastweb MIDNET tables and adds coverage update row for both of them.")
  logger = Logger()

  main(parser.parse_args())

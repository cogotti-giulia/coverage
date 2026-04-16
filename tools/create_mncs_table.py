import argparse
import sys
from dotenv import load_dotenv

load_dotenv(".env.dev")

import mysql.connector

from utils.database.db_connect import get_db_connection
from utils.database.sql import SqlHelper
from utils.lte_specs import MobileOperator, DEFAULT_MNCS_TABLE_NAME, DEFAULT_UPDATE_TABLE_NAME
from utils.style import Logger


def main(args):
  try:
    with get_db_connection() as conn:
      # FIXME MyIsam does not support Foreign Keys, while InnoDB does
      sql_helper = SqlHelper(conn)
      mnc_columns = [
        ("mnc", "VARCHAR(5)", "PRIMARY KEY"),
        ("supplier_id", "INT", "NOT NULL")
      ]

      sql_helper.create_table(DEFAULT_MNCS_TABLE_NAME, mnc_columns)

      operator_list = []
      if args.operator:
        for op_name in args.operator:
          operator_list.append(MobileOperator.from_identifier(op_name))
      else:
        operator_list = MobileOperator

      rows_to_insert = []
      for op in operator_list:
        # 1. prendi l'id  dalla check_coverage_coverageupdate
        ids_sql = f"""SELECT id FROM {DEFAULT_UPDATE_TABLE_NAME} WHERE supplier LIKE CONCAT('%', %s, '%')"""

        res = sql_helper.execute(ids_sql, (op.value,))
        res_list = SqlHelper.extract_column(res, 0)

        for id_op in res_list:
          for mnc in op.mncs:
            rows_to_insert.append({
              "mnc": mnc,
              "supplier_id": id_op
            })

    if rows_to_insert:
      sql_helper.bulk_insert(
        table=DEFAULT_MNCS_TABLE_NAME,
        data_list=rows_to_insert,
        ignore=True
      )


  except mysql.connector.Error as db_err:
    logger.error(f"FATAL: Database connection failed: {db_err}")
    sys.exit(1)
  except Exception as e:
    logger.error(f"FATAL: Unexpected pipeline error: {e}")
    sys.exit(1)


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description="Creates or updates the MNCS table, adding a row for each operator. When inserting skip rows that would cause duplicate key or constraint errors.")
  parser.add_argument("--operator", type=str, nargs='+',
                      help="One or more operators (e.g., --operator Vodafone WindTre). Omitting syncs all.")

  logger = Logger()

  main(parser.parse_args())

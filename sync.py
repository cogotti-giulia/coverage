import sys

from dotenv import load_dotenv
load_dotenv(".env.dev")
import argparse
import mysql.connector

from utils.database.db_connect import get_db_connection
from utils.loader import CoveragePipelineOrchestrator
from utils.style import Logger


def main(args):
  try:
    with get_db_connection() as conn:
      orchestrator = CoveragePipelineOrchestrator(conn, debug_mode=args.debug)
      if args.operator:
        for op_name in args.operator:
          orchestrator.sync_operator(op_name, extension=args.format)
      else:
        orchestrator.sync_all_operators(extension=args.format)

  except mysql.connector.Error as db_err:
    logger.error(f"FATAL: Database connection failed: {db_err}")
    sys.exit(1)
  except Exception as e:
    logger.error(f"FATAL: Unexpected pipeline error: {e}")
    sys.exit(1)

if __name__ == '__main__':
  # TODO add dry-run mode
  parser = argparse.ArgumentParser(description="LTE Coverage Data Sync Pipeline")
  parser.add_argument("--operator", type=str, nargs='+',
                      help="One or more operators (e.g., --operator Vodafone WindTre). Omitting syncs all.")
  parser.add_argument("--format", type=str,
                      help="File extension to process (e.g., ntm, csv). Omitting process all")

  parser.add_argument("--debug", action="store_true", default=False, help="Enable to show more cool debug lines!")

  logger = Logger()

  main(parser.parse_args())



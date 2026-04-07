from dotenv import load_dotenv
load_dotenv(".env.dev")

from loader import CoveragePipelineOrchestrator

from utils.database.db_connect import get_db_connection

# TODO handle operator to sync, by writing scripts

def main():
  with get_db_connection() as conn:
    orchestrator = CoveragePipelineOrchestrator(conn)
    orchestrator.sync_operator("Vodafone")


if __name__ == '__main__':
    main()
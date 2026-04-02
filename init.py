import os
from dotenv import load_dotenv
load_dotenv(".env.dev")

from utils import config
from loader import NetmonsterParser, CoverageDbSynchronizer
from utils.lte_specs import LTEBand, Operator

from utils.database.db_connect import get_db_connection


def main():

  #  curl 'https://lteitaly.it/api/AV1.php'
  #  -c cookies.txt
  #  -X POST
  #  -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0'
  #  -H 'Content-Type: application/json;charset=UTF-8'
  #  -H 'Cookie: cf_clearance=q8ZpEEORQudlb8R29R2FMucszv69KbG5yyx4MvRGTig-1774265599-1.2.1.1-Ac14q.wYojxy8Fa81mb3ypXjN_YwXhPizFDo0TYTiLe66zTbWTGwwMSiu1KHop5b6RgkrcjWqXt5XYB4edwBKXKTKizhlQNXP84Cnuy.Rs7zIpJ6qL3bTrkoZEavNpF98xlnmbZ2AHoJqJQMKhExeCKES04YpreF_j_t8kXa8OJx2U4m9OsZZM6NHgVCQCjvqQuaghw9jKKKP9FNDlSYHJamxiE68OLSRnK2rGNTdMo;
  #  SESSION=apK16YjYqM8pAfqiqAwBF5k9pwwR8DvW; lang=it'
  #  --data-raw '["login","nicola.masiero","T.7e@SyykT7jH2j",true]'
  # TODO: capire se devo aggiornare o buttare via i dati e ricrearli :/
  # 1. Grab the dictionary Key
  my_operator = Operator.VODAFONE

  # 2. You figure out it's Band 20 from the CSV
  my_band = LTEBand.B20

  # 3. Ask the operator for its specific rules for that band!
  tower_spec = my_operator.specs.get(my_band)

  print(f"Operator: {my_operator}")  # Output: Vodafone
  print(f"MNCS: {my_operator.mncs}")  # Output: 10
  print(f"Band: {tower_spec.band}")  # Output: B20
  print(f"Frequency: {tower_spec.band.frequency}")  # Output: 800
  print(f"Ampiezza: {tower_spec.bandwidth} MHz")  # Output: 10 MHz
  print(f"Max Speed: {tower_spec.speed} Mbps")  # Output: 100 Mbps

  with get_db_connection() as conn:
    importer = NetmonsterParser()
    # TODO HANDLE FILENAME
    # potrei prenderlo dalla cartella "inbox" il primo .ntm che trovo
    # se serve lo archivio in archive
    # chiamo la cartella come l'operator name no? boh si
    # devo anc
    filename = os.path.join(config.STATIC_DOC_ROOT, "Vodafone", "vodafone_20250716_lteitaly.ntm")
    df = importer.to_dataframe(filename)

    db_loader = CoverageDbSynchronizer(conn)
    db_loader.replace_operator_coverage(Operator.VODAFONE, df)





if __name__ == '__main__':
    main()
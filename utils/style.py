import sys
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)


class Logger:
  """Just a simple Logger class to uniform the printed lines"""
  LEVELS = {
    "INFO": Fore.LIGHTCYAN_EX + "[INFO] " + Style.BRIGHT,
    "SUCCESS": Fore.GREEN + "[SUCCESS] " + Style.BRIGHT,
    "WARNING": Fore.YELLOW + Style.BRIGHT + "[WARNING] " + Style.BRIGHT,
    "ERROR": Fore.RED + Style.BRIGHT + "[ERROR] " + Style.BRIGHT,
  }

  @staticmethod
  def log(message, level="LOG"):
    prefix = Logger.LEVELS.get(level.upper(), "[LOG] ")
    print(prefix + str(message))

  @staticmethod
  def info(message):
    Logger.log(message, "INFO")

  @staticmethod
  def success(message):
    Logger.log(message, "SUCCESS")

  @staticmethod
  def warning(message, warning_detail=None):
    Logger.log(message, "WARNING")
    if warning_detail:
      print("{}Details: {}{}".format(Fore.YELLOW, Fore.RESET, warning_detail))

  @staticmethod
  def error(message, error_detail=None):
    Logger.log(message, "ERROR")
    if error_detail:
      print("{}Details: {}".format(Fore.RED, error_detail))

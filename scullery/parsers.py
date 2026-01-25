'''
Used to define sub-parsers
'''
from typing import Callable, Any

PARSER_FACTORY = {}

def register_parser(mid:str, parser_cb:Callable[None,[Any]]):
  '''Register a sub-parser

  :param mid: id for this sub-parser... Mainly used for sorting
  :param parser_cb: callback function that registers a sub-parser
  '''
  PARSER_FACTORY[mid] = parser_cb


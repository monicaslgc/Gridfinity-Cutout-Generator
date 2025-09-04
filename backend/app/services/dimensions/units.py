from __future__ import annotations
import math
from typing import Optional


# Common Wikidata unit QIDs → millimetre factor
WIKIDATA_UNIT_TO_MM = {
"http://www.wikidata.org/entity/Q174789": 1.0, # millimetre
"http://www.wikidata.org/entity/Q174728": 10.0, # centimetre
"http://www.wikidata.org/entity/Q11573": 1000.0, # metre
"http://www.wikidata.org/entity/Q218593": 25.4, # inch
"http://www.wikidata.org/entity/Q3710": 304.8, # foot

from .bb import BBMonthlyPDFParser
from .stone import StonePDFParser
from .cef import CEFPdfParser
from .sicredi import SicrediPDFParser
from .santander import SantanderPDFParser
from .itau import ItauPDFParser
from .bradesco import BradescoPDFParser
from .sicoob import SicoobPDFParser
from .cresol import CresolParser

PARSERS = {
    '001': BBMonthlyPDFParser,
    'STONE': StonePDFParser,
    '104': CEFPdfParser,
    '748': SicrediPDFParser,
    '033': SantanderPDFParser,
    '341': ItauPDFParser,
    '237': BradescoPDFParser,
    '756': SicoobPDFParser,
    'CRESOL': CresolParser
}

__all__ = [
    'BBMonthlyPDFParser', 
    'StonePDFParser', 
    'CEFPdfParser', 
    'SicrediPDFParser', 
    'SantanderPDFParser', 
    'ItauPDFParser',
    'BradescoPDFParser',
    'SicoobPDFParser'
]

# -*- coding: utf-8 -*-

from pyExcelerator import *

def save_stream(self):
    #import CompoundDoc
    doc = CompoundDoc.XlsDoc()
    return doc.savestream(self.get_biff_data())

setattr(Workbook,"save_stream",save_stream)

def savestream(self, stream):
    padding = '\x00' * (0x1000 - (len(stream) % 0x1000))
    self.book_stream_len = len(stream) + len(padding)
    self._XlsDoc__build_directory()
    self._XlsDoc__build_sat()
    self._XlsDoc__build_header()
    s = ""
    s = s + str(self.header)
    s = s + str(self.packed_MSAT_1st)
    s = s + str(stream)
    s = s + str(padding)
    s = s + str(self.packed_MSAT_2nd)
    s = s + str(self.packed_SAT)
    s = s + str(self.dir_stream)
    return s

setattr(CompoundDoc.XlsDoc,"savestream",savestream)
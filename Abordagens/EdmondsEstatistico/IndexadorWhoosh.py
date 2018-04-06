from whoosh.index import create_in, open_dir
from whoosh.qparser import QueryParser
from unidecode import unidecode
from whoosh.fields import *
import traceback
import os.path
import string

class IndexadorWhoosh(object):
    def __init__(self, dir_indexes):
        self.dir_indexes = dir_indexes

    def indexar_documentos(self, dir_documentos):
        if not os.path.exists(self.dir_indexes):
            os.mkdir(self.dir_indexes)

        schema = Schema(title=TEXT(stored=True), path=ID(stored=True), content=TEXT(stored=True))
        indexes = create_in(self.dir_indexes, schema)
        writer = indexes.writer()

    def consultar_documentos(self, lista_palavras):
        indexes = open_dir(self.dir_indexes)
        searcher = indexes.searcher()
        parser = QueryParser("content", indexes.schema)

        consultar = ""
        OR = " OR "

        for arg in lista_palavras:
            consultar += arg + OR

        consultar = parser.parse(consultar[:-len(OR)])
        resultado = [doc['content'] for doc in searcher.search(consultar, limit=None)]

        try: searcher.close()
        except: pass

        return resultado
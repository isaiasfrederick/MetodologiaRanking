import os.path
import string
import traceback

import whoosh.index
from unidecode import unidecode
from whoosh.fields import *
from whoosh.index import create_in
from whoosh.qparser import QueryParser


class Whoosh(object):
    DIR_INDEXES = "/mnt/ParticaoAlternat/Bases/Corpora/indexes"
    SCHEMA = Schema(title=TEXT(stored=True), path=ID(stored=True), content=TEXT(stored=True))

    @staticmethod
    def iniciar_indexacao(dir_lista_arquivos):
        if not os.path.exists(Whoosh.DIR_INDEXES):
            os.mkdir(Whoosh.DIR_INDEXES)
            indexer = create_in(Whoosh.DIR_INDEXES, Whoosh.SCHEMA)
        else:
            indexer = whoosh.index.open_dir(Whoosh.DIR_INDEXES)

        writer = indexer.writer()

        arquivo_lista = open(dir_lista_arquivos, 'r')
        todos_arquivos = [e.replace('\n', '') for e in arquivo_lista.readlines()]
        arquivo_lista.close()

        indice_arquivo = 1
        for arquivo in todos_arquivos:
            indice_linha = 1
            with open(arquivo) as arq:
                for linha_arq in arq:
                    try:
        				#conteudo = unicode(str(linha_arq).decode('utf-8'))
        				#conteudo = re.sub(r'[^\x00-\x7F]+',' ', conteudo)
                        conteudo = str(linha_arq)
                        conteudo = "".join([i if ord(i) < 128 else " " for i in conteudo])
                        nome_arquivo = arquivo+'-'+str(indice_linha)

                        title = unicode(nome_arquivo)
                        path = unicode(nome_arquivo)
                        content = unicode(conteudo)

                        writer.add_document(title=title, path=path, content=content)
                    except Exception, e:
                        print("\n")
                        traceback.print_exc()
                        print("\n")

                    print('\tArquivo %d - Linha %d' % (indice_arquivo, indice_linha))
                    indice_linha += 1
            indice_arquivo += 1

        print('Realizando commit...')
        writer.commit()
        print('Commit realizado...')

    @staticmethod
    def consultar_documentos(lista_palavras, operador, limite=None):
        if type(lista_palavras) != list:
            raise Exception("Indexador deve receber uma lista!")

        indexes = whoosh.index.open_dir(Whoosh.DIR_INDEXES)
        searcher = indexes.searcher()
        parser = QueryParser("content", indexes.schema)

        consultar = ""
        operador = " " + operador + " "

        for arg in lista_palavras:
            consultar += arg+operador

        consultar = parser.parse(consultar[:-len(operador)])
        resultado = [doc for doc in searcher.search(consultar, limit=limite)]

        return resultado

    @staticmethod
    def get_regex():
        rgx1 = u"\.|\,|\;|\s|\"|\-|\?|\!|\:|\t|\`|\_|\\(|\\)|\\[|\\]|@|\*"
        rgx2 = u"\u2019|\u201d|\u201f|\u2013|\u2014|\u2018"
        rgx3 = u"\u00e2|\u20ac|\u2122|\u0080"

        return rgx1+'|'+rgx2+'|'+rgx3

    @staticmethod
    def limpar(string):
        regex = get_regex()
        return ' '.join(re.split(regex, string))

#! coding: utf-8

from ModuloUtilitarios.Utilitarios import Utilitarios
from gensim.models import KeyedVectors

# Esta classe trabalha com WordEmbbedings para realizar a tarefa de prediçao de sinonimos
class RepresentacaoDistribuida(object):
    def __init__(self, configs):
        caminho_modelos = configs["dir_modelos"]
        caminho_completo_modelo = self.exibir_todos_modelos(caminho_modelos)

        raw_input(caminho_completo_modelo)
        self.vetores_palavras = KeyedVectors.load_word2vec_format(caminho_completo_modelo, binary=True)
        self.configs = configs

    def exibir_todos_modelos(self, caminho_modelos):
        todos_arquivos = Utilitarios.listar_arquivos(caminho_modelos)
        cont = 1

        print('\nESCOLHA O MODELO DESEJADO:')
        for p in todos_arquivos:
            print("%d - %s" % (cont, p))

        print('\n')
        indice = int(raw_input('Indice >> '))

        return todos_arquivos[indice - 1]

    def obter_palavras_relacionadas(self, palavra):
        pass
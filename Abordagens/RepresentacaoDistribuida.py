#! coding: utf-8

from gensim.scripts.glove2word2vec import glove2word2vec
from ModuloUtilitarios.Utilitarios import Utilitarios
from gensim.test.utils import datapath, get_tmpfile
from gensim.models import KeyedVectors
from sys import argv

# Esta classe trabalha com WordEmbbedings para realizar a tarefa de prediçao de sinonimos
class RepresentacaoDistribuida(object):
    def __init__(self, configs):
        self.modelo = None
        self.configs = configs

    def obter_palavras_relacionadas(self, palavra):
        return []

    # Retirado de https://radimrehurek.com/gensim/scripts/glove2word2vec.html
    def carregar_modelo(self, diretorio, binario=True):
        if binario == False:
            arq_glove = diretorio

            dir_arquivo_tmp = diretorio.split('/').pop()
            arq_tmp = self.configs['dir_temporarios'] + '/' + dir_arquivo_tmp + '.tmp'

            glove2word2vec(arq_glove, arq_tmp)
            self.modelo = KeyedVectors.load_word2vec_format(arq_tmp)
        else:
            self.modelo = KeyedVectors.load_word2vec_format(diretorio, binary=True)
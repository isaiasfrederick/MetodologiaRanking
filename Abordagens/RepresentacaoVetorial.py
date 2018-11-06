#! coding: utf-8

from gensim.scripts.glove2word2vec import glove2word2vec
from Utilitarios import Util
from gensim.test.utils import datapath, get_tmpfile
from gensim.models import KeyedVectors
from nltk.stem import PorterStemmer
from nltk.corpus import wordnet
from sys import argv
import re

wn = wordnet

# Esta classe trabalha com WordEmbbedings para realizar a tarefa de prediçao de sinonimos
class RepresentacaoVetorial(object):
    def __init__(self, configs):
        self.modelo = None
        self.configs = configs
        self.stemmer = PorterStemmer()

    # Dado um synset, cria uma representacao vetorial para o mesmo
    def criar_vetor_synset(self, lema_principal_synset, nome_synset):
        descritor_synset = wn.synset(nome_synset).lemma_names()
        lista_negativa = [ ]

        if wn.synset(nome_synset).pos() in ['n', 'v']:
            for hiper in wn.synset(nome_synset).hypernyms():
                raw_input("@@@ " + str(hiper.lemma_names()))
                descritor_synset += hiper.lemma_names()
            for hipo in wn.synset(nome_synset).hyponyms():
                descritor_synset += hipo.lemma_names()

        descritor_synset = list(set(descritor_synset))

        for synset in wn.synsets(lema_principal_synset, wn.synset(nome_synset).pos()):
            lista_negativa += synset.lemma_names()

        lista_negativa = list(set(lista_negativa) - set(descritor_synset))

        descritor_synset_tmp = descritor_synset
        descritor_synset = [ ]

        for p in descritor_synset_tmp:
            descritor_synset += re.split("_|-", p)

        print(descritor_synset)
        print("\n\n\n")
        print(lista_negativa)
        print("\n\n\n")

        return self.obter_palavras_relacionadas(positivos=descritor_synset, negativos=lista_negativa, topn=40)

    def obter_palavras_relacionadas(self, positivos=None, negativos=None, topn=1):
        try:
            if positivos == "": positivos = None
            if negativos == "": negativos = None

            if positivos != None: positivos = [p for p in positivos if p in self.modelo]
            if negativos != None: negativos = [p for p in negativos if p in self.modelo]

            return self.modelo.most_similar(positive=positivos, negative=negativos, topn=topn)
        except KeyError, ke:
            return [ ]

    def iniciar_processo(self, palavra_arg, pos_semeval, contexto, topn=10):
        if self.modelo == None:
            raw_input("Nao ha modelo carregado!")

        todos_conjuntos_synsets = [ ]

        registros = self.obter_palavras_relacionadas(positivos=[palavra_arg], topn=topn)
        saida = [ ]

        for palavra_flexionada, pontuacao in registros:
            # palavra = self.stemmer.stem(palavra_flexionada)
            palavra = palavra_flexionada            
            synsets = Util.obter_synsets(palavra, pos_semeval)

            if not synsets in todos_conjuntos_synsets:
                if synsets.__len__() > 0:
                    lema_synset = synsets[0].name().split('.')[0]
                    saida.append((lema_synset, pontuacao))
                todos_conjuntos_synsets.append(synsets)

        return [r[0] for r in saida]

    def palavra_diferente(self, lista_palavras):
        if type(lista_palavras) == str:
            lista_palavras = lista_palavras.split(" ")

        return self.modelo.doesnt_match(lista_palavras)

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
#! coding: utf-8
from pywsd.lesk_isaias import cosine_lesk
from ModuloUtilitarios.Utilitarios import Utilitarios

class DesambiguadorWordnet(object):   
    def __init__(self, configs): pass

    def adapted_cosine_lesk(self, contexto, palavra, pos=None):
        assinaturas, resultado = cosine_lesk(contexto, palavra, pos=pos, nbest=True)
        parametros, assinaturas = assinaturas

        return resultado

    # Realiza o processo de desambiguacao gerando um Ranking 
    # que usa da medida de cosseno como critério de ordenação
    # A partir disto, realiza a coleta de palavras correlatas
    # ao significado sugerido
    def extrair_sinonimos(self, contexto, palavra, pos=None, usar_exemplos=False):
        max_sinonimos = 10
        resultado = self.adapted_cosine_lesk(contexto, palavra, pos)

        sinonimos = []

        for item in resultado:
            synset, pontuacao = item

            if sinonimos.__len__() < max_sinonimos:
                sinonimos += [p for p in synset.lemma_names() if not Utilitarios.multipalavra(p)]
                sinonimos = list(set(sinonimos))

        return sinonimos[:max_sinonimos]
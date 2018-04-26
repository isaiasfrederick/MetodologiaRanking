from nltk.stem.porter import PorterStemmer
from nltk import word_tokenize, pos_tag
from nltk.corpus import wordnet as wn
from ModuloUtilitarios.Utilitarios import Utilitarios
import re

# esta classe funcionara como um "casador" de definicoes de diferentes fontes da abordagem
class RepositorioCentralConceitos:
    def __init__(self, configs):
        self.stemmer = PorterStemmer()
        self.configs = configs
        self.sep = "[-_;]"

    # Dado um conceito central através de um lema, retorne um conceito mais indicado
    # Sem remover stop_words
    def buscador_conceitos_centrais(self, lema, doc):
        resultado = []
        doc = self.stemizar_frase(doc)

        for s in wn.synsets(lema):
            resultado.append(s, Utilitarios.cosseno(s.definition(), doc))

        resultado.sort(key=lambda k: k[1], reverse=True)
        return resultado

    def buscar_casamento_perfeito(self, lema, todos_synsets, definicoes_oxford):
        resultados_oxford = dict()
        substantivos_univocos = list()
        contadores_substantivos_univocos = dict()

        for def_oxford in definicoes_oxford:
            for substantivo in self.extrair_substantivos(def_oxford):
                if not substantivo in resultados_oxford:
                    resultados_oxford[substantivo] = list()

                resultados_oxford[substantivo].append(def_oxford)

        # Identificando hiperonimo que so acontece uma vez nas definicoes
        for d in resultados_oxford:
            if len(resultados_oxford[d]) == 1:
                substantivos_univocos.append(d)
                contadores_substantivos_univocos[d] = 0
        
        for synset in todos_synsets:
            for caminho_tmp in synset.hypernym_paths():
                caminho = list(caminho_tmp)
                caminho = caminho[:-1]
                caminho.reverse()

                for hiperonimo in caminho:
                    for subs in substantivos_univocos:
                        if subs in hiperonimo.lemma_names():
                            contadores_substantivos_univocos[subs] += 1

        print('\n\n')
        raw_input(contadores_substantivos_univocos)
        return resultados_oxford

    def stemizar_frase(self, frase):
        return ' '.join([self.stemmer.stem(p) for p in frase.split(' ')])

    def mesclar_wordnet_oxford(self, lemma, obj_oxford):
        todos_synsets = wn.synsets(lemma, pos)

    def assinatura_relacionados(self, conjunto):
        sep = self.sep
        assinatura = ""

        for s in conjunto:
            assinatura += ' '.join([' ' + re.sub(sep, ' ', n) for n in s.lemma_names()])
            assinatura += ' ' + re.sub(sep, ' ', s.definition())

        return assinatura

    def assinatura_synset(self, s, usar_relacoes=True, stem=True):
        sep = self.sep

        assinatura = ' '.join([' ' + re.sub(sep, ' ', n) for n in s.lemma_names()])
        assinatura += ' ' + re.sub(sep, ' ', s.definition())

        if usar_relacoes:
            assinatura += ' ' + self.assinatura_relacionados(s.member_meronyms())
            assinatura += ' ' + self.assinatura_relacionados(s.member_holonyms())
            assinatura += ' ' + self.assinatura_relacionados(s.part_meronyms())
            assinatura += ' ' + self.assinatura_relacionados(s.part_holonyms())
        if stem:
            assinatura = self.stemizar_frase(assinatura)

        return assinatura.lower()

    # Retira substantivos da definicao
    def extrair_substantivos(self, definicao):
        pos_tags = pos_tag(word_tokenize(definicao))

        return [s[0] for s in pos_tags if s[1][0] == "N"]

    def extrair_hiperonimos_detectados(self, lemma, definicao):
        todos_substantivos = self.extrair_substantivos(definicao)

        resultados = dict()

        for s in wn.synsets(lemma):
            for caminho in s.hypernym_paths():
                for substantivo in todos_substantivos:
                    for sh in wn.synsets(substantivo):
                        if sh in caminho:
                            if not sh.name() in resultados:
                                resultados[sh.name()] = list()

                            resultados[sh.name()].append(s.name())
                            print('Os conceitos %s e %s casaram!' % (s.name(), sh.name()))

        return resultados
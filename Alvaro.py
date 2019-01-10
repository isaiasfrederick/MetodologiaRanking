# -*- coding: UTF-8 -*-
from DesOx import DesOx
from DesambiguadorWordnet import DesWordnet
from CasadorManual import CasadorManual
from Utilitarios import Util
from Arvore import Arvore, No
from nltk.corpus import wordnet
from RepresentacaoVetorial import RepVetorial
from string import punctuation
import CasadorManual
import traceback
import math
import sys

import nltk

import textblob

from OxAPI import BaseOx
from pywsd.lesk import cosine_lesk

wn = wordnet


class Alvaro(object):
    INSTANCE = None
    OBJETO_NGRAMS = { }

    # "nome#pos" : relacao
    relacao_sinonimia = { }

    def __init__(self, configs, base_ox, casador_manual, rep_vetorial):
        self.cfgs = configs
        self.base_ox = base_ox
        self.casador_manual = casador_manual
        self.rep_vetorial = rep_vetorial

    def construir_arvore_definicoes(self, lema, pos, max_prof, cands):
        seps = ":::"
        arvores = [ ]

        prof = 1

        for def_polissemia in BaseOx.obter_definicoes(self.base_ox, lema, pos):
            mxsdef = self.cfgs['alvaro']['mxspdef']

            sins = BaseOx.obter_sins(self.base_ox, lema, def_polissemia, pos=pos)
            sins = [s for s in sins if not Util.e_mpalavra(s)][:mxsdef]

            if cands in [None, [ ]]:
                flag_cand = True
                cands = [ ]
            else:
                flag_cand = False

            if set(sins).intersection(set(cands)) or flag_cand:
                label = "%s%s%s"%(lema, seps, def_polissemia)
                nodo_nivel1 = self.adicionar_nivel_arvore(label, No(None, label), pos, prof + 1, max_prof, cands)
                arvores.append(Arvore(nodo_nivel1))
        return arvores

    def adicionar_nivel_arvore(self, label, nodo_pai, pos, prof, max_prof, cands):
        flag_cand = cands in [None, [ ]]
        seps = ":::"

        # Se for menor que a profundidade maxima permitida
        if prof <= max_prof:
            lema, definicao = tuple(label.split(seps))
            for sin in BaseOx.obter_sins(self.base_ox, lema, definicao, pos=pos):
                if sin in cands or flag_cand:
                    for def_polissemia in BaseOx.obter_definicoes(self.base_ox, sin, pos=pos):
                        label = "%s%s%s"%(sin, seps, def_polissemia)
                        nodo_pai.add_filho(self.adicionar_nivel_arvore(label,
                                        No(nodo_pai, label), pos, prof+1, max_prof, cands))

        # Pai nao tera filhos, caso base
        return nodo_pai

    def construir_relacao_definicoes(self, palavra, pos, fontes='oxford', indice=1000):
        cfgs = self.cfgs

        resultado = { }

        dir_cache_rel_sinonimia = cfgs['caminho_bases']+'/'+cfgs['oxford']['cache']['sinonimia']

        kcache_relacao_sin = "%s-%s.json"%(palavra, pos)
        dir_obj = dir_cache_rel_sinonimia+'/'+kcache_relacao_sin

        if fontes == 'oxford':
            definicoes_palavra = BaseOx.obter_definicoes(BaseOx.INSTANCE, palavra, pos)
            for def_polis in definicoes_palavra[:indice]:
                resultado[def_polis] = { }
                for sin in BaseOx.obter_sins(BaseOx.INSTANCE, palavra, def_polis):
                    resultado[def_polis][sin] = BaseOx.obter_definicoes(BaseOx.INSTANCE, sin, pos)
                    if resultado[def_polis][sin] == None: resultado[d] = [ ]
            return resultado
        else:
            raise Exception('Este tipo de fonte nao foi implementada!')

    def pontuar_relacao_sinonimia(self, palavra, pos, fontes='oxford', indice=1000):
        relacao_sinonimia = self.construir_relacao_definicoes(palavra, pos, fontes=fontes)
        relacao_sinonimia_ponderada = { }

        for def_ambigua in relacao_sinonimia:
            if not def_ambigua in relacao_sinonimia_ponderada:
                relacao_sinonimia_ponderada[def_ambigua] = [ ]

            sins = BaseOx.obter_sins(BaseOx.INSTANCE, palavra, def_ambigua, pos=pos)

            for sin_iter in relacao_sinonimia[def_ambigua]:
                for def_iter in relacao_sinonimia[def_ambigua][sin_iter]:
                    pont = RepVetorial.word_move_distance(RepVetorial.INSTANCE, def_ambigua, def_iter)
                    relacao_sinonimia_ponderada[def_ambigua].append((sin_iter, def_iter, pont))

        return relacao_sinonimia_ponderada

    # Obtem a palavra mais usual para o significado mais usual para uma palavra
    def sugestao_contigencial(self, palavra,\
                        pos, fontes_def='oxford',\
                        metodo='definicao_usual',\
                        ctx=None, med_sim='cosine'):

        if metodo == 'definicao_usual':
            if pos == 'r':
                sins = wn.synsets(palavra, pos)[0].lemma_names()
                try:
                    sins.remove(palavra)
                except: pass
                return sins

            if fontes_def == 'wordnet':
                for syn in wn.synsets(palavra, pos):
                    for lema in syn.lemma_names():
                        if not Util.e_mpalavra(lema) and lema != palavra:
                            return [lema]
            elif fontes_def == 'oxford':
                try:
                    pos_ox = Util.cvsr_pos_semeval_ox(pos)                    
                    todas_definicoes = BaseOx.obter_definicoes(palavra, pos_ox)
                    def_prin = todas_definicoes[0]
                    sins = BaseOx.obter_sins(palavra, def_prin)
                    return sins
                except Exception, e:
                    print(e)
                    pass
        elif metodo == 'desambiguador':
            if fontes_def == 'wordnet':
                raise("\n\nFuncao nao implementada!\n\n")
            elif fontes_def == 'oxford':
                des_ox = DesOx(self.cfgs, self.base_ox, rep_vetorial=self.rep_vetorial)
                try:
                    label, definicao, exemplos = DesOx.desambiguar(des_ox, ctx, palavra, pos, nbest=True, med_sim=med_sim)[0][0]
                    sins_preditos = BaseOx.obter_sins(palavra, definicao, pos)
                    return sins_preditos
                except Exception, e:
                    pass
        else:
            raise("\nOpcao invalida para o metodo de SUGESTAO CONTIGENCIAL!\n")

        return [""]
            
    # Gabarito no formato [[palavra, voto], ...]
    def possui_moda(self, gabarito):
        todos_votos = sorted([v[1] for v in gabarito], reverse=True)
        return todos_votos.count(todos_votos[0])!=1

    # Seletor candidatos desconsiderando a questao da polissemia sob este aspecto
    # este metodo seleciona todos os candidatos 
    def selec_candidatos(self, palavra, pos, fontes=['wordnet'], max_por_def=4, indice_definicao=-1):        
        candidatos = set()
        comprimento = None

        if fontes in [[ ], None]:
            raise Exception("Fontes nao foram informadas!")
        if indice_definicao != -1 and fontes!=['oxford']:
            msg = "\nVoce nao pode selecionar um unico indice para mais de duas fontes! "
            msg += "O casamento de definicoes nao existe implementado!\n" 
            raise(msg)

        if 'wordnet' in fontes:
            for s in wn.synsets(palavra, pos):
                candidatos.update(s.lemma_names()[:max_por_def])
                if pos == 'n':
                    for h in s.hypernyms():
                        candidatos.update(h.lemma_names()[:max_por_def])
                    for h in s.hyponyms():
                        candidatos.update(h.lemma_names()[:max_por_def])
                elif pos in ['a','r','v']:
                    for similar in s.similar_tos():
                        candidatos.update(similar.lemma_names()[:max_por_def])

        if 'oxford' in fontes:
            todas_definicoes = BaseOx.obter_definicoes(self.base_ox, palavra, pos)
            for definicao in todas_definicoes:
                try:                
                    candidatos_tmp = BaseOx.obter_sins(self.base_ox, palavra, definicao, pos)[:max_por_def]
                except:
                    candidatos_tmp = [ ]
                candidatos.update([ ] if candidatos_tmp == None else candidatos_tmp)

        comprimento = len(candidatos)

        if set(['wordembbedings', 'embbedings']).intersection(set(fontes)):
            obter_palavras_relacionadas = self.rep_vetorial.obter_palavras_relacionadas
            ptmp = [p[0] for p in obter_palavras_relacionadas(positivos=[palavra],\
                                                        pos=pos, topn=comprimento)]
            candidatos.update(ptmp)

        if palavra in candidatos:
            candidatos.remove(palavra)

        return [p for p in list(candidatos) if len(p) > 1]

    # Retirado de https://stevenloria.com/tf-idf/
    def tf(self, word, blob):
        return float(blob.words.count(word))
        #return float(blob.words.count(word)) / float(len(blob.words))

    def n_containing(self, word, bloblist):
        return sum(1 for blob in bloblist if word in blob.words)

    def idf(self, word, bloblist):
        return math.log(len(bloblist) / len((1 + self.n_containing(word, bloblist))))

    def tfidf(self, word, blob, bloblist):
        return self.tf(word, blob) * self.idf(word, bloblist)

    @staticmethod
    def gerar_ngram(sentenca, _min_, _max_, palavra_central=None):
        ngrams_dict = { }
        tokens_tagueados = nltk.pos_tag(nltk.word_tokenize(sentenca))

        for n in range(_min_, _max_+1):
            ngrams_dict[n] = [ ]

        for n in range(_min_, _max_+1):
            for i in range(0, len(tokens_tagueados)-n):
                if i+n < len(tokens_tagueados):
                    novo_ngram = tokens_tagueados[i:i+n]
                
                    if palavra_central in [t for (t, pt) in novo_ngram] or palavra_central == None:
                        novo_ngram = [(t, pt) for (t, pt) in novo_ngram if not t in punctuation]
                        if palavra_central in [t for (t, pt) in novo_ngram] or palavra_central == None:
                            try:
                                if not novo_ngram in ngrams_dict[len(novo_ngram)]:
                                    ngrams_dict[len(novo_ngram)].append(novo_ngram)
                            except: pass

        ngrams = [ ]

        for n in sorted(ngrams_dict.keys(), reverse=True):
            ngrams += ngrams_dict[n]

        return ngrams

    @staticmethod
    def carregar_coca_ngrams(diretorio):
        min_ngram = 2
        max_ngram = 5

        arquivo_ngrams = open(diretorio, 'r')
        todas_linhas = arquivo_ngrams.readlines()
        arquivo_ngrams.close()

        todos_ngrams_tuplas = { } # <ngram : count>

        for linha_iter in todas_linhas:
            colunas = str(linha_iter).lower().split("\t")
            freq, tokens = int(colunas[0]), "\t".join(colunas[1:])

            ngrams = Alvaro.gerar_ngram(tokens, min_ngram, max_ngram)

            for ng in ngrams:
                if not str(ng) in todos_ngrams_tuplas:
                    todos_ngrams_tuplas[str(ng)] = int(freq)
                else:
                    todos_ngrams_tuplas[str(ng)] += int(freq)

        return todos_ngrams_tuplas

    @staticmethod
    def pontuar_sintagma(freq, len_sintagma, max_sintagma):
        len_sintagma = float(len_sintagma)
        max_sintagma = float(max_sintagma + 1)

        return freq / (1.00 / (len_sintagma ** 3))


    # https://stackoverflow.com/questions/24192979/
    @staticmethod
    def obter_antonimos(palavra, pos):
        if not pos in ['a', 's']:
            return [ ]
            
        anto = [ ]
        for s in wn.synsets(palavra, pos):
            for l in s.lemmas():
                for a in l.antonyms():
                    if not a.name() in anto:
                        anto.append(a.name())
        return anto
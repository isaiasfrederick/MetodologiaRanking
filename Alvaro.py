# -*- coding: UTF-8 -*-
from DesOx import DesOx
from DesambiguadorWordnet import DesWordnet
from CasadorManual import CasadorManual
from Utilitarios import Util
from Arvore import Arvore, No
from nltk.corpus import wordnet
import CasadorManual
import traceback
import math
import sys

from OxAPI import BaseOx
from pywsd.lesk import cosine_lesk

wn = wordnet

class AbordagemAlvaro(object):
    ABORDAGEM = None

    # "nome#pos" : relacao
    relacao_sinonimia = { }

    def __init__(self, configs, base_ox, casador_manual, rep_vetorial):
        self.cfgs = configs
        self.base_ox = base_ox
        self.casador_manual = casador_manual
        self.rep_vetorial = rep_vetorial

    def construir_relacao_definicoes(self, palavra, pos, fontes='oxford', indice=1000):
        cfgs = self.cfgs

        resultado = { }

        dir_cache_rel_sinonimia = cfgs['caminho_raiz_bases']+'/'+cfgs['oxford']['cache']['sinonimia']

        kcache_relacao_sin = "%s-%s.json"%(palavra, pos)
        dir_obj = dir_cache_rel_sinonimia+'/'+kcache_relacao_sin

        if fontes == 'oxford':
            definicoes_palavra = self.base_ox.obter_definicoes(palavra, pos)
            for def_polis in definicoes_palavra[:indice]:
                resultado[def_polis] = { }
                for sin in self.base_ox.obter_sins(palavra, def_polis):
                    resultado[def_polis][sin] = self.base_ox.obter_definicoes(sin, pos)
                    if resultado[def_polis][sin] == None: resultado[d] = [ ]
            return resultado
        else:
            raise Exception('Este tipo de fonte nao foi implementada!')

    def construir_arvore_definicoes(self, lema, pos, max_prof):
        seps = ":::"
        arvores = [ ]

        prof = 1

        for def_polissemia in self.base_ox.obter_definicoes(lema, pos):
            label = "%s%s%s"%(lema, seps, def_polissemia)
            nodo_nivel1 = self.adicionar_nivel_arvore(label, No(None, label), pos, prof + 1, max_prof)
            arvores.append(Arvore(nodo_nivel1))
        return arvores

    def adicionar_nivel_arvore(self, label, nodo_pai, pos, prof, max_prof):
        seps = ":::"
        # Se for menor que a profundidade maxima permitida
        if prof <= max_prof:
            lema, definicao = tuple(label.split(seps))
            for sin in self.base_ox.obter_sins(lema, definicao, pos=pos):
                for def_polissemia in self.base_ox.obter_definicoes(sin, pos=pos):
                    label = "%s%s%s"%(sin, seps, def_polissemia)
                    nodo_pai.add_filho(self.adicionar_nivel_arvore(label, No(nodo_pai, label), pos, prof + 1, max_prof))

        # Pai nao tera filhos, caso base
        return nodo_pai

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
                    todas_definicoes = self.base_ox.obter_definicoes(palavra, pos_ox)
                    def_prin = todas_definicoes[0]
                    sins = self.base_ox.obter_sins(palavra, def_prin)
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
                    label, definicao, exemplos = des_ox.desambiguar(ctx, palavra, pos, nbest=True, med_sim=med_sim)[0][0]
                    sins_preditos = self.base_ox.obter_sins(palavra, definicao, pos)
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
            raise("\nVoce nao pode selecionar um unico indice para mais de duas fontes! O casamento de definicoes nao existe implementado!\n")

        if 'wordnet' in fontes:
            for s in wn.synsets(palavra, pos):
                candidatos.update(s.lemma_names()[:max_por_def])

        comprimento = len(candidatos)

        if 'oxford' in fontes:
            todas_definicoes = self.base_ox.obter_definicoes(palavra, pos)
            for definicao in todas_definicoes:
                candidatos_tmp = self.base_ox.obter_sins(palavra, definicao, pos)[:max_por_def]
                candidatos.update([ ] if candidatos_tmp == None else candidatos_tmp)

        if 'wordembbedings' in fontes:
            ptmp = self.rep_vetorial.obter_palavras_relacionadas(positivos=palavra, pos=pos, topn=comprimento)
            ptmp = [p for p, score in ptmp]
            candidatos.update(ptmp)

        if palavra in candidatos:
            candidatos.remove(palavra)

        return list(candidatos)

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
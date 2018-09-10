# -*- coding: utf-8 -*-
from Utilitarios import Utilitarios
from nltk.corpus import stopwords as sw
from unidecode import unidecode
from nltk import word_tokenize
from math import log10, sqrt
from string import printable
from os import system, path
from nltk import pos_tag
from Abordagens.IndexadorWhoosh import *
from sys import argv
import traceback
import json
import nltk
import sys
import re

class AbordagemEdmonds(object):
    def __init__(self, configs, indexador_whoosh, contadores):
        self.indexador = indexador_whoosh
        self.contadores = contadores
        self.configs = configs

    def salvar_json(self, caminho_json_saida, palavras):        
        Utilitarios.salvar_json(caminho_json_saida, palavras)

    def get_regex(self):
        rgx1 = u"\.|\,|\;|\s|\"|\-|\?|\!|\:|\t|\`|\_|\\(|\\)|\\[|\\]|@|\*"
        rgx2 = u"\u2019|\u201d|\u201f|\u2013|\u2014|\u2018"
        rgx3 = u"\u00e2|\u20ac|\u2122|\u0080"

        return rgx1+'|'+rgx2+'|'+rgx3

    def calcular_mi(self, tamanho_corpus, freq_par, freq_a, freq_b, janela):
        numerador = (float(freq_par) * float(tamanho_corpus)) / (freq_a * freq_b * (janela * 2))
        return log10(numerador) / log10(2)

    def calcular_tscore(self, tamanho_corpus, freq_par, freq_a, freq_b, janela=1):
        freq_a_normalizada = float(freq_a)/tamanho_corpus
        freq_b_normalizada = float(freq_b)/tamanho_corpus

        freq_par_esperada_normalizada = freq_a_normalizada * freq_b_normalizada
        freq_par_normalizada = float(freq_par)/tamanho_corpus

        numerador = freq_par_normalizada - freq_par_esperada_normalizada
        denominador = sqrt(freq_par_esperada_normalizada)

        return numerador / denominador

    def tokenize(self, string, remover_vazias=False):
        splitada = re.split(self.get_regex(), string)
        return [t for t in splitada if t.strip()] if remover_vazias else splitada

    def ftokens(self, token_tagueado):
        # removendo numerais 
        return not token_tagueado[1] in ['CD', 'POS']

    def selecionar_par(self, mi, tscore):
        return mi >= 0 and tscore >= 0

    def percorrer_janela(self, raiz, janela, palavras_proibidas, palavras_ctxt):
        for p_viz in janela:
            try:
                if self.contadores[p_viz]:
                    if not p_viz in palavras_proibidas:
                        if not p_viz in palavras_ctxt[raiz]:
                            palavras_ctxt[raiz][p_viz] = 0
                        palavras_ctxt[raiz][p_viz] += 1
            except KeyError, ke: pass
        return palavras_ctxt

    def construir_rede(self, raizes_arg, nivel_maximo, janela):
        raizes = list(raizes_arg)
        palavras_proibidas = set(raizes)

        todos_objetos_niveis = []

        for nivel in range(1, nivel_maximo + 1):
            dir_obj_nivel = self.construir_nivel('nivel-%s.json' % nivel, raizes, janela, palavras_proibidas)

            todos_objetos_niveis.append(dir_obj_nivel)

            palavras_novo_nivel = []

            obj_nivel = Utilitarios.carregar_json(dir_obj_nivel)

            for raiz in obj_nivel.keys():
                palavras_novo_nivel += obj_nivel[raiz].keys()

            raw_input("%d é o total de novas palavras adicionadas para o mesmo nível" % len(palavras_novo_nivel))

            palavras_proibidas.update(palavras_novo_nivel)
            raizes = palavras_novo_nivel


#   palavras_proibidas = set
    def construir_nivel(self, nome_arq_saida, raizes, janela, set_palavras_proibidas):
        tam_corpus = sum(self.contadores.values())
        cont_coocorrencia = dict()
        resultado_metricas = dict()
        total_linhas = 0

        for raiz in raizes:
            set_palavras_proibidas.add(raiz)
            cont_coocorrencia[raiz] = dict()
            resultado_metricas[raiz] = dict()

        # recupera todos os documentos que contém palavras do contexto
        documentos_retornados = self.indexador.consultar_documentos(raizes)

        for doc in documentos_retornados:
            tmp = doc.replace('\t', ' ').split(' ')
            fr_tokenizada = []

            try:
                try:
                    # retirando a ID do documento
                    tokens_tmp = self.tokenize(unicode(doc.lower()), remover_vazias=True)[1:]
                    tokens_tagueados_tmp = pos_tag(tokens_tmp)
                except UnicodeDecodeError, ude:
                    traceback.print_exc()
                    raw_input('<enter>')
                    print('Retomando fluxo de execucao...')

                tokens_tagueados = [e for e in tokens_tagueados_tmp if self.ftokens(e)]
                fr_tokenizada = [e[0] for e in tokens_tagueados]                
            except Exception, e:
                traceback.print_exc()
                raw_input('<enter>')
                print('Retomando fluxo de execucao...')

            for raiz in raizes:
                try:
                    index = fr_tokenizada.index(raiz)

                    esq_ctxt = fr_tokenizada[index - janela : index]
                    dir_ctxt = fr_tokenizada[index + 1 : index + 1 + janela]

                    cont_coocorrencia = self.percorrer_janela(raiz, esq_ctxt, set_palavras_proibidas, cont_coocorrencia)
                    cont_coocorrencia = self.percorrer_janela(raiz, dir_ctxt, set_palavras_proibidas, cont_coocorrencia)
                                
                except ValueError, ve: pass
                except Exception, e:
                    traceback.print_exc()
                    raw_input('<enter>')
                    print('Retomando fluxo de execucao...')

            total_linhas += 1

        metrica_mi = dict()
        metrica_tscore = dict()

        # Calculando Mutual Information
        for raiz in cont_coocorrencia:
            metrica_mi[raiz] = dict()
            metrica_tscore[raiz] = dict()

            for viz in cont_coocorrencia[raiz]:
                freq_sin = self.contadores[raiz]
                freq_viz = self.contadores[viz]

                metrica_mi[raiz][viz] = self.calcular_mi(tam_corpus, cont_coocorrencia[raiz][viz], freq_sin, freq_viz, janela)
                metrica_tscore[raiz][viz] = self.calcular_tscore(tam_corpus, cont_coocorrencia[raiz][viz], freq_sin, freq_viz)

                mi, tscore = metrica_mi[raiz][viz], metrica_tscore[raiz][viz]
                resultado_metricas[raiz][viz] = {'t-score': tscore, 'mi': mi, 'co': cont_coocorrencia[raiz][viz]}

        caminho_json_saida = self.configs['aplicacao']['dir_saida_base_coocorrencia'] + '/' + nome_arq_saida
        self.salvar_json(caminho_json_saida, resultado_metricas)
        
        print('Salvando arquivo em: ' + caminho_json_saida)
        print('Fim desta funcao.')

        return caminho_json_saida

    def gerar_contador_palavras(self, dir_arq_corpus, caminho_saida):
        caminhos_corpus = carregar_caminhos_corpus(dir_arq_corpus)
        contadores = dict()

        print('\nGERADO DE CONTADORES\n')

        for a in caminhos_corpus:
            with open(a, 'r') as arq:
                print('Indexando palavras do arquivo ' + a)
                for l in arq:
                    try:
                        try:
                            fr_tokenizada = self.tokenize(unicode(l.lower()), remover_vazias=True)[1:]
                        except Exception, e:
                            fr_tokenizada = []

                        for token in fr_tokenizada:
                            if not token in contadores:
                                contadores[token] = 1
                            contadores[token] += 1

                    except Exception, e:
                        print(e)
                        traceback.print_exc()

        self.salvar_json(caminho_saida, contadores)

    # carrega caminho de corpus
    def carregar_caminhos_corpus(self, file):
        arq = open(file, 'r')
        caminhos = [e.replace('\n', '') for e in arq.readlines()]
        arq.close()

        return caminhos

    # carrega documento de sinonimos
    def carregar_sinonimos(self, caminho):
        arquivo_sinonimos = open(caminho, 'r')
        sinonimos_aproximados = []

        for ltmp in arquivo_sinonimos.readlines():
            l = ltmp.replace('\n', '')
            sinonimos_aproximados.append(l.split(','))

        arquivo_sinonimos.close()
        return sinonimos_aproximados

    # checa se a palavra esta na frase
    def contida(self, palavra, frase):
        palavra = palavra.lower()
        frase = frase.lower()

        if ' ' + palavra + ' ' in frase:
            return True
        if ' ' + palavra in  frase:
            return True
        for p in [',', '.', ';', '"']:
            if palavra + p in frase:
                return True

        return False

# -*- coding: utf-8 -*-
from ModuloUtilitarios.Utilitarios import Utilitarios
from nltk.corpus import stopwords as sw
from unidecode import unidecode
from nltk import word_tokenize
from math import log10, sqrt
from string import printable
from os import system, path
from nltk import pos_tag
from Indexador import *
from sys import argv
import traceback
import json
import nltk
import sys
import re

class AbordagemEdmonds(object):
    def __init__(self, indexador_whoosh, contadores):
        self.indexador = indexador_whoosh
        self.contadores = contadores

    def salvar_json(self, caminho_json_saida, palavras):        
        Utilitarios.salvar_json(caminho_json_saida, palavras)
        #try:
        #    obj_texto = json.dumps(palavras, indent=4, encoding='latin1')        
        #except UnicodeDecodeError, ude:
        #    pass

        #obj_json_saida = open(caminho_json_saida, 'w')
        #obj_json_saida.write(obj_texto)
        #obj_json_saida.close()

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

    def percorrer_janela(self, raiz, janela, freq_min, raizes, palavras_ctxt):
        for p_viz in janela:
            try:
                if self.contadores[p_viz] >= freq_min:
                    if not p_viz in raizes:
                        if not p_viz in palavras_ctxt[raiz]:
                            palavras_ctxt[raiz][p_viz] = 0
                        palavras_ctxt[raiz][p_viz] += 1
            except KeyError, ke: pass
        return palavras_ctxt

#   def calcular_mi(self, tamanho_corpus, freq_par, freq_a, freq_b, janela):
#   def calcular_tscore(self, tamanho_corpus, freq_par, freq_a, freq_b, janela=1):
    def construir_relacao_primeira_ordem(self, sinonimo, palavras_contexto):
        resultado = dict()
        tam_corpus = sum(self.contadores.values())
        freq_sinonimo = self.contadores[sinonimo]
        mi = self.calcular_mi(tam_corpus, palavras_ctxt[palavra][viz], freq_sin, freq_viz, janela)
        tscore = self.calcular_tscore(tam_corpus, palavras_ctxt[palavra][viz], freq_sin, freq_viz)
        return (mi, tscore)

    def construir_redes(self, configs, raizes, janela, freq_min):
        tam_corpus = sum(self.contadores.values())
        cont_coocorrencia = dict()
        total_linhas = 0

        for raiz in raizes: cont_coocorrencia[raiz] = dict()

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

                    cont_coocorrencia = self.percorrer_janela(raiz, esq_ctxt, freq_min, raizes, cont_coocorrencia)
                    cont_coocorrencia = self.percorrer_janela(raiz, dir_ctxt, freq_min, raizes, cont_coocorrencia)
                                
                except ValueError, ve: pass
                except Exception, e:
                    traceback.print_exc()
                    raw_input('<enter>')
                    print('Retomando fluxo de execucao...')

            total_linhas += 1

        metrica_mi = dict()
        metrica_tscore = dict()

        resultado = []

        # Calculando Mutual Information
        for raiz in cont_coocorrencia:
            metrica_mi[raiz] = dict()
            metrica_tscore[raiz] = dict()

            for viz in cont_coocorrencia[raiz]:
                freq_sin = self.contadores[raiz]
                freq_viz = self.contadores[viz]

                metrica_mi[raiz][viz] = self.calcular_mi(tam_corpus, cont_coocorrencia[raiz][viz], freq_sin, freq_viz, janela)
                metrica_tscore[raiz][viz] = self.calcular_tscore(tam_corpus, cont_coocorrencia[raiz][viz], freq_sin, freq_viz)

                if self.selecionar_par(metrica_mi[raiz][viz], metrica_tscore[raiz][viz]):
                    resultado.append((raiz, viz, metrica_mi[raiz][viz], metrica_tscore[raiz][viz]))

        caminho_json_saida = '-'.join(raizes)
        #self.salvar_json(caminho_json_saida, cont_coocorrencia)
        self.salvar_json(caminho_json_saida, resultado)
        raw_input('Salvando arquivo em: ' + caminho_json_saida)
        resultado = sorted(resultado, key=lambda e: e[2], reverse=True)
        raw_input('Fim desta funcao.')

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

    def init(acao, dir_arq_corpus, caminho_arquivo_sinonimos):
        index_corpus = '/media/isaias/ParticaoAlternat/LeipzigCorpus/Unificado/indexes'
        indexador = IndexadorWhoosh(index_corpus)
        dir_contadores = raw_input('Diretorio contadores: ')

        caminhos_corpus = carregar_caminhos_corpus(dir_arq_corpus)

        if acao == 'contadores':
            gerar_contador_palavras(dir_arq_corpus, dir_contadores)
        elif acao == 'redes':
            arq_contadores = open(dir_contadores, 'r')
            obj_contadores = json.loads(arq_contadores.read())
            arq_contadores.close()

            todos_grupos_sinonimos = carregar_sinonimos(caminho_arquivo_sinonimos)
            tamanho_janela = raw_input('Tamanho janela: ')

            for cluster in todos_grupos_sinonimos:
                ordem = 1
                ordem_max = 2
                construir_redes
                (
                    ordem_max,
                    ordem,
                    indexador,
                    obj_contadores,
                    list(cluster),
                    cluster,
                    int(tamanho_janela)
                )
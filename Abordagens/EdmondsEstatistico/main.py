# -*- coding: utf-8 -*-
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

def salvar_json(caminho_json_saida, palavras):
    try:
        obj_texto = json.dumps(palavras, indent=4, encoding='latin1')
    except UnicodeDecodeError, ude:
        pass

    obj_json_saida = open(caminho_json_saida, 'w')
    obj_json_saida.write(obj_texto)
    obj_json_saida.close()

def get_regex():
    rgx1 = u"\.|\,|\;|\s|\"|\-|\?|\!|\:|\t|\`|\_|\\(|\\)|\\[|\\]|@|\*"
    rgx2 = u"\u2019|\u201d|\u201f|\u2013|\u2014|\u2018"
    rgx3 = u"\u00e2|\u20ac|\u2122|\u0080"

    return rgx1+'|'+rgx2+'|'+rgx3

def calcular_mi(tamanho_corpus, freq_par, freq_a, freq_b, janela):
    numerador = (float(freq_par) * float(tamanho_corpus)) / (freq_a * freq_b * (janela * 2))
    return log10(numerador) / log10(2)

def calcular_tscore(tamanho_corpus, freq_par, freq_a, freq_b, janela=1):
    freq_a_normalizada = float(freq_a)/tamanho_corpus
    freq_b_normalizada = float(freq_b)/tamanho_corpus

    freq_par_esperada_normalizada = freq_a_normalizada * freq_b_normalizada
    freq_par_normalizada = float(freq_par)/tamanho_corpus

    numerador = freq_par_normalizada - freq_par_esperada_normalizada
    denominador = sqrt(freq_par_esperada_normalizada)

    return numerador / denominador

def tokenize(string, remover_vazias=False):
    regex = get_regex()

    splitada = re.split(regex, string)

    if remover_vazias:
        return [t for t in splitada if t.strip()]
    else:
        return splitada

def ftokens(token_tagueado):
    return not token_tagueado[1] in ['CD', 'POS']

def selecionar_par(mi, tscore):
    return mi >= 0 and tscore >= 0

def filtrar_corpus(ordem, dir_arq_corpus, pasta_corpus_filtrados, coocorrentes, sinonimos_principais):
    caminhos_corpus = carregar_caminhos_corpus(dir_arq_corpus)
    nome_arquivo_saida = pasta_corpus_filtrados + '/' + '-'.join(nearsynonyms-ASDF) + '-' + ssinonimos_principais'

    if not path.isfile(nome_arquivo_saida):
        filtro_texto  = '\|'.join(['\<' + e + '\>' for e in coocorrentes])

        for a in caminhos_corpus:
            comando = "cat %s | grep -i \"%s\" >> %s" % (a, filtro_texto, nome_arquivo_saida)
            if not system(comando):
                print('\nO comando para filtrar o corpus foi executado com sucesso!')
                print(comando + '\n')
    else:
        print("Arquivo '%s.txt' para o cluster ja existe!" % '-'.join(sinonimos_principais)

    return nome_arquivo_saida

def construir_redes
(
    ordem_max,
    ordem_atual,
    indexador,
    contadores,
    palavras_contexto,
    sinonimos_principais,
    janela,
    frequencia_minima    
):
    palavras = dict()
    tam_corpus = sum(contadores.values())
    contador_frequencia = dict()
    total_linhas = 0

    for p in palavras_contexto:
        contador_frequencia[p] = 0
        palavras[p] = dict()

    documentos = indexador.consultar_documentos(palavras_contexto)

    if True:
        for l in documentos:
            tmp = str(l).replace('\t', ' ').split(' ')
            fr_tokenizada = []

            try:
                try:
                    tokens = tokenize(unicode(l.lower()), remover_vazias=True)[1:]
                    tokens_tagueados = pos_tag(tokens)
                except UnicodeDecodeError, ude:
                    traceback.print_exc()
                    raw_input('<enter>')
                    print('Retomando fluxo de execucao...')

                tokens_tagueados_filtrados = [e for e in tokens_tagueados if ftokens(e)]
                fr_tokenizada = [e[0] for e in tokens_tagueados_filtrados]
            except Exception, e:
                traceback.print_exc()
                raw_input('<enter>')
                print('Retomando fluxo de execucao...')

            for p in palavras_contexto:
                try:
                    index = fr_tokenizada.index(p)
                    esq = fr_tokenizada[index - janela : index]
                    dir = fr_tokenizada[index + 1 : index + 1 + janela]

                    contador_frequencia[p] += 1

                    for e in esq:
                        if contadores[e] >= frequencia_minima:
                            if not e in sinonimos_principais:
                                if not e in palavras[p]: palavras[p][e] = 0
                                palavras[p][e] += 1
                    for d in dir:
                        if contadores[d] >= frequencia_minima:
                            if not d in sinonimos_principais:
                                if not d in palavras[p]: palavras[p][d] = 0
                                palavras[p][d] += 1

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
    for p in palavras:
        metrica_mi[p] = dict()
        metrica_tscore[p] = dict()

        for viz in palavras[p]:
            freq_sin = contadores[p]
            freq_viz = contadores[viz]

            metrica_mi[p][viz] = calcular_mi(tam_corpus, palavras[p][viz], freq_sin, freq_viz, janela)
            metrica_tscore[p][viz] = calcular_tscore(tam_corpus, palavras[p][viz], freq_sin, freq_viz)

            if selecionar_par(metrica_mi[p][viz], metrica_tscore[p][viz]):
                resultado.append((p, viz, metrica_mi[p][viz], metrica_tscore[p][viz]))

    caminho_json_saida = '-'.join(sinonimos_principais) + ' - ' + str(ordem_atual)
    salvar_json(caminho_json_saida, palavras)

    resultado = sorted(resultado, key=lambda e: e[2], reverse=True)

    if ordem_atual < ordem_max:
        coocorrentes = []

        for p in palavras:
            coocorrentes += [v for v in palavras[p]]

        construir_redes
        (
            ordem_max,
            ordem_atual + 1,
            indexador,
            contadores,
            coocorrentes,
            sinonimos_principais,
            janela,
            frequencia_minima
        )

def gerar_contador_palavras(dir_arq_corpus, caminho_saida):
    caminhos_corpus = carregar_caminhos_corpus(dir_arq_corpus)
    contadores = dict()

    print('\nGERADO DE CONTADORES\n')

    for a in caminhos_corpus:
        with open(a, 'r') as arq:
            print('Indexando palavras do arquivo ' + a)
            for l in arq:
                try:
                    try:
                        fr_tokenizada = tokenize(unicode(l.lower()), remover_vazias=True)[1:]
                    except Exception, e:
                        fr_tokenizada = []

                    for token in fr_tokenizada:
                        if not token in contadores:
                            contadores[token] = 1
                        contadores[token] += 1

                except Exception, e:
                    print(e)
                    traceback.print_exc()

    salvar_json(caminho_saida, contadores)

def carregar_caminhos_corpus(file):
    arq = open(file, 'r')
    caminhos = [e.replace('\n', '') for e in arq.readlines()]
    arq.close()

    return caminhos

def carregar_sinonimos(caminho):
    arquivo_sinonimos = open(caminho, 'r')
    sinonimos_aproximados = []

    for l in arquivo_sinonimos.readlines():
        l2 = str(l).replace('\n', '')
        sinonimos_aproximados.append(l2.split(','))

    arquivo_sinonimos.close()
    return sinonimos_aproximados

def contida(palavra, frase):
    if ' ' + palavra + ' ' in frase:
        return True
    if ' ' + palavra in  frase:
        return True
    for p in [',', '.', ';', '"']:
        if palavra + p in frase:
            return True

    return False


if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf8')

    index_corpus = '/media/isaias/ParticaoAlternat/LeipzigCorpus/Unificado/indexes'
    indexador = IndexadorWhoosh(index_corpus)
    dir_contadores = raw_input('Diretorio contadores: ')

    try:
        acao, dir_arq_corpus, caminho_arquivo_sinonimos = argv[1:]
    except:
        print('\nTENTE:\n')
        print('py main.py contadores <dir_arq_corpus> <caminho_arquivos_sinonimos>')
        print('py main.py redes <dir_arq_corpus> <caminho_arquivos_sinonimos>')

        exit(0)

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

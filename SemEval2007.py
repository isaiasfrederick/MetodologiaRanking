#! coding: utf-8
from RepositorioCentralConceitos import BaseUnificadaOxford
from Abordagens import IndexadorWhoosh, AbordagemEdmonds
from ModuloBasesLexicas.ModuloClienteBabelNetAPI import ClienteBabelAPI
from ModuloExtrator.InterfaceAbordagens import InterfaceAbordagens
from ModuloBasesLexicas.ModuloClienteOxfordAPI import *
from pywsd.lesk import cosine_lesk as cosine_lesk
from nltk.corpus import wordnet as wordnet
import xml.etree.ElementTree as ET
from os.path import isfile, join
from operator import itemgetter
from random import shuffle
from Utilitarios import *
from lxml import etree
from os import listdir
from os import system
from sys import argv
import traceback
import operator
import os.path
import copy
import io
import re

class ValidadorSemEval(object):
    def __init__(self, configs):
        self.configs = configs

        self.dir_respostas_competidores = configs['semeval2007']['dir_resultados_concorrentes']
        self.gold_file_test = configs['semeval2007']['test']['gold_file']
        self.comando_scorer = configs['semeval2007']['comando_scorer']
        self.dir_tmp = configs['dir_temporarios']

        self.todas_abordagens = dict()

    # Gera o score das metricas das tarefas do SemEval para as abordagens originais da
    def obter_score_participantes_originais(self, tarefa):
        resultados_json = {}
        todos_participantes = [p for p in self.listar_arq(self.dir_respostas_competidores) if '.' + tarefa in p]

        for participante in todos_participantes:
            resultados_json[participante] = self.obter_score(self.dir_respostas_competidores, participante)

        return resultados_json

    # Recupera o score das abordagens posteriores à competição
    def obter_score_participantes_posteriores(self):
        pass

    def obter_score(self, dir_pasta_submissao, participante):
        tarefa = participante.split('.')[1]
        arquivo_tmp = "%s/%s.tmp" % (self.dir_tmp, participante)

        if dir_pasta_submissao[-1] == "/":
            dir_pasta_submissao = dir_pasta_submissao[:-1]

        comando_scorer = self.comando_scorer
        dir_entrada = dir_pasta_submissao + '/' + participante
        dir_saida = dir_pasta_submissao + '/' + arquivo_tmp

        args = (comando_scorer, dir_entrada, self.gold_file_test, tarefa, arquivo_tmp)

        comando = "perl %s %s %s -t %s > %s" % args

        system(comando)

        # Le a saida do formatoo <chave>:<valor> por linha
        obj = self.ler_registro(arquivo_tmp)
        obj['nome'] = participante

        system('rm ' + arquivo_tmp)

        return obj

    def listar_arq(self, dir_arquivos):
        return [f for f in listdir(dir_arquivos) if isfile(join(dir_arquivos, f))]

    def filtrar_participantes(self, participantes, tarefa):
        return [p for p in participantes if tarefa in p]

    def ler_registro(self, path_arquivo):
        obj = {}
        arq = open(str(path_arquivo), 'r')
        linhas = arq.readlines()

        for l2 in linhas:
            try:
                l = str(l2).replace('\n','')
                chave, valor = l.split(':')
                obj[chave] = float(valor)
            except: pass

        arq.close()
        return obj

    def ler_entrada_teste(self, dir_arquivo_teste):
        todos_lexelts = dict()

        parser = etree.XMLParser(recover=True)
        arvore_xml = ET.parse(dir_arquivo_teste, parser)
        raiz = arvore_xml.getroot()

        for lex in raiz.getchildren():
            todos_lexelts[lex.values()[0]] = [ ]
            for inst in lex.getchildren():
                codigo = str(inst.values()[0])
                context = inst.getchildren()[0]
                frase = "".join([e for e in context.itertext()]).strip()

                palavra = inst.getchildren()[0].getchildren()[0].text
                todos_lexelts[lex.values()[0]].append({'codigo': codigo, 'frase': frase, 'palavra': palavra})

        return todos_lexelts

    # Formata a submissao para o padrao da competicao, que é lido pelo script Perl
    def formatar_submissao(self, nome_abordagem, entrada):
        metrica = nome_abordagem.split('.').pop()

        todas_metricas = self.configs['semeval2007']['tarefas']
        limite_respostas = int(todas_metricas['limites'][metrica])

        dir_arquivo_saida = self.configs['dir_saidas_rankeador'] + '/' + nome_abordagem
        arquivo_saida = open(dir_arquivo_saida, 'w')

        separador = todas_metricas['separadores'][metrica]

        for lemma in entrada:
            for id_entrada in entrada[lemma]:
                respostas = entrada[lemma][id_entrada][:limite_respostas]
                args = (lemma, id_entrada, separador, ';'.join(respostas))
                arquivo_saida.write("%s %s %s %s\n" % args)
        
        arquivo_saida.close()

        return nome_abordagem

    # Formata a submissao para o padrao da competicao, que é lido pelo script Perl
    def formatar_submissao_final(self, dir_arquivo_saida, entrada, limite_resposta, separador):
        arquivo_saida = open(dir_arquivo_saida, 'w')

        for lexelt in entrada:
            respostas = entrada[lexelt][:limite_resposta]
            args = (lexelt, separador, ';'.join(respostas))
            arquivo_saida.write("%s %s %s\n" % args)
        
        arquivo_saida.close()

    def carregar_gabarito(self, dir_gold_file):
        arquivo_gold = open(dir_gold_file, 'r')
        todas_linhas = arquivo_gold.readlines()
        arquivo_gold.close()

        saida = dict()
        separador = " :: "

        todas_linhas = [linha for linha in todas_linhas if linha != "\n"]

        for linha in todas_linhas:
            resposta_linha = dict()
            try:
                ltmp = str(linha).replace('\n', '')
                chave, sugestoes = ltmp.split(separador)
                sugestoes = [s for s in sugestoes.split(';') if s]

                for sinonimo in sugestoes:
                    sinonimo_lista = str(sinonimo).split(' ')
                    votos = int(sinonimo_lista.pop())
                    sinonimo_final = ' '.join(sinonimo_lista)
                
                    resposta_linha[sinonimo_final] = votos
                saida[chave] = resposta_linha
            except:
                traceback.print_exc()
        
        return saida

    # Carregar arquivos Submissão SemEval 2007 (formatado com o padrao SemEval)
    def carregar_arquivo_submissao(self, configs, dir_arquivo, tarefa="oot"):
        arquivo_submetido = open(dir_arquivo, 'r')
        todas_linhas = arquivo_submetido.readlines()
        arquivo_submetido.close()

        saida = dict()

        separador = configs['semeval2007']['tarefas']['separadores'][tarefa]
        separador = " " + separador + " "

        total_sugestoes = 0

        for linha in todas_linhas:
            resposta_linha = dict()
            try:
                ltmp = str(linha).replace('\n', '')

                chave, sugestoes = ltmp.split(separador)
                todos_candidatos = sugestoes.split(';')
                indice = 0

                for sinonimo in todos_candidatos:
                    if sinonimo != "":
                        sinonimo_lista = sinonimo
                        votos = len(todos_candidatos) - indice           
                        resposta_linha[sinonimo] = votos

                    indice += 1

                saida[chave] = resposta_linha
            except:
                traceback.print_exc()
        
        return saida
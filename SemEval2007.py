#! coding: utf-8
from RepositorioCentralConceitos import BaseOx
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


class VlddrSemEval(object):
    def __init__(self, cfgs):
        self.cfgs = cfgs

        cfgs_se = cfgs['semeval2007']
        dir_se = cfgs['caminho_raiz_bases']+'/'+cfgs['semeval2007']['dir_raiz']

        self.dir_resp_compet = dir_se+'/'+cfgs_se['dir_resultados_concorrentes']
        self.gold_file_test = dir_se+'/'+cfgs_se['test']['gold_file']
        self.comando_scorer = dir_se+'/'+cfgs_se['comando_scorer']
        self.dir_tmp = cfgs['caminho_raiz_bases']+'/'+cfgs['dir_temporarios']

        self.todas_abordagens = dict()

    # Gera o score das metricas das tarefas do SemEval para as abordagens originais da competicao
    def aval_parts_orig(self, tarefa, pos_filtradas=None, lexelts_filtrados=None):
        # Alias para funcao
        carregar_submissao = self.carregar_arquivo_submissao

        pos_semeval = self.cfgs['semeval2007']['todas_pos']

        todos_participantes = [p for p in Util.list_arqs(self.dir_resp_compet) if '.'+tarefa in p]
        todos_participantes = [p for p in todos_participantes if not '-' in p]

        if pos_filtradas in [None, []]:
            pos_filtradas = pos_semeval

        # Filtrando participante por POS
        todos_participantes_tmp = list(todos_participantes)
        todos_participantes = []

        for participante in todos_participantes_tmp:
            cfgs_tarefa = self.cfgs['semeval2007']['tarefas']

            max_sugestoes = int(cfgs_tarefa['limites'][tarefa])
            separador = cfgs_tarefa['separadores'][tarefa]

            dir_arq_original = self.dir_resp_compet+"/"+participante
            predicao_filtr = carregar_submissao(self.cfgs,\
                            dir_arq_original, tarefa,\
                            pos_filtradas=pos_filtradas,\
                            lexelts_filtrados=lexelts_filtrados)

            # Convertendo o nome do arquivo original
            # para o nome do arquivo filtrado por POS-tags
            # SWAG.oot" => "SWAG-n.oot
            velho_sufixo = '.'+tarefa
            novo_sufixo = "-%s%s"%("".join(pos_filtradas), velho_sufixo)
            dir_arq_filtrado = dir_arq_original.replace(velho_sufixo, novo_sufixo)

            if lexelts_filtrados in [None, []]:
                lexelts_filtrados = predicao_filtr.keys()
            else:
                lexelts_filtrados = list(set(lexelts_filtrados)&set(predicao_filtr.keys()))

            # Convertendo a resposta do formato dicionario para list
            for lexelt in lexelts_filtrados:
                resp_list = sorted(predicao_filtr[lexelt].items(), key=lambda x: x[1], reverse=True)
                resp_list = [e[0] for e in resp_list]
                #if lexelt in casos_filtrados or True: pass
                predicao_filtr[lexelt] = resp_list

            # Formatando arquivo filtrado
            self.formtr_submissao(dir_arq_filtrado, predicao_filtr, max_sugestoes, separador)
            # Retirando nome do participante, porém sem o diretorio que o contém
            todos_participantes.append(dir_arq_filtrado.split("/")[-1])

        resultados_json = {}

        for participante in todos_participantes:
            resultados_json[participante] = self.obter_score(self.dir_resp_compet, participante)

        # Se filtro de POS fora ativado, limpe os arquivos com submissao filtrada por POS-tags
        if pos_filtradas != pos_semeval:
            for participante in todos_participantes:
                pass
                #Util.limpar_arquivo('%s/%s'%(self.dir_resp_compet, participante))

        return resultados_json

    # Checa se dada submissao nao sugeriu uma misera instancia contendo resposta!
    def submissao_invalida(self, dir_entrada, tarefa):
        submissao = self.carregar_arquivo_submissao(self.cfgs, dir_entrada, tarefa)
        resp = False
        for lexelt in submissao:
            if len(submissao[lexelt]) > 0:
                resp = True
        return resp == False

    # Executa o script Perl para gerar o score das abordagens
    def obter_score(self, dir_pasta_submissao, participante):
        tarefa = participante.split('.')[1]
        arquivo_tmp = "%s/%s.tmp" % (self.dir_tmp, participante)

        if dir_pasta_submissao[-1] == "/":
            dir_pasta_submissao = dir_pasta_submissao[:-1]

        comando_scorer = self.comando_scorer
        dir_entrada = dir_pasta_submissao+'/'+participante
        dir_saida = dir_pasta_submissao+'/'+arquivo_tmp

        if self.submissao_invalida(dir_entrada, tarefa):
            raise Exception("Esta submissao ('%s') nao sugeriu respostas!" % participante)

        args = (comando_scorer, dir_entrada,
                self.gold_file_test, tarefa, arquivo_tmp)

        comando = "perl %s %s %s -t %s > %s" % args

        try:
            system(comando)

            # Le a saida do formatoo <chave>:<valor> por linha
            obj = self.ler_registro(arquivo_tmp)
            obj['nome'] = participante

            system('rm ' + arquivo_tmp)

            return obj
        except Exception, e:
            print(e)
            return None

    def filtrar_participantes_tarefa(self, participantes, tarefa):
        return [p for p in participantes if tarefa in p]

    def ler_registro(self, path_arquivo):
        obj = dict()
        arq = open(str(path_arquivo), 'r')
        linhas = arq.readlines()

        for linha_tmp in linhas:
            try:
                l = str(linha_tmp).replace('\n', '')
                chave, valor = l.split(':')
                obj[chave] = float(valor)
            except:
                pass

        arq.close()
        return obj

    # Formata a submissao para o padrao da competicao, que é lido pelo script Perl
    def formtr_submissao(self, dir_arquivo_saida, predicao, max_sugestoes, separador):
        if predicao in [set(), None]:
            return

        arquivo_saida = open(dir_arquivo_saida, 'w')

        for lexelt in predicao:            
            try:
                respostas = predicao[lexelt][:max_sugestoes]
                args = (lexelt, separador, ';'.join(respostas))
                arquivo_saida.write("%s %s %s\n" % args)
            except: pass

    # Carregar o caso de entrada para gerar o ranking de sinonimos
    def carregar_caso_entrada(self, dir_arq_caso_entrada, padrao_se=False):
        todos_lexelts = dict()

        parser = etree.XMLParser(recover=True)
        arvore_xml = ET.parse(dir_arq_caso_entrada, parser)
        raiz = arvore_xml.getroot()

        for lex in raiz.getchildren():
            todos_lexelts[lex.values()[0]] = []
            for inst in lex.getchildren():
                codigo = str(inst.values()[0])
                context = inst.getchildren()[0]
                frase = "".join([e for e in context.itertext()]).strip()

                palavra = inst.getchildren()[0].getchildren()[0].text
                todos_lexelts[lex.values()[0]].append(
                    {'codigo': codigo, 'frase': frase, 'palavra': palavra})

        if padrao_se:
            todos_lexelts_tmp = dict(todos_lexelts)
            todos_lexelts = dict()

            for lexelt in todos_lexelts_tmp:
                for reg in todos_lexelts_tmp[lexelt]:
                    novo_lexelt = "%s %s"%(lexelt, str(reg['codigo']))
                    todos_lexelts[novo_lexelt] = reg

        return todos_lexelts

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
                chave, sugestoes = str(linha).replace(
                    '\n', '').split(separador)
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
    def carregar_arquivo_submissao(self, cfgs, dir_arquivo,\
                    tarefa="oot",pos_filtradas=[], lexelts_filtrados=[]):

        if pos_filtradas in [[], None]:
            # Assumindo valor default => ['a', 'v', 'n', 'r']
            pos_filtradas = cfgs['semeval2007']['todas_pos']

        arquivo_submetido = open(dir_arquivo, 'r')
        todas_linhas = arquivo_submetido.readlines()
        arquivo_submetido.close()

        # Predicao filtrada por POS-tags
        saida_filtrada_pos = dict()
        # Predicao filtrada pelos LEXELTS permitidos
        saida_filtrada_lexelt = dict()

        separador = cfgs['semeval2007']['tarefas']['separadores'][tarefa]
        separador = " " + separador + " "

        total_sugestoes = 0

        for linha in todas_linhas:
            resposta_linha = dict()
            try:
                chave, sugestoes = str(linha).replace('\n', '').split(separador)
                # "cry.v 893" => ["cry", "v", "893"]
                lema_tmp, pos_tmp, lema_id_tmp = re.split('[\.\s]', chave)

                if pos_tmp in pos_filtradas:
                    todos_candidatos = sugestoes.split(';')
                    indice = 0

                    for sinonimo in todos_candidatos:
                        if sinonimo != "":
                            sin_lista = sinonimo
                            votos = len(todos_candidatos)-indice
                            resposta_linha[sinonimo] = votos

                        indice+=1

                    saida_filtrada_pos[chave] = resposta_linha

                # Filtro por Lexelt, None ou [] sao valores Default
                if chave in lexelts_filtrados or lexelts_filtrados == []:
                    saida_filtrada_lexelt[chave] = resposta_linha

            except:  # Se linha está sem predição
                pass

        saida = dict()
        for lexelt in set(saida_filtrada_pos)&set(saida_filtrada_lexelt):
            saida[lexelt] = saida_filtrada_pos[lexelt]

        return saida

    # Ordena o gabarito padrao anotado SemEval2007 por frequencia de votos
    def fltr_gabarito(self, gabarito):
        try:
            return sorted(gabarito, key=lambda x: x[1], reverse=True)
        except:
            return []

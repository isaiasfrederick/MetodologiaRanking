from os import system
from os import listdir
from os.path import isfile, join
import xml.etree.ElementTree as ET
from lxml import etree
import operator

class ValidadorRankingSemEval2007(object):
    def __init__(self, configs):
        self.configs = configs

        self.dir_respostas = configs['semeval2007']['dir_resultados_concorrentes']
        self.gold_file = configs['semeval2007']['trial']['gold_file']
        self.scorer = configs['semeval2007']['trial']['scorer']
        self.dir_tmp = configs['dir_temporarios']

    def obter_score_participantes(self, metrica):
        resultados_json = {}

        todos_participantes_best = [p for p in self.listar_arq(self.dir_respostas) if '.' + metrica in p]

        for participante in todos_participantes_best:
            resultados_json[participante] = self.calcular_score_abordagem(self.dir_respostas, participante)

        return resultados_json

    def calcular_score_abordagem(self, dir_respostas, participante):
        import os.path

        metrica = participante.split('.')[1]
        arquivo_tmp = self.dir_tmp + '/' + participante.replace('.' + metrica, '.tmp')

        comando_scorer = self.scorer
        dir_entrada = dir_respostas + '/' + participante
        dir_saida = dir_respostas + '/' + arquivo_tmp

        args = (comando_scorer, dir_entrada, self.gold_file, metrica, arquivo_tmp)

        comando = "perl %s %s %s -t %s > %s" % args
        system(comando)

        obj = self.ler_registro(arquivo_tmp)
        obj['nome'] = participante

        system('rm ' + arquivo_tmp)

        return obj

    def ordenar_scores(self, lista_scores, valor):
        lista_scores.sort(key=operator.itemgetter(valor))
        lista_scores.reverse()

        return lista_scores

    def listar_arq(self, dir_arquivos):
        return [f for f in listdir(dir_arquivos) if isfile(join(dir_arquivos, f))]

    def filtrar_participantes(self, participantes, metrica):
        return [p for p in participantes if metrica in p]

    def ler_registro(self, path_arquivo):
        obj = {}
        arq = open(str(path_arquivo), 'r')
        linhas = arq.readlines()

        for l in linhas:
            try:
                chave, valor = l.split(':')
                obj[chave] = float(valor) if float(valor) % 1 else int(valor)
            except: pass

        arq.close()
        return obj

    def ler_entrada_teste(self, dir_arquivo_teste):
        todos_lexelts = dict()

        parser = etree.XMLParser(recover=True)
        arvore_xml = ET.parse(dir_arquivo_teste, parser)
        raiz = arvore_xml.getroot()

        for lex in raiz.getchildren():
            todos_lexelts[lex.values()[0]] = []
            for inst in lex.getchildren():
                codigo = str(inst.values()[0])
                context = inst.getchildren()[0]
                frase = "".join([e for e in context.itertext()]).strip()

                palavra = inst.getchildren()[0].getchildren()[0].text
                todos_lexelts[lex.values()[0]].append({'codigo': codigo, 'frase': frase, 'palavra': palavra})

        return todos_lexelts

    def formatar_submissao(self, nome_abordagem, entrada):
        metrica = nome_abordagem.split('.').pop()

        todas_metricas = self.configs['semeval2007']['metricas']
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


class ValidadorGeneralizedAveragePrecision(object):
    def __init__(self):
        pass
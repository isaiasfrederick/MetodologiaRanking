# -*- coding: utf-8 -*-
from os import system
import requests
import glob
import json
import os
import re, math
from collections import Counter
from unicodedata import normalize
from sys import version_info
import random, string
import unicodedata
import re, math
import os
from nltk.corpus import stopwords
from collections import Counter
import requests


class Utilitarios(object):
    @staticmethod
    def requisicao_http(url, headers=None):
        if headers:
            res = requests.get(url, headers = headers)
        else:
            res = requests.get(url)

        return res if res.status_code == 200 else None

    @staticmethod
    def conversor_pos(pos_wordnet):
        pos = pos_wordnet
        #ADJ, ADJ_SAT, ADV, NOUN, VERB = 'a', 's', 'r', 'n', 'v'

        if pos == 'n': pos = 'Noun'
        elif pos == 'v': pos = 'Verb'
        elif pos == 'r': pos = 'Adverb'
        elif pos == 'a': pos = 'Adjective'
        else: pos = ''

        return pos

    @staticmethod
    def multipalavra(palavra):
        return '-' in palavra or ' ' in palavra or '_' in palavra

    @staticmethod
    def remover_multipalavras(lista):
        return [e for e in lista if Utilitarios.multipalavra(e) == False]

    @staticmethod
    def carregar_configuracoes(dir_configs):
        arq = open(dir_configs, 'r')
        obj = json.loads(arq.read())
        arq.close()
        
        return obj

    @staticmethod
    def cosseno(doc1, doc2):
        vec1 = Utilitarios.doc_para_vetor(doc1.lower())
        vec2 = Utilitarios.doc_para_vetor(doc2.lower())

        intersection = set(vec1.keys()) & set(vec2.keys())
        numerator = sum([vec1[x] * vec2[x] for x in intersection])

        sum1 = sum([vec1[x]**2 for x in vec1.keys()])
        sum2 = sum([vec2[x]**2 for x in vec2.keys()])
        denominator = math.sqrt(sum1) * math.sqrt(sum2)

        if denominator:
            return float(numerator) / denominator
        else:
            return 0.0

    @staticmethod
    def jaccard(doc1, doc2):
        doc1 = set(doc1.split())
        doc2 = set(doc2.split())

        return float(len(doc1 & doc2)) / len(doc1 | doc2)

    @staticmethod
    def juntar_tokens(array):
        saida = ""

        for token in array:
            saida += re.sub('[_-]', ' ', token) + ' '

        return list(set(saida[:-1].split(' ')))

    @staticmethod
    def doc_para_vetor(text):
        WORD = re.compile(r'\w+')
        words = WORD.findall(text)
        words = text.split(' ')

        return Counter(words)

    @staticmethod
    def carregar_json(diretorio):
        try:
            arq = open(diretorio, 'r')
            obj = json.loads(arq.read())
            arq.close()

            return obj

        except:
            return None

    @staticmethod
    def deletar_arquivo(dir_arquivo):
        system("rm " + dir_arquivo)

    @staticmethod
    def limpar_diretorio_temporarios(configs):
        os.system('rm ' + configs['dir_temporarios'] + '/*')

    @staticmethod
    def salvar_json(diretorio, obj):
        try:
            arq = open(diretorio, 'w')
            obj_serializado = json.dumps(obj, indent=4)
            arq.write(obj_serializado)
            arq.close()

            return True
        except:
            return False

    @staticmethod
    def listar_arquivos(diretorio):
        return glob.glob(diretorio + '/*')

    @staticmethod
    def limpar_console():
        system('clear')

    @staticmethod
    def retornar_valida(frase):
        frase = Utils.remove_acentos(frase)
        frase = re.sub('[?!,;]', '', frase)
        frase = frase.replace("\'", " ")
        frase = frase.replace("-", " ")
        frase = frase.replace("\'", "")
        frase = frase.replace("\\`", "")
        frase = frase.replace("\"", "")
        frase = frase.replace("\n", " ")

        return frase.strip().lower()

    @staticmethod
    def retornar_valida(frase, lower=True, strip=True):
        frase = Utils.remove_acentos(frase)
        frase = re.sub('[?!,;]', '', frase)
        frase = frase.replace("\'", " ")
        frase = frase.replace("-", " ")
        frase = frase.replace("\'", "")
        frase = frase.replace("\\`", "")
        frase = frase.replace("\"", "")
        frase = frase.replace("\n", " ")

        if lower: frase = frase.lower()
        if strip: frase = frase.strip()

        return frase

    @staticmethod
    def remove_acentos(cadeia, codif='utf-8'):
        if version_info[0] == 2:
            try:
                return normalize('NFKD', cadeia.decode(codif)).encode('ASCII','ignore')
            except: pass
        elif version_info[0] == 3:
            try:
                return normalize('NFKD', cadeia).encode('ASCII', 'ignore').decode('ASCII')
            except: pass

        return cadeia

    @staticmethod
    def retornar_valida_pra_indexar(frase):
        frase = Utilitarios.remove_acentos(frase)
        frase = re.sub('[(\[?!,;.\])]', ' ', frase)
        frase = frase.replace("\'", " ")
        frase = frase.replace("-", " ")
        frase = frase.replace(":", " ")
        frase = frase.replace("@", " ")
        frase = frase.replace("\'", " ")
        frase = frase.replace("/", " ")
        frase = frase.replace("\\`", " ")
        frase = frase.replace("\"", " ")
        frase = frase.replace("\n", " ")

        frase = ''.join(e for e in frase if (e.isalnum() and not e.isdigit()) or e == ' ')

        return frase.strip().lower()

    @staticmethod
    def obter_peso_frase(frase):
        frequencias = Utils.obter_frequencias_frase(frase)
        soma = sum([e[1] for e in frequencias])

        return (soma / len(frequencias), frequencias)

    @staticmethod
    def is_stop_word(p):
        return p in stopwords.words('english')
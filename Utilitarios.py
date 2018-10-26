# -*- coding: utf-8 -*-
from os import system
import requests
import glob
import json
import os
import re, math
from collections import Counter
from pywsd.utils import lemmatize, porter, lemmatize_sentence
from unicodedata import normalize
from sys import version_info
import random, string
import unicodedata
import re, math
import os
from nltk.corpus import stopwords
from collections import Counter
import requests
from nltk import pos_tag as pt, word_tokenize as wt
from nltk.corpus import stopwords, wordnet

wn = wordnet

class Util(object):
    configs = None
    # Contadores Corpus
    contadores = None

    @staticmethod
    def normalizar_palavra(palavra):
        try: return palavra
        except: pass

        return palavra

    @staticmethod
    def requisicao_http(url, headers=None):
        if headers:
            res = requests.get(url, headers = headers)
        else:
            res = requests.get(url)

        return res if res.status_code == 200 else None

    @staticmethod
    def conversor_pos_wn_oxford(pos):
        #ADJ, ADJ_SAT, ADV, NOUN, VERB = 'a', 's', 'r', 'n', 'v'
        
        if pos == 'n': pos = 'Noun'
        elif pos == 'v': pos = 'Verb'
        elif pos == 'r': pos = 'Adverb'
        elif pos == 'a': pos = 'Adjective'

        return pos

    @staticmethod
    def conversor_pos_semeval_wn(pos):
        if pos == 'a': return 's'
        
        return pos

    @staticmethod
    def conversor_pos_oxford_wn(pos):
        if pos in ['Noun', 'Verb', 'Adjective']:
            return pos[0].lower()
        elif pos == 'Adverb':
            return 'r'
        elif pos == 'Conjunction':
            return 'r'

        return pos

    @staticmethod
    def descontrair(txt):
        # specific
        txt = re.sub(r"won't", "will not", txt)
        txt = re.sub(r"can\'t", "can not", txt)

        # general
        txt = re.sub(r"n\'t", " not", txt)
        txt = re.sub(r"\'re", " are", txt)
        txt = re.sub(r"\'s", " is", txt)
        txt = re.sub(r"\'d", " would", txt)
        txt = re.sub(r"\'ll", " will", txt)
        txt = re.sub(r"\'t", " not", txt)
        txt = re.sub(r"\'ve", " have", txt)
        txt = re.sub(r"\'m", " am", txt)
        return txt

    @staticmethod
    def e_multipalavra(palavra):
        return '-' in palavra or ' ' in palavra or '_' in palavra

    @staticmethod
    def remover_multipalavras(lista):
        return [e for e in lista if Util.e_multipalavra(e) == False]

    @staticmethod
    def carregar_configuracoes(dir_configs):
        arq = open(dir_configs, 'r')
        obj = json.loads(arq.read())
        arq.close()
        
        Util.configs = obj

        return obj

    @staticmethod
    def cosseno(doc1, doc2):
        vec1 = Util.doc_para_vetor(doc1.lower())
        vec2 = Util.doc_para_vetor(doc2.lower())

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
    def abrir_json(diretorio, criar=False):
        try:
            arq = open(diretorio, 'r')
        except Exception, e:
            if criar == False: return None

        try:
            obj = json.loads(arq.read())
        except Exception:
            arq = open(diretorio, 'w')
            arq.write("{ }")
            obj = { }

        if arq.closed == False: arq.close()
        return obj

    @staticmethod
    def deletar_arquivo(dir_arquivo):
        system("rm " + dir_arquivo)

    @staticmethod
    def limpar_diretorio_temporarios(configs):
        os.system('rm ' + configs['dir_temporarios'] + '/*')

    @staticmethod
    def limpar_diretorio(configs, diretorio):
        os.system('rm ' + diretorio + '/*')

    @staticmethod
    def obter_synsets(palavra, pos_semeval):
        if pos_semeval != 'a':
            return wordnet.synsets(palavra, pos_semeval)
        else:
            saida = [ ]

            for pos in ['a', 's']: # adjective e adjective sattelite
                saida += wordnet.synsets(palavra, pos)

            return saida

    # RETIRA AS PONDERACOES DE ACORDO COM A POS DESEJADA DA WORDNET
    @staticmethod
    def filtrar_ponderacoes(pos_semeval, ponderacoes):
        lista_pos = ['s', 'a'] if pos_semeval == 'a' else [pos_semeval]

        return [e for e in ponderacoes if e[0].pos() in lista_pos]

    @staticmethod
    def salvar_json(diretorio, obj):
        try:
            arq = open(diretorio, 'w')
            obj_serializado = json.dumps(obj, indent=4)
            arq.write(obj_serializado)
            arq.close()

            return True
        except:
            import traceback
            traceback.print_exc()
            raw_input('ERRO')
            return False

    @staticmethod
    def extrair_sinonimos_candidatos_definicao(definicao, pos):
        #ADJ, ADJ_SAT, ADV, NOUN, VERB = 'a', 's', 'r', 'n', 'v'

        if not type(pos) in [str, unicode]:
            print('\n\n')
            print('\nTipo POS: ' + str(type(pos)))

            traceback.print_stack()
            sys.exit(1)

        wn = wordnet

        if pos.__len__() > 1:
            pos = Util.conversor_pos_oxford_wn(pos)

        associacoes = dict()

        associacoes['n'] = ['N']
        associacoes['v'] = ['v', 'J']
        associacoes['a'] = ['R', 'J']
        associacoes['s'] = ['R', 'J']
        associacoes['r'] = ['R', 'J']
        associacoes = None
        
        try:
            resultado_tmp =  [p for p in pt(wt(definicao.lower())) if not p[0] in stopwords.words('english')]
        except:
            raw_input('\nDefinicoes que geraram excecao: ' + str(definicao) + '\n')

        resultado = [ ]

        try:
            for l, pos_iter in resultado_tmp:
                if wn.synsets(l, pos):
                    resultado.append(l)

        except:
            # retirando pontuacao
            tmp = [p[0] for p in resultado_tmp if len(p[0]) > 1]

            for l in tmp:
                try:
                    if wn.synsets(l, pos):
                        raw_input('Adicionando %s para %s' % (l, definicao))
                        resultado.append(l)
                except:
                    resultado.append(l)

        if not resultado:
            # retirando pontuacao
            tmp = [p[0] for p in resultado_tmp]
            resultado = [p for p in tmp if len(p) > 1]

        return resultado

    # Retorna todos arquivos da pasta. SOMENTE arquivos
    @staticmethod
    def listar_arqs(dir_arqs, caminho_completo=True):
        if caminho_completo:
            return [f for f in os.listdir(dir_arqs) if os.path.isfile(os.path.join(dir_arqs, f))]
        else:
            return os.listdir(dir_arqs)

    @staticmethod
    def limpar_console():
        system('clear')

    @staticmethod
    def retornar_valida(frase):
        frase = Util.remove_acentos(frase)
        frase = re.sub('[?!,;]', '', frase)
        frase = frase.replace("\'", " ")
        frase = frase.replace("-", " ")
        frase = frase.replace("\'", "")
        frase = frase.replace("\\`", "")
        frase = frase.replace("\"", "")
        frase = frase.replace("\n", " ")

        return frase.strip().lower()

    @staticmethod
    def arquivo_existe(pasta, nome_arquivo):
        if pasta[-1] != "/":
            pasta = pasta + "/"

        return os.path.isfile(pasta + nome_arquivo) 

    @staticmethod
    def processar_contexto(lista_ctx, stop=True, lematizar=True, stem=True):
        if stop:
            lista_ctx = [i for i in lista_ctx if i not in stopwords.words('english')]
        if lematizar:
            lista_ctx = [lemmatize(i) for i in lista_ctx]
        if stem:
            lista_ctx = [porter.stem(i) for i in lista_ctx]

        return lista_ctx

    @staticmethod
    def retornar_valida(frase, lower=True, strip=True):
        frase = Util.remove_acentos(frase)
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
        frase = Util.remove_acentos(frase)
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
        frequencias = Util.obter_frequencias_frase(frase)
        soma = sum([e[1] for e in frequencias])

        return (soma / len(frequencias), frequencias)

    @staticmethod
    def is_stop_word(p):
        return p in stopwords.words('english')

    @staticmethod
    def ordenar_palavras(todas_palavras):
        dir_contadores = Util.configs['leipzig']['dir_contadores']

        if Util.contadores == None:
            contadores = Util.abrir_json(dir_contadores)
            Util.contadores = contadores
        else:
            contadores = Util.contadores

        palavras_indexadas = dict()
        palavras_ordenadas = [ ]
        
        for palavra in todas_palavras:
            try:
                if not contadores[palavra] in palavras_indexadas:
                    palavras_indexadas[contadores[palavra]] = [ ]
            except:
                palavras_indexadas[0] = [ ]

            try:
                palavras_indexadas[contadores[palavra]].append(palavra)
            except:
                palavras_indexadas[0].append(palavra)

        chaves = palavras_indexadas.keys()
        chaves.sort(reverse=True)

        for chave in chaves:
            palavras_ordenadas += list(set(palavras_indexadas[chave]))

        return palavras_ordenadas
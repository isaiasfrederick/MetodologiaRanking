
from nltk.corpus import stopwords, wordnet
from pyperclip import copy as copy
from lxml import html, etree
from itertools import chain
from sys import argv
import requests
import json
import re

from ModuloUtilitarios.Utilitarios import Utilitarios
import os
import traceback
import json

class ClienteOxfordAPI(object):
    def __init__(self, configs):
        configs_oxford = configs['oxford']

        self.configs = configs
        self.url_base = configs_oxford['url_base']
        self.app_id = configs_oxford['app_id']
        self.chave = configs_oxford['app_key']
        self.headers = {
            'app_id' : self.app_id,
            'app_key': self.chave
        }

        self.dir_urls_invalidas_sinonimos = configs['oxford']['cache']['obj_urls_invalidas_sinonimos']
        self.obj_urls_invalidas_sinonimos = Utilitarios.carregar_json(self.dir_urls_invalidas_sinonimos)

        self.dir_urls_invalidas_definicoes = configs['oxford']['cache']['obj_urls_invalidas_definicoes']
        self.obj_urls_invalidas_definicoes = Utilitarios.carregar_json(self.dir_urls_invalidas_definicoes)

        if not self.obj_urls_invalidas_sinonimos:
            self.obj_urls_invalidas_sinonimos = dict()
        if not self.obj_urls_invalidas_definicoes:
            self.obj_urls_invalidas_definicoes = dict()

    # retorna todas informacoes da API de Oxford
    def iniciar_coleta(self, palavra):
        definicoes = self.obter_definicoes(palavra) # Objeto 1
        sinonimos = self.obter_sinonimos(palavra) # Objeto 2

        # a API nao prove sinonimos e definicoes de forma unificada, entao...
        objeto_unificado = self.mesclar_significados_sinonimos(definicoes, sinonimos)
        return objeto_unificado

    def obter_lista_categoria(self, categoria):
        url = self.url_base + '/wordlist/en/registers=Rare;domains=' + categoria
        return Utilitarios.requisicao_http(url, self.headers)

    def obter_frequencia(self, palavra):
        url = self.url_base + '/stats/frequency/word/en/?corpus=nmc&lemma=' + palavra
        return Utilitarios.requisicao_http(url, self.headers)

    def obter_definicoes(self, palavra, lematizar=True):
        if palavra in self.obj_urls_invalidas_definicoes:
            print('ClienteOxford: URL evitada: ' + palavra + '\t\tHeaders: ' + str(self.headers))
            return None

        dir_cache_oxford = self.configs['oxford']['cache']['definicoes']            
        dir_obj_json = dir_cache_oxford + '/' + palavra + '.json'

        if os.path.isfile(dir_obj_json):
            return Utilitarios.carregar_json(dir_obj_json)

        try:
            url = self.url_base + "/entries/en/" + palavra
            obj = Utilitarios.requisicao_http(url, self.headers).json()

            saida_tmp = []
            saida = {}

            for e in obj['results'][0]['lexicalEntries']:
                saida_tmp.append(e)
            for entry in saida_tmp:
                if not entry['lexicalCategory'] in saida: saida[entry['lexicalCategory']] = []
                for sense in entry['entries'][0]['senses']:
                    saida[entry['lexicalCategory']].append(sense)

            print('ClienteOxford URL certa: ' + url + '\t\tHeaders: ' + str(self.headers))
            print('ClienteOxford: Salvando em cache: ' + str(Utilitarios.salvar_json(dir_obj_json, saida)))

            return saida
        except:
            traceback.print_exc()
            raw_input('Pression <enter>')
            self.obj_urls_invalidas_definicoes[palavra] = ""
            raw_input('ClienteOxford: URL errada: ' + url + '\t\tHeaders: ' + str(self.headers))
            return None

    def obter_sinonimos(self, palavra):
        if palavra in self.obj_urls_invalidas_sinonimos:
            print('ClienteOxford: URL evitada: ' + palavra + '\t\tHeaders: ' + str(self.headers))
            return None

        dir_cache_oxford = self.configs['oxford']['cache']['sinonimos']            
        dir_obj_json = dir_cache_oxford + '/' + palavra + '.json'

        if os.path.isfile(dir_obj_json):
            return Utilitarios.carregar_json(dir_obj_json)

        try:
            url = self.url_base + "/entries/en/" + palavra + "/synonyms"
            obj = Utilitarios.requisicao_http(url, self.headers).json()
            obj_json = {}

            for entry in obj['results'][0]['lexicalEntries']:
                pos = entry['lexicalCategory']
                if not pos in obj_json:
                    obj_json[pos] = []
                for sense in entry['entries'][0]['senses']:
                    obj_json[pos].append(sense)

            print('URL CERTA: ' + url + '\t\tHeaders: ' + str(self.headers))
            print('Salvando em cache: ' + str(Utilitarios.salvar_json(dir_obj_json, obj_json)))

            return obj_json
        except:
            self.obj_urls_invalidas_sinonimos[palavra] = ""
            print('URL ERRADA: ' + url + '\t\tHeaders: ' + str(self.headers))
            return None

    def persistir_urls_invalidas(self):
        Utilitarios.salvar_json(self.dir_urls_invalidas_sinonimos, self.obj_urls_invalidas_sinonimos)
        Utilitarios.salvar_json(self.dir_urls_invalidas_definicoes, self.obj_urls_invalidas_definicoes)

    def buscar_sinonimos_por_id(self, id, elemento):
        for e in elemento:
            if e['id'] == id:
                return [s['text'] for s in e['synonyms']]
        
        return []

    def buscar_exemplos_por_id(self, id, elemento):
        for e in elemento:
            if e['id'] == id:
                return [s['text'] for s in e['examples']]
        
        return []

    def mesclar_significados_sinonimos(self, definicoes_tmp, sinonimos):
        definicoes = dict(definicoes_tmp)
        todas_pos = definicoes.keys()

        for pos in todas_pos:
            for reg in definicoes[pos]:
                try:
                    sense_id = reg['thesaurusLinks'][0]['sense_id']
                    reg['synonyms'] = self.buscar_sinonimos_por_id(sense_id, sinonimos[pos])
                    reg['examples'] = self.buscar_exemplos_por_id(sense_id, sinonimos[pos])

                    for sig in reg['subsenses']:
                        sense_id = sig['thesaurusLinks'][0]['sense_id']
                        sig['synonyms'] = self.buscar_sinonimos_por_id(sense_id, sinonimos[pos])
                        sig['examples'] = self.buscar_exemplos_por_id(sense_id, sinonimos[pos])
                except:
                    pass

        return definicoes

    def obter_antonimos(self, palavra):
        url = self.url_base + "/entries/en/" + palavra + "/antonyms"
        return Utilitarios.requisicao_http(url, self.headers)

    def __del__(self):
        try:
            self.persistir_urls_invalidas()
        except:
            traceback.print_exc()


class ColetorOxfordWeb(object):
    def __init__(self, configs):
        self.configs = configs

    def iniciar_coleta(self, lemma):
        dir_cache = self.configs['oxford']['cache']['extrator_web']
        dir_cache_obj = dir_cache + '/' + lemma + '.json'
        obj = Utilitarios.carregar_json(dir_cache_obj)

        if obj: return obj

        resultado = {}
        conjunto_frames = self.buscar_frame_principal(lemma)

        for frame in conjunto_frames:
            res_tmp = self.scrap_frame_definicoes(frame)
            # lista com UM elemento apenas
            pos = res_tmp.keys()[0]
            resultado[pos] = res_tmp[pos]

        obj = json.loads(json.dumps(resultado))
        Utilitarios.salvar_json(dir_cache_obj, obj)

        return obj

    # remove as aspas das frases de exemplo selecionadas pelo coletor
    # Entrada: `frase de exemplo`       Saida: frase de exemplo
    def remove_aspas(self, frase):
        return frase[1:-1]

    def buscar_frames_principais_sinonimos(self, lemma):
        url_base = self.configs['oxford']['url_base_thesaurus']

        page = requests.get(url_base + '/' + lemma)
        tree = html.fromstring(page.content)

        path = "//*[@id='content']/div/div/div/div/div/div/section[h3/span[@class='pos']]"

        try:
            requests.session().cookies.clear()
        except: pass

        return tree.xpath(path)

    def obter_termos_sinonimos(self, lemma, f):
        elementos = self.buscar_frames_principais_sinonimos(lemma)

        resultados = {}

        for e in elementos:
            path = "h3/span[@class='pos']"
            func = e.find(path).text[0].lower()
            path = "div[@class='row']/div[@class='se2']"
            significado = e.findall(path)

            for s in significado:
                path = "div/div/div[@class='synList']/div[@class='synGroup']/p"

                for p in s.findall(path):
                    sinonimos = p.text_content()

                    if not func in resultados: resultados[func] = []
                    resultados[func] += sinonimos.split(', ')

        resultado_persistivel = []

        for r in resultados[f]:
            r_tmp = {'lemma': lemma, 'funcao': f, 'sinonimo': r}
            resultado_persistivel.append(r_tmp)

        return list(set(resultados[f]))

    def buscar_frame_principal(self, termo):
        page = requests.get('https://en.oxforddictionaries.com/definition/' + termo)
        tree = html.fromstring(page.content)

        try:
            requests.session().cookies.clear()
        except: pass

        path = "//*[@id='content']/div[1]/div[2]/div/div/div/div[1]/section[@class='gramb']"

        principal = tree.xpath(path)
        return principal

    def scrap_frame_definicoes(self, frame):
        resultado = {}
        pos = frame.find("h3[@class='ps pos']/span[@class='pos']").text.capitalize()
        raw_input(pos)
        frame_definicoes = frame.findall('ul/li')

        resultado = dict()

        for frame_definicao in frame_definicoes:
            try:
                def_princ_txt = frame_definicao.find("div/p/span[@class='ind']").text
            except:
                def_princ_txt = None

            if def_princ_txt:
                resultado[def_princ_txt] = dict()

                path = "div/div[@class='exg']/div/em"
                exemplos_principais = [self.remove_aspas(e.text) for e in frame_definicao.findall(path)]

                path = "div/div[@class='examples']/div[@class='exg']/ul/li/em"
                mais_exemplos = [self.remove_aspas(e.text) for e in frame_definicao.findall(path)]

                exemplos_principais += mais_exemplos

                path = "div/ol[@class='subSenses']/li[@class='subSense']"
                definicoes_secundarias = frame_definicao.findall(path)

                resultado[def_princ_txt]['def_secs'] = {}
                resultado[def_princ_txt]['exemplos'] = exemplos_principais

                for definicao_secundaria in definicoes_secundarias:
                    try:
                        def_sec_txt = definicao_secundaria.find("span[@class='ind']").text
                    except:
                        pass

                    if def_sec_txt:
                        path = "div[@class='trg']/div[@class='exg']/div[@class='ex']/em"
                        exes_princ_def_sec_txt = [self.remove_aspas(e.text) for e in definicao_secundaria.findall(path)]

                        path = "div[@class='trg']/div[@class='examples']/div[@class='exg']/ul/li[@class='ex']/em"
                        exes_sec_def_sec_txt = [self.remove_aspas(e.text) for e in definicao_secundaria.findall(path)]

                        exes_princ_def_sec_txt += exes_sec_def_sec_txt

                        resultado[def_princ_txt]['def_secs'][def_sec_txt] = {'exemplos': []}
                        resultado[def_princ_txt]['def_secs'][def_sec_txt]['exemplos'] = exes_princ_def_sec_txt

        djson = json.dumps({pos: resultado})

        return json.loads(djson)

    def stem_tokens(self, tokens):
        from nltk.stem.snowball import SnowballStemmer
        stemmer = SnowballStemmer("english")
        return [stemmer.stem(t) for t in tokens]

    def retornar_tokens_radicalizados(self, frase):
        return None

    def classificar_exemplos(self, lemma, synset, funcao_sintatica):
        print('A definicao \'%s\' nao possui exemplos...' % synset.definition())
        dtmp = synset.definition().split(' ')
        print('Definicao tokenizada: ' + str(self.stem_tokens(dtmp)))
        is_stop_word = Utils.Utils.is_stop_word
        frase_valida = Utils.Utils.retornar_valida

        dados_coletados = self.iniciar_coleta(lemma)[funcao_sintatica]
        definicoes_principais = list(dados_coletados)

        palavras_indexadas = dict()
        definicoes_indexadas = set()

        for definicao in definicoes_principais:
            def_tokenizada = [p for p in frase_valida(definicao).split(' ') if not is_stop_word(p)]
            def_tokenizada = self.stem_tokens(def_tokenizada)

            for palavra in set(def_tokenizada):
                if not palavra in palavras_indexadas:
                    palavras_indexadas[palavra] = list()
                palavras_indexadas[palavra].append(definicao)
                definicoes_indexadas.add(definicao)

            for def_sec in dados_coletados[definicao]['def_secs'].keys():
                def_tokenizada = [p for p in frase_valida(def_sec).split(' ') if not is_stop_word(p)]
                def_tokenizada = self.stem_tokens(def_tokenizada)

                for palavra in set(def_tokenizada):
                    if not palavra in palavras_indexadas:
                        palavras_indexadas[palavra] = list()
                    palavras_indexadas[palavra].append(def_sec)
                    definicoes_indexadas.add(definicao)

        if True:
            for chave in palavras_indexadas.keys():
                print('\n\n ' + chave + ':')
                for d in palavras_indexadas[chave]:
                    text1 = " ".join(list(d))
                    text2 = " ".join(list(synset.definition()))

                    v1 = Utils.Utils.texto_para_vetor(text1)
                    v2 = Utils.Utils.texto_para_vetor(text2)

                    distancia = Utils.Utils.get_cosine(v1, v2)
                    print('\t\t' + str(distancia) + ' - '+ d)


        return list()

# esta classe faz o merge de objetos do coletor
class BaseUnificadaObjetosOxford(object):
    def __init__(self, configs):
        self.configs = configs
        self.cliente_api_oxford = ClienteOxfordAPI(self.configs)
        self.coletor_web_oxford = ColetorOxfordWeb(self.configs)

    # mescla objetos obtidos via coletor-web e cliente API
    def iniciar_consulta(self, palavra):
        obj_cli = self.cliente_api_oxford.iniciar_coleta(palavra)
        obj_col = self.coletor_web_oxford.iniciar_coleta(palavra)

        if not obj_cli or not obj_col:
            return None

        obj_col = dict(obj_col)

        try:
            for pos in obj_col:
                for def_primaria in obj_col[pos]:
                    sinonimos = self.obter_sinonimos_por_definicao(pos, def_primaria, obj_cli)
                    obj_col[pos][def_primaria]['sinonimos'] = sinonimos

                    for def_sec in obj_col[pos][def_primaria]['def_secs']:
                        sinonimos = self.obter_sinonimos_por_definicao(pos, def_sec, obj_cli)
                        obj_col[pos][def_primaria]['def_secs'][def_sec]['sinonimos'] = sinonimos
        except:
            return None

        return obj_col


    def obter_sinonimos_por_definicao(self,pos, definicao, obj_cli):
        # retirando o ponto final e colocando em caixa baixa
        definicao = definicao[:-1].lower()

        try:
            for regs in obj_cli[pos]:
                if definicao in regs['definitions']:
                    try: return regs['synonyms']
                    except: return []

                for subsense in regs['subsenses']:
                    if definicao in subsense['definitions']:
                        try: return subsense['synonyms']
                        except: return []
        except: pass
            
        return []


    def testar_extrator_oxford(self, palavra):        
        coletor_web_oxford = ColetorOxfordWeb(self.configs)
        cliente_api_oxford = ClienteOxfordAPI(self.configs)

        obj_cli = cliente_api_oxford.iniciar_coleta(palavra)
        obj_col = coletor_web_oxford.iniciar_coleta(palavra)

        unificador_oxford = BaseUnificadaObjetosOxford(self.configs)
        obj_integrado_oxford = unificador_oxford.iniciar_consulta(obj_cli, obj_col)

        print('\n\n')
        raw_input(obj_integrado_oxford)
        raw_input('\n<enter>')
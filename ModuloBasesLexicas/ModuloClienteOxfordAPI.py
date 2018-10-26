from nltk.corpus import stopwords, wordnet
from pyperclip import copy as copy
from lxml import html, etree
import traceback
from itertools import chain
from sys import argv
import requests
import json
import sys
import re

from textblob import Word

from Utilitarios import Util
import os
import traceback
import json
import time

# Esta classe faz o merge de objetos do coletor
class BaseUnificadaOx(object):
    # Salva os pares <<palavra, definicao> : sinonimos>
    # Para os dados de Oxford
    sinonimos_extraidos_definicao = dict()

    # Todos objetos unificados providos pelo menotod OterObjUnificado
    #Indexados pelo formato <palavra, obj>
    objs_unificados = dict()

    def __init__(self, configs):
        self.configs = configs
        self.cliente_api_oxford = ClienteOxfordAPI(self.configs)
        self.coletor_web_oxford = ColetorOxfordWeb(self.configs)

    def obter_obj_cli_api(self, palavra):
        return self.cliente_api_oxford.iniciar_coleta(palavra)

    def obter_obj_col_web(self, palavra):
        return self.coletor_web_oxford.iniciar_coleta(palavra)

    def obter_atributo(self, palavra, pos, definicao, atributo):
        obj_unificado = self.obter_obj_unificado(palavra)

        if pos != None:
            if len(pos) == 1:
                todas_pos = [Util.conversor_pos_wn_oxford(pos)]
        else:
            todas_pos = obj_unificado.keys()

        try:
            for pos in todas_pos:
                for def_primaria in obj_unificado[pos]:
                    if definicao == def_primaria:
                        return obj_unificado[pos][def_primaria][atributo]

                    for def_sec in obj_unificado[pos][def_primaria]['def_secs']:
                        if definicao == def_sec:
                            return obj_unificado[pos][def_primaria]['def_secs'][def_sec][atributo]

        except:
            print("A palavra %s e definicao '%s' retornou 0 sinonimos!" % (palavra, definicao))

        return None

    # Mescla objetos obtidos via coletor-web e objeto unificado ClienteAPI
    def obter_obj_unificado(self, palavra):
        BaseUnificadaOx.objs_unificados = {}

        palavra = Util.normalizar_palavra(palavra)

        if palavra in BaseUnificadaOx.objs_unificados:
            print('@@@ Achei os dados no cache!\nPalavra: ' + palavra)

            if not BaseUnificadaOx.objs_unificados[palavra]:
                print('NULO!\n')

            return BaseUnificadaOx.objs_unificados[palavra]

        obj_cli_unificado = self.cliente_api_oxford.iniciar_coleta(palavra)
        obj_coletado = self.coletor_web_oxford.iniciar_coleta(palavra)

        if not obj_cli_unificado or not obj_coletado:
            BaseUnificadaOx.objs_unificados[palavra] = None
            return None

        obj_coletado = dict(obj_coletado)

        try:
            for pos in obj_coletado:
                for def_primaria in obj_coletado[pos]:
                    sinonimos = self.obter_sinonimos_fonte_obj_api(pos, def_primaria, obj_cli_unificado)

                    try:
                        sinonimos = BaseUnificadaOx.sinonimos_extraidos_definicao[palavra][def_primaria]
                    except: pass

                    if sinonimos.__len__() == 0:
                        sinonimos = self.extrair_sinonimos_candidatos_definicao(def_primaria, pos)

                        if not palavra in BaseUnificadaOx.sinonimos_extraidos_definicao:
                            BaseUnificadaOx.sinonimos_extraidos_definicao[palavra] = {}                
                        BaseUnificadaOx.sinonimos_extraidos_definicao[palavra][def_primaria] = sinonimos

                    obj_coletado[pos][def_primaria]['sinonimos'] = sinonimos

                    for def_sec in obj_coletado[pos][def_primaria]['def_secs']:
                        sinonimos = self.obter_sinonimos_fonte_obj_api(pos, def_sec, obj_cli_unificado)
                        if sinonimos.__len__() == 0:
                            sinonimos = self.obter_sinonimos_fonte_obj_api(pos, def_primaria, obj_cli_unificado)

                            try:
                                sinonimos = BaseUnificadaOx.sinonimos_extraidos_definicao[palavra][def_primaria]
                            except: pass

                            if sinonimos.__len__() == 0:
                                sinonimos = self.extrair_sinonimos_candidatos_definicao(def_sec, pos)

                                if not palavra in BaseUnificadaOx.sinonimos_extraidos_definicao:
                                    BaseUnificadaOx.sinonimos_extraidos_definicao[palavra] = {}                
                                BaseUnificadaOx.sinonimos_extraidos_definicao[palavra][def_primaria] = sinonimos


                        obj_coletado[pos][def_primaria]['def_secs'][def_sec]['sinonimos'] = sinonimos
        except:
            traceback.print_exc()
            BaseUnificadaOx.objs_unificados[palavra] = None
            return None

        obj_unificado = dict(obj_coletado)
        BaseUnificadaOx.objs_unificados[palavra] = obj_unificado

        return obj_unificado

    # Obtem sinonimos a partir da palavra, definicao, pos
    def obter_sinonimos(self, palavra, definicao, pos=None):
        obj_unificado = self.obter_obj_unificado(palavra)

        if pos == None:
            lista_pos = [pos for pos in obj_unificado.keys()]
        elif len(pos) == 1:
            lista_pos = [Util.conversor_pos_wn_oxford(pos)]

        try:
            for pos in lista_pos:
                for def_primaria in obj_unificado[pos]:
                    if definicao in def_primaria or def_primaria in definicao:
                        return obj_unificado[pos][def_primaria]['sinonimos']

                    for def_sec in obj_unificado[pos][def_primaria]['def_secs']:
                        if definicao in def_sec or def_sec in definicao:
                            return obj_unificado[pos][def_primaria]['def_secs'][def_sec]['sinonimos']
        except:
            print("A palavra %s e definicao '%s' retornou 0 sinonimos!" % (palavra, definicao))

        return None

    # Obtem exemplos a partir do objeto unificado
    def obter_exemplos__(self, pos, definicao, obj_unificado):
        if len(pos) == 1:
            pos = Util.conversor_pos_wn_oxford(pos)

        try:
            for def_primaria in obj_unificado[pos]:
                if definicao == def_primaria:
                    return obj_unificado[pos][def_primaria]['exemplos']

                for def_sec in obj_unificado[pos][def_primaria]['def_secs']:
                    if definicao == def_sec:
                        return obj_unificado[pos][def_primaria]['def_secs'][def_sec]['exemplos']

        except:
            print("A palavra %s e definicao '%s' retornou 0 sinonimos!" % (palavra, definicao))

        return None

    # Obter todas as definicoes
    def obter_todas_definicoes(self, palavra, pos=None):
        obj_unificado = self.obter_obj_unificado(palavra)

        try:
            # Se POS = None, pegue todas as POS
            if pos != None:
                pos = Util.conversor_pos_wn_oxford(pos)

                if pos in obj_unificado:
                    obj_unificado = { pos: obj_unificado[pos] }
                else:
                    obj_unificado = dict()
            else:
                pass

            todas_definicoes = [ ]
        except (TypeError, AttributeError), e:
            try:
                return self.obter_todas_definicoes(Word(palavra).singularize(), pos)
            except:
                return [ ]

        try:
            for pos in obj_unificado:
                for def_primaria in obj_unificado[pos]:
                    todas_definicoes.append(def_primaria)

                    for def_sec in obj_unificado[pos][def_primaria]['def_secs']:
                        todas_definicoes.append(def_sec)
        except: pass

        return todas_definicoes

    def existe_intersecao(self, s1, s2):
        return bool(set(s1) & set(s2))

    # Definicao deve vir com ponto e caixa baixa
    def obter_sinonimos_fonte_obj_api(self, pos, definicao_oxford, obj_cli_api):
        # retirando o ponto final e colocando em caixa baixa
        pos = Util.conversor_pos_wn_oxford(pos)

        todas_versoes_definicoes = [ ]

        todas_versoes_definicoes.append(definicao_oxford)
        todas_versoes_definicoes.append(definicao_oxford[:-1])
        todas_versoes_definicoes.append(definicao_oxford.lower())
        todas_versoes_definicoes.append(definicao_oxford[:-1].lower())

        try:
            for regs in obj_cli_api[pos]:
                if self.existe_intersecao(todas_versoes_definicoes, regs['definitions']):
                    try: return regs['synonyms']
                    except: pass

                if 'subsenses' in regs:
                    for sub_regs in regs['subsenses']:
                        if self.existe_intersecao(todas_versoes_definicoes, sub_regs['definitions']):
                            try: return sub_regs['synonyms']
                            except: return regs['synonyms']

        except: pass

        return [ ]

    # Extrai todos (substantivos, verbos) de uma dada definicao e coloca como sinonimos candidatos
    def extrair_sinonimos_candidatos_definicao(self, definicao, pos):
        return Util.extrair_sinonimos_candidatos_definicao(definicao, pos)
#
#
# extrai da API da ferramenta todos Objetos utilizados pela abordagem
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
        self.obj_urls_invalidas_sinonimos = Util.abrir_json(self.dir_urls_invalidas_sinonimos)

        self.dir_urls_invalidas_definicoes = configs['oxford']['cache']['obj_urls_invalidas_definicoes']
        self.obj_urls_invalidas_definicoes = Util.abrir_json(self.dir_urls_invalidas_definicoes)

        if not self.obj_urls_invalidas_sinonimos:
            self.obj_urls_invalidas_sinonimos = dict()
        if not self.obj_urls_invalidas_definicoes:
            self.obj_urls_invalidas_definicoes = dict()

    # retorna todas informacoes da API de Oxford
    def iniciar_coleta(self, palavra):
        definicoes_tmp = self.obter_definicoes(palavra) # Objeto 1
        sinonimos_tmp = exemplos_tmp = self.obter_sinonimos(palavra) # Objeto 2

        if sinonimos_tmp:
            sinonimos_tmp = self.converter_obj_sinonimos(sinonimos_tmp)        
        if exemplos_tmp:
            exemplos_tmp = self.converter_obj_exemplos(exemplos_tmp)

        if not definicoes_tmp:
            print('Objeto de DEFINICOES para %s obtido na coleta do ClienteOxford nao funcionou!' % palavra)
            print('As definicoes para %s nao foram encontradas!' % palavra)
            print('\n\n')

        if not sinonimos_tmp:
            print('Objeto de SINONIMOS para %s obtido na coleta do ClienteOxford nao funcionou!' % palavra)
            print('\n\n')


        if definicoes_tmp:
            # a API nao prove sinonimos e definicoes de forma unificada, entao junte as duas
            objeto_unificado = self.mesclar_definicoes_com_sinonimos(definicoes_tmp, sinonimos_tmp, exemplos_tmp)
        else:
            objeto_unificado = {}

        definicoes_tmp = None
        sinonimos_tmp = None
        exemplos_tmp = None

        return objeto_unificado

    # Converte um .json de sinonimos para pares <id : lista sinonimos>
    def converter_obj_sinonimos(self, obj_sinonimos):
        resultado = dict()

        for pos in obj_sinonimos:
            for reg in obj_sinonimos[pos]:
                if 'id' in reg and 'synonyms' in reg:
                    try:
                        resultado[reg['id']] = [e['text'] for e in reg['synonyms']]
                    except: pass

                if 'subsenses' in reg:
                    for reg2 in reg['subsenses']:
                        if 'id' in reg2 and 'synonyms' in reg2:
                            
                            try:
                                resultado[reg2['id']] = [e['text'] for e in reg2['synonyms']]
                            except: pass

        return resultado

    # Converte um .json de sinonimos para pares <id : lista sinonimos>
    def converter_obj_exemplos(self, obj_exemplos):
        resultado = dict()

        for pos in obj_exemplos:
            for reg in obj_exemplos[pos]:
                if 'id' in reg and 'examples' in reg:
                    try:
                        resultado[reg['id']] = [e['text'] for e in reg['examples']]
                    except: pass

                if 'subsenses' in reg:
                    for reg2 in reg['subsenses']:
                        if 'id' in reg2 and 'examples' in reg2:
                            
                            try:
                                resultado[reg2['id']] = [e['text'] for e in reg2['examples']]
                            except: pass

        return resultado

    def obter_lista_categoria(self, categoria):
        url = self.url_base + '/wordlist/en/registers=Rare;domains=' + categoria
        inicio = time.time()
        resultado = Util.requisicao_http(url, self.headers)
        fim = time.time()
        print('Tempo gasto para a URL %s: %s' + (url, str(fim-inicio)))
        return resultado

    def obter_frequencia(self, palavra):
        dir_cache = self.configs['oxford']['cache']['frequencias']

        todos_arquivos_cache = Util.listar_arqs(self.configs['oxford']['cache']['frequencias'])
        todos_arquivos_cache = [c.split("/")[-1] for c in todos_arquivos_cache]

        if palavra + ".json" in todos_arquivos_cache:
            path = dir_cache + '/' + palavra + '.json'
            obj = Util.abrir_json(path)

            return obj['result']['frequency']
        else:
            url = self.url_base + '/stats/frequency/word/en/?corpus=nmc&lemma=' + palavra
            obj_req = Util.requisicao_http(url, self.headers)

            path = dir_cache + '/' + palavra + '.json'
            Util.salvar_json(path, obj_req.json())

            try:
                return obj_req.json()['result']['frequency']
            except Exception, e:
                return 0

    def obter_definicoes(self, palavra, lematizar=True):
        if palavra in self.obj_urls_invalidas_definicoes:
            #print('ClienteOxford: URL evitada: ' + palavra + '\t\tHeaders: ' + str(self.headers))
            print('ClienteOxford: URL evitada: ' + palavra)
            return None

        dir_cache_oxford = self.configs['oxford']['cache']['definicoes']            
        dir_obj_json = dir_cache_oxford + '/' + palavra + '.json'

        if os.path.isfile(dir_obj_json):
            return Util.abrir_json(dir_obj_json)

        try:
            url = self.url_base + "/entries/en/" + palavra

            print('\nRequerindo URL %s' % url)
            inicio = time.time()
            obj = Util.requisicao_http(url, self.headers).json()
            fim = time.time()

            print('Tempo gasto: ' + str(fim-inicio))

            saida_tmp = [ ]
            saida = {}

            for e in obj['results'][0]['lexicalEntries']:
                saida_tmp.append(e)
            for entry in saida_tmp:
                if not entry['lexicalCategory'] in saida: saida[entry['lexicalCategory']] = [ ]
                for sense in entry['entries'][0]['senses']:
                    saida[entry['lexicalCategory']].append(sense)

            print('ClienteOxford URL certa: ' + url + '\t\tHeaders: ' + str(self.headers))
            print('ClienteOxford: Salvando em cache: ' + str(Util.salvar_json(dir_obj_json, saida)))

            return saida
        except:
            traceback.print_exc()
            self.obj_urls_invalidas_definicoes[palavra] = ""
            #print('ClienteOxford: URL errada: ' + url + '\t\tHeaders: ' + str(self.headers))
            print('ClienteOxford: URL errada: ' + palavra)
            return None

    def obter_sinonimos(self, palavra):
        if palavra in self.obj_urls_invalidas_sinonimos:
            #print('ClienteOxford: URL evitada: ' + palavra + '\t\tHeaders: ' + str(self.headers))
            print('ClienteOxford: URL evitada: ' + palavra)
            return None

        dir_cache_oxford = self.configs['oxford']['cache']['sinonimos']            
        dir_obj_json = dir_cache_oxford + '/' + palavra + '.json'

        if os.path.isfile(dir_obj_json):
            return Util.abrir_json(dir_obj_json)

        try:
            url = self.url_base + "/entries/en/" + palavra + "/synonyms"
            obj = Util.requisicao_http(url, self.headers).json()
            obj_json = {}

            for entry in obj['results'][0]['lexicalEntries']:
                pos = entry['lexicalCategory']
                if not pos in obj_json:
                    obj_json[pos] = [ ]
                for sense in entry['entries'][0]['senses']:
                    obj_json[pos].append(sense)

            print('URL CERTA: ' + url + '\t\tHeaders: ' + str(self.headers))
            print('Salvando em cache: ' + str(Util.salvar_json(dir_obj_json, obj_json)))

            return obj_json
        except:
            self.obj_urls_invalidas_sinonimos[palavra] = ""
            print('URL ERRADA: ' + url + '\t\tHeaders: ' + str(self.headers))
            return None

    def persistir_urls_invalidas(self):
        Util.salvar_json(self.dir_urls_invalidas_sinonimos, self.obj_urls_invalidas_sinonimos)
        Util.salvar_json(self.dir_urls_invalidas_definicoes, self.obj_urls_invalidas_definicoes)

    def buscar_sinonimos_por_id(self, id, elemento):
        for e in elemento:
            if e['id'] == id:
                return [s['text'] for s in e['synonyms']]
        
        return [ ]

    def buscar_exemplos_por_id(self, significado_id, sinonimos_tmp):
        for e in elemento:
            if e['id'] == significado_id:
                return [s['text'] for s in e['examples']]
        
        return [ ]

    def mesclar_definicoes_com_sinonimos(self, definicoes_tmp, sinonimos_tmp, exemplos_tmp):
        if not definicoes_tmp: return None

        definicoes = dict(definicoes_tmp)
        todas_pos = definicoes.keys()

        for pos in todas_pos:
            for reg in definicoes[pos]:
                try:
                    sense_id = reg['thesaurusLinks'][0]['sense_id']

                    try:
                        reg['synonyms'] = sinonimos_tmp[sense_id]
                    except Exception, e:
                        reg['synonyms'] = [ ]

                    try:
                        reg['examples'] = exemplos_tmp[sense_id]
                    except:
                        reg['examples'] = [ ]

                    for sig in reg['subsenses']:
                        sense_id = sig['thesaurusLinks'][0]['sense_id']

                        try:
                            sig['synonyms'] = sinonimos_tmp[sense_id]
                        except Exception, e:
                            sig['synonyms'] = [ ]

                        try:
                            sig['examples'] = exemplos_tmp[sense_id]
                        except:
                            sig['examples'] = [ ]
                except:
                    pass

        return definicoes

    def obter_antonimos(self, palavra):
        url = self.url_base + "/entries/en/" + palavra + "/antonyms"
        return Util.requisicao_http(url, self.headers)

    def __del__(self):
        try:
            self.persistir_urls_invalidas()
        except:
            traceback.print_exc()
#
#
# extrai da interface Web todos Objetos utilizados pela abordagem
class ColetorOxfordWeb(object):
    # Nome auto-explicativo
    cache_objetos_coletados = {}

    def __init__(self, configs):
        self.configs = configs

    def iniciar_coleta(self, lema):
        if not lema:
            return None

        if lema in ColetorOxfordWeb.cache_objetos_coletados:
            return ColetorOxfordWeb.cache_objetos_coletados[lema]

        dir_cache = self.configs['oxford']['cache']['extrator_web']
        dir_cache_obj = dir_cache + '/' + lema + '.json'
        obj = Util.abrir_json(dir_cache_obj)

        if obj != None:
            ColetorOxfordWeb.cache_objetos_coletados[lema] = obj
            return obj

        resultado = {}

        try:
            conjunto_frames = self.buscar_frame_principal(lema)
        except:
            pass

        if not conjunto_frames:
            ColetorOxfordWeb.cache_objetos_coletados[lema] = None
            return None

        for frame in conjunto_frames:
            res_tmp = self.scrap_frame_definicoes(frame, lema)

            # lista com UM elemento apenas
            pos = res_tmp.keys()[0]

            if not pos in resultado:
                resultado[pos] = dict()

            for def_primaria in res_tmp[pos]:
                resultado[pos][def_primaria] = res_tmp[pos][def_primaria]

        obj = json.loads(json.dumps(resultado))
        Util.salvar_json(dir_cache_obj, obj)

        ColetorOxfordWeb.cache_objetos_coletados[lema] = obj
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

                    if not func in resultados: resultados[func] = [ ]
                    resultados[func] += sinonimos.split(', ')

        resultado_persistivel = [ ]

        for r in resultados[f]:
            r_tmp = {'lemma': lemma, 'funcao': f, 'sinonimo': r}
            resultado_persistivel.append(r_tmp)

        return list(set(resultados[f]))

    def buscar_frame_principal(self, termo):
        try:
            page = requests.get('https://en.oxforddictionaries.com/definition/' + termo)
        except:
            print('Excecao no metodo buscar_frame_principal() para o termo ' + termo + '\n')
            return None

        tree = html.fromstring(page.content)

        try:
            requests.session().cookies.clear()
        except: pass

        path = "//*[@id='content']/div[1]/div[2]/div/div/div/div[1]/section[@class='gramb']"

        principal = tree.xpath(path)
        return principal

    def scrap_frame_definicoes(self, frame, lema):
        resultado = {}

        pos = None

        try:
            pos = frame.find("h3[@class='ps pos']/span[@class='pos']").text.capitalize()
        except:
            print("\n\n")
            traceback.print_exc()
            print("\n\n")
            print(lema)
            raw_input("\n\n<enter>")

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
                        def_sec_txt = None

                    if def_sec_txt:
                        path = "div[@class='trg']/div[@class='exg']/div[@class='ex']/em"
                        exes_princ_def_sec_txt = [self.remove_aspas(e.text) for e in definicao_secundaria.findall(path)]

                        path = "div[@class='trg']/div[@class='examples']/div[@class='exg']/ul/li[@class='ex']/em"
                        exes_sec_def_sec_txt = [self.remove_aspas(e.text) for e in definicao_secundaria.findall(path)]

                        exes_princ_def_sec_txt += exes_sec_def_sec_txt

                        resultado[def_princ_txt]['def_secs'][def_sec_txt] = {'exemplos': [ ]}
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
        dtmp = synset.definition().split(' ')

        is_stop_word = Util.Utils.is_stop_word
        frase_valida = Util.Utils.retornar_valida

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

                    v1 = Util.Utils.texto_para_vetor(text1)
                    v2 = Util.Utils.texto_para_vetor(text2)

                    distancia = Util.Utils.get_cosine(v1, v2)
                    print('\t\t' + str(distancia) + ' - '+ d)


        return list()

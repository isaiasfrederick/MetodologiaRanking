from nltk.corpus import stopwords, wordnet
from pyperclip import copy as copy
from nltk.stem import WordNetLemmatizer
from lxml import html, etree
import traceback
from itertools import chain
from sys import argv
import requests
import json
import sys
import re

from Utilitarios import Util
from textblob import Word
import traceback
import json
import time
import os

# Esta classe faz o merge de objetos do coletor
class BaseOx(object):
    BASE_OX = None
    # Salva os pares <<palavra, definicao> : sinonimos>
    # Para os dados de Oxford
    sins_extraidos_definicao = dict()
    lematizador = WordNetLemmatizer()
    # Quando determinado objeto nao esta acessivel nem no disco e nem via URL
    objs_sinonimos_inatingiveis = set()
    # Todos objetos unificados providos pelo menotod OterObjUnificado
    #Indexados pelo formato <palavra, obj>
    objs_unificados = dict()

    def __init__(self, cfgs, cli_ox, ext_web):
        self.cfgs = cfgs
        self.cli_api_ox = cli_ox
        self.extrator_web_ox = ext_web

    def obter_obj_cli_api(self, palavra):
        return self.cli_api_ox.iniciar_coleta(palavra)

    def obter_obj_col_web(self, palavra):
        return self.extrator_web_ox.iniciar_coleta(palavra)

    def obter_atributo(self, palavra, pos, definicao, atributo):
        obj_unificado = self.construir_objeto_unificado(palavra)

        if pos != None:
            if len(pos) == 1:
                todas_pos = [Util.cvrsr_pos_wn_oxford(pos)]
            else: todas_pos = [pos]
        else: todas_pos = obj_unificado.keys()

        try:
            for pos in todas_pos:
                for def_primaria in obj_unificado[pos]:
                    obj_filtrado = obj_unificado[pos][def_primaria]
                    if definicao == def_primaria:
                        return obj_filtrado[atributo]
                    for def_sec in obj_filtrado['def_secs']:
                        if definicao == def_sec:
                            return obj_filtrado['def_secs'][def_sec][atributo]
        except Exception, e: pass
        return None


    def construir_objeto_unificado(self, palavra):
        palavra_sing = Util.singularize(palavra)

        if palavra in BaseOx.objs_unificados:
            return BaseOx.objs_unificados[palavra]

        dir_bases = self.cfgs['caminho_raiz_bases']
        dir_cache_oxford = self.cfgs['oxford']['cache']
        nome_arq = palavra + '.json'

        dir_obj_definicoes = dir_bases+'/'+dir_cache_oxford['definicoes']+'/'+nome_arq
        dir_obj_extrator = dir_bases+'/'+dir_cache_oxford['extrator_web']+'/'+nome_arq
        dir_obj_sinonimos = dir_bases+'/'+dir_cache_oxford['sinonimos']+'/'+nome_arq

        obj_definicoes = Util.abrir_json(dir_obj_definicoes, criar=False)
        obj_extrator   = Util.abrir_json(dir_obj_extrator, criar=False)

        if not dir_obj_sinonimos in BaseOx.objs_sinonimos_inatingiveis:
            obj_sinonimos  = Util.abrir_json(dir_obj_sinonimos, criar=False)

            if obj_sinonimos in [None, { }]:
                obj_sinonimos = self.cli_api_ox.obter_sinonimos(palavra)
                if obj_sinonimos in [None, { }] and palavra_sing != palavra:
                    obj_sinonimos = self.cli_api_ox.obter_sinonimos(palavra_sing)
            if obj_sinonimos:
                Util.salvar_json(dir_obj_sinonimos, obj_sinonimos)
                if palavra_sing != palavra:
                    dir_obj_sinonimos = dir_bases+'/'+dir_cache_oxford['sinonimos']+'/'+palavra_sing + '.json'
                    Util.salvar_json(dir_obj_sinonimos, obj_sinonimos)                
            else:
                BaseOx.objs_sinonimos_inatingiveis.add(palavra)
                BaseOx.objs_sinonimos_inatingiveis.add(palavra_sing)
                #print("\n %s resultou null!\n"%dir_obj_sinonimos)

        if obj_extrator == None:
            obj_extrator = self.extrator_web_ox.iniciar_coleta(palavra)

            if obj_extrator != None and obj_extrator != { }:
                Util.salvar_json(dir_obj_extrator, obj_extrator)

                dir_obj_extrator_sing = dir_bases+'/'+dir_cache_oxford['extrator_web']+'/'+palavra_sing+'.json'                

                if dir_obj_extrator_sing != dir_obj_extrator:
                    Util.salvar_json(dir_obj_extrator_sing, obj_extrator)

                return obj_extrator

            else:

                obj_extrator = self.extrator_web_ox.iniciar_coleta(palavra_sing)

                if obj_extrator != None and obj_extrator != { }:
                    Util.salvar_json(dir_obj_extrator, obj_extrator)

                    dir_obj_extrator_sing = dir_bases+'/'+dir_cache_oxford['extrator_web']+'/'+palavra_sing+'.json'                

                    if dir_obj_extrator_sing != dir_obj_extrator:
                        Util.salvar_json(dir_obj_extrator_sing, obj_extrator)

                    return obj_extrator

            #print("\n%s nao possui paginas extraidas...\n"%dir_obj_extrator)
            return { }

        # Processando definicoes
        obj_join_definicoes = { }

        # Processando definicoes extrator
        obj_join_extrator = { }
        for pos in obj_extrator:
            for def_prim in obj_extrator[pos]:
                k_reg = pos + self.cfgs['separador'] + def_prim[:-1].lower()
                obj_join_extrator[k_reg] = obj_extrator[pos][def_prim]['exemplos']

                for def_sec in obj_extrator[pos][def_prim]['def_secs']:
                    k_reg = pos + self.cfgs['separador'] + def_sec[:-1].lower()
                    obj_join_extrator[k_reg] = obj_extrator[pos][def_prim]['def_secs'][def_sec]['exemplos']

        if not obj_definicoes or not obj_sinonimos:
            return obj_extrator

        for pos in obj_definicoes:
            for reg in obj_definicoes[pos]:
                if 'thesaurusLinks' in reg:
                    k_reg = pos + self.cfgs['separador'] + reg['thesaurusLinks'][0]['sense_id']

                    if 'definitions' in reg:
                        if 'subsenses' in reg:
                            for reg_sub in reg['subsenses']:
                                try:
                                    k_reg = pos + self.cfgs['separador'] + reg_sub['thesaurusLinks'][0]['sense_id']
                                except:
                                    k_reg = pos + self.cfgs['separador'] + reg_sub['id']
                                try:
                                    obj_join_definicoes[k_reg] = reg_sub['definitions']
                                except: pass
                    else: pass
                else: pass

        obj_unificado = dict(obj_extrator)
        # Processando sinonimos
        obj_join_sinonimos = { }

        for pos in obj_sinonimos:
            for reg in obj_sinonimos[pos]:
                k_reg = pos + self.cfgs['separador'] + reg['id']
                try: sins_tmp = [r['text'] for r in reg['synonyms']]
                except: sins_tmp = [ ]
                obj_join_sinonimos[k_reg] = sins_tmp

                if 'subsenses' in reg:
                    for reg_sub  in reg['subsenses']:
                        k_reg = pos + self.cfgs['separador'] + reg_sub['id']
                        try: sins_tmp = [r['text'] for r in reg_sub['synonyms']]
                        except: sins_tmp = [ ]
                        obj_join_sinonimos[k_reg] = sins_tmp

        # Realizando juncao de sinonimos
        obj_join_sinonimos_tmp = { }

        for k_reg in obj_join_sinonimos:
            if k_reg in obj_join_definicoes:
                obj_join_sinonimos_tmp[obj_join_definicoes[k_reg][0]] = obj_join_sinonimos[k_reg]

        for pos in obj_extrator:
            for def_prim in obj_extrator[pos]:
                if def_prim[:-1].lower() in obj_join_sinonimos_tmp:
                    sins = obj_join_sinonimos_tmp[def_prim[:-1].lower()]
                    obj_unificado[pos][def_prim]['sinonimos'] = sins

                for def_sec in obj_extrator[pos][def_prim]['def_secs']:
                    if def_sec[:-1].lower() in obj_join_sinonimos_tmp:
                        sins = obj_join_sinonimos_tmp[def_sec[:-1].lower()]
                        obj_unificado[pos][def_prim]['def_secs'][def_sec]['sinonimos'] = sins

        obj_join_sinonimos_tmp = None
        obj_join_definicoes = None
        obj_join_extrator = None
        obj_join_sinonimos = None
        obj_definicoes = None
        obj_sinonimos = None
        obj_extrator = None

        BaseOx.objs_unificados[palavra] = obj_unificado

        for pos_excluir in set(obj_unificado.keys())-set(self.cfgs['oxford']['pos']):
            if pos_excluir in obj_unificado:
                del obj_unificado[pos_excluir]

        if obj_unificado == None or  obj_unificado == { }:
            print("O objeto da palavra %s deu errado!"%palavra)

        return obj_unificado

    # Obtem sinonimos a partir da palavra, definicao, pos e do OBJETO UNIFICADO
    def obter_sins(self, palavra, definicao, pos=None):
        obj_unificado = self.construir_objeto_unificado(palavra)

        if pos == None:
            lista_pos = [pos for pos in obj_unificado.keys()]
        elif len(pos) == 1:
            lista_pos = [Util.cvrsr_pos_wn_oxford(pos)]

        try:
            for pos in lista_pos:
                for def_primaria in obj_unificado[pos]:
                    obj_filtrado = obj_unificado[pos][def_primaria]
                    if definicao in def_primaria or def_primaria in definicao:
                        return obj_filtrado['sinonimos']
                    for def_sec in obj_unificado[pos][def_primaria]['def_secs']:
                        if definicao in def_sec or def_sec in definicao:
                            return obj_filtrado['def_secs'][def_sec]['sinonimos']
        except Exception, e:
            wn = wordnet
            sins_def = self.extrair_sins_cands_def(definicao, pos)

            pos = pos.lower()[0]
            conj_lemas = set()

            for s in wn.synsets(palavra, pos):
                for shiper in s.hypernyms():
                    conj_lemas.update(shiper.lemma_names())
                for shipo in s.hyponyms():
                    conj_lemas.update(shipo.lemma_names())

            for s in wn.synsets(palavra, pos):
                for caminho_hiper in s.hypernym_paths():
                    for sh in caminho_hiper:
                        conj_lemas.update(set(set(set(sins_def) & set(sh.lemma_names()))))

            return [p for p in sins_def if p in conj_lemas and Util.e_mpalavra(p) == False]


        return None

    # Obter todas as definicoes
    def obter_definicoes(self, palavra, pos=None):
        obj_unificado = self.construir_objeto_unificado(palavra)

        if obj_unificado == None:
            pos_verb = "Verb"
            if pos == pos_verb:
                palavra = BaseOx.lematizador.lemmatize(palavra, pos=pos[0].lower())
                try:
                    return self.obter_definicoes(palavra, pos_verb)
                except Exception, e:
                    return None
        try:
            # Se POS = None, pegue todas as POS
            if pos != None:
                pos = Util.cvrsr_pos_wn_oxford(pos)

                if pos in obj_unificado:
                    obj_unificado = { pos: obj_unificado[pos] }
                else:
                    obj_unificado = dict()
            else:
                pass

            todas_definicoes = [ ]
        except (TypeError, AttributeError), e:
            return [ ]

        try:
            for pos in obj_unificado:
                for def_primaria in obj_unificado[pos]:
                    todas_definicoes.append(def_primaria)

                    for def_sec in obj_unificado[pos][def_primaria]['def_secs']:
                        todas_definicoes.append(def_sec)
        except: pass

        return todas_definicoes

    # Extrai todos (substantivos, verbos) de uma dada definicao e coloca como sinonimos candidatos
    def extrair_sins_cands_def(self, definicao, pos):
        return Util.extrair_sins_cands_def(definicao, pos)



class CliOxAPI(object):
    CLI = None

    palavras_singularizadas = { }

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

        dir_bases = self.configs['caminho_raiz_bases']
        cfg_cache = configs['oxford']['cache']

        self.dir_urls_invalidas_sinonimos = dir_bases+'/'+cfg_cache['obj_urls_invalidas_sinonimos']
        self.obj_urls_invalidas_sinonimos = Util.abrir_json(self.dir_urls_invalidas_sinonimos)

        self.dir_urls_invalidas_definicoes = dir_bases+'/'+cfg_cache['obj_urls_invalidas_definicoes']
        self.obj_urls_invalidas_definicoes = Util.abrir_json(self.dir_urls_invalidas_definicoes)

        if not self.obj_urls_invalidas_sinonimos:
            self.obj_urls_invalidas_sinonimos = dict()
        if not self.obj_urls_invalidas_definicoes:
            self.obj_urls_invalidas_definicoes = dict()

    def obter_lista_categoria(self, categoria):
        url = self.url_base + '/wordlist/en/registers=Rare;domains=' + categoria
        inicio = time.time()
        resultado = Util.requisicao_http(url, self.headers)
        fim = time.time()
        print('Tempo gasto para a URL %s: %s' + (url, str(fim-inicio)))
        return resultado

    def obter_frequencia(self, palavra):
        dir_cache = self.configs['oxford']['cache']['frequencias']

        todos_arquivos_cache = Util.list_arqs(self.configs['oxford']['cache']['frequencias'])
        todos_arquivos_cache = [c.split("/")[-1] for c in todos_arquivos_cache]

        if palavra + ".json" in todos_arquivos_cache:
            path = dir_cache+'/'+palavra + '.json'
            obj = Util.abrir_json(path)

            return obj['result']['frequency']
        else:
            url = self.url_base + '/stats/frequency/word/en/?corpus=nmc&lemma=' + palavra
            obj_req = Util.requisicao_http(url, self.headers)

            path = dir_cache+'/'+palavra + '.json'
            Util.salvar_json(path, obj_req.json())

            try:
                return obj_req.json()['result']['frequency']
            except Exception, e:
                return 0

    def obter_definicoes(self, palavra, lematizar=True):
        if palavra in self.obj_urls_invalidas_definicoes:
            return None

        dir_bases = self.configs['caminho_raiz_bases']
        dir_cache_oxford = dir_bases+'/'+self.configs['oxford']['cache']['definicoes']
        dir_obj_json = dir_cache_oxford+'/'+palavra+'.json'

        if os.path.isfile(dir_obj_json):            
            return Util.abrir_json(dir_obj_json)

        try:
            url = self.url_base+"/entries/en/"+palavra

            #Util.print_formatado('\nRequerindo URL %s' % url)
            obj = Util.requisicao_http(url, self.headers).json()

            saida_tmp = [ ]
            saida = { }

            for e in obj['results'][0]['lexicalEntries']:
                saida_tmp.append(e)
            for entry in saida_tmp:
                if not entry['lexicalCategory'] in saida: saida[entry['lexicalCategory']] = [ ]
                for sense in entry['entries'][0]['senses']:
                    saida[entry['lexicalCategory']].append(sense)

            print('ClienteOxford URL certa: ' + url)
            print('ClienteOxford: Salvando em cache: ' + str(Util.salvar_json(dir_obj_json, saida)))

            return saida
        except Exception, e:
            self.obj_urls_invalidas_definicoes[palavra] = ""
            Util.print_formatado('ClienteOxford: URL errada: '+palavra, visivel=False)
            return None

    def obter_sinonimos(self, palavra):
        if palavra in self.obj_urls_invalidas_sinonimos:
            Util.print_formatado('ClienteOxford: URL evitada: ' + palavra)
            return None

        dir_bases = self.configs['caminho_raiz_bases']
        dir_cache_oxford = dir_bases+'/'+self.configs['oxford']['cache']['sinonimos']        
        dir_obj_json = dir_cache_oxford+'/'+palavra+'.json'

        if os.path.isfile(dir_obj_json):
            return Util.abrir_json(dir_obj_json)

        try:
            url = self.url_base+"/entries/en/"+palavra+"/synonyms"
            obj = Util.requisicao_http(url, self.headers).json()
            obj_json = { }

            for entry in obj['results'][0]['lexicalEntries']:
                pos = entry['lexicalCategory']
                if not pos in obj_json:
                    obj_json[pos] = [ ]
                for sense in entry['entries'][0]['senses']:
                    obj_json[pos].append(sense)

            print('Salvando em cache: ' + str(Util.salvar_json(dir_obj_json, obj_json)))

            return obj_json
        except:
            self.obj_urls_invalidas_sinonimos[palavra] = ""
            #print('URL ERRADA: ' + url)
            return None

    def persistir_urls_invalidas(self):
        Util.salvar_json(self.dir_urls_invalidas_sinonimos, self.obj_urls_invalidas_sinonimos)
        Util.salvar_json(self.dir_urls_invalidas_definicoes, self.obj_urls_invalidas_definicoes)

    def obter_antonimos(self, palavra):
        url = "%s/entries/en/%s/antonyms" % (self.url_base, palavra)
        return Util.requisicao_http(url, self.headers)

    def __del__(self):
        try:
            self.persistir_urls_invalidas()
        except:
            traceback.print_exc()



class ExtWeb(object):
    EXT = None
    # Nome auto-explicativo
    cache_objetos_coletados = { }

    def __init__(self, cfgs):
        self.cfgs = cfgs

        dir_cache_ext = self.cfgs['oxford']['cache']['extrator_web']

        self.dir_raiz_bases = self.cfgs['caminho_raiz_bases']
        self.dir_cache = self.dir_raiz_bases+'/'+dir_cache_ext
        self.url_base_defs = self.cfgs['oxford']['url_base_definicoes']

    def iniciar_coleta(self, palavra):
        if palavra in ExtWeb.cache_objetos_coletados:
            return ExtWeb.cache_objetos_coletados[palavra]

        dir_cache_obj = "%s/%s.json"%(self.dir_cache, palavra)
        obj = Util.abrir_json(dir_cache_obj)

        if obj != None: return obj

        resultado = { }

        conjunto_frames = self.buscar_frame_principal(palavra)

        if not conjunto_frames:
            ExtWeb.cache_objetos_coletados[palavra] = None
            return None

        for frame in conjunto_frames:
            res_tmp = self.scrap_frame_definicoes(frame, palavra)

            # Se nao consegue sequer obter as POS, nao tem porque usar
            if res_tmp == None:
                ExtWeb.cache_objetos_coletados[palavra] = None
                return None

            # lista com UM elemento apenas
            pos = res_tmp.keys()[0]

            if not pos in resultado:
                resultado[pos] = dict()

            for def_primaria in res_tmp[pos]:
                resultado[pos][def_primaria] = res_tmp[pos][def_primaria]

        obj = json.loads(json.dumps(resultado))
        Util.salvar_json(dir_cache_obj, obj)

        ExtWeb.cache_objetos_coletados[palavra] = obj
        return obj

    # remove as aspas/crase das frases de exemplo selecionadas pelo coletor
    # Entrada: `frase de exemplo`       Saida: frase de exemplo
    def remove_aspas(self, frase):
        return frase[1:-1]

    def buscar_frames_principais_sinonimos(self, lemma):
        url_base = self.cfgs['oxford']['url_base_thesaurus']

        page = requests.get(url_base+'/'+lemma)
        tree = html.fromstring(page.content)

        path = "//*[@id='content']/div/div/div/div/div/div/section[h3/span[@class='pos']]"

        try:
            requests.session().cookies.clear()
        except: pass

        return tree.xpath(path)

    def obter_termos_sinonimos(self, lemma, f):
        elementos = self.buscar_frames_principais_sinonimos(lemma)

        resultados = { }

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
            page = requests.get(self.url_base_defs+'/'+termo)
        except:
            print("\nExcecao no metodo buscar_frame_principal() para o termo '%s'\n\n"%termo)

            palavra_sing = Util.singularize(termo)

            if palavra_sing != termo:
                return self.buscar_frame_principal(palavra_sing)
            else:
                print("\nExcecao no metodo buscar_frame_principal() para o termo '%s'\n\n"%termo)
                return None

        tree = html.fromstring(page.content)

        try:
            requests.session().cookies.clear()
        except: pass

        path = "//*[@id='content']/div[1]/div[2]/div/div/div/div[1]/section[@class='gramb']"
        principal = tree.xpath(path)

        return principal

    def scrap_frame_definicoes(self, frame, lema):
        resultado = { }

        pos = None

        try:
            pos = frame.find("h3[@class='ps pos']/span[@class='pos']").text.capitalize()
        except:
            # Se nao consegue achar a POS, todo o resto da extracao esta comprometido
            # print("\n\n@@@ Erro na extracao da POS-Tag da pagina para a query '%s'!\n\n"%lema)
            return None

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
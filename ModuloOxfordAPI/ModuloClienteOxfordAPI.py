from ModuloUtilitarios.Utilitarios import Utilitarios
import os
import traceback
import requests
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
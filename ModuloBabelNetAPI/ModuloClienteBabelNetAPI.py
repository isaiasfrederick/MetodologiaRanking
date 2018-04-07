from Utilitarios import Utilitarios
import requests
import json

class ClienteBabelAPI(object):
    def __init__(self, configs):
        self.configs = configs
        
        configs_babelnet = self.configs['babelnet']

        self.url_base = configs_babelnet['url_base']
        self.chave = configs_babelnet['app_key']
    
    def obter_versao(self):
        url = self.url_base + '/getVersion?key=' + self.chave
        return Utilitarios.requisicao_http(url)

    def recuperar_synsets(self, palavra):
        url = self.url_base + '/getSynsetIds?lemma=%s&searchLang=EN&key=%s' % (palavra, self.chave)
        return Utilitarios.requisicao_http(url)

    def obter_informacao_synset(self, synset_id):
        url = self.url_base + '/getSynset?id=%s&key=%s' % (synset_id, self.chave)
        resultado = Utilitarios.requisicao_http(url)

        exemplos = dict()
        definicoes = dict()

        for ex in resultado.json()['examples']:
            if not ex['sourceSense'] in exemplos:
                exemplos[ex['sourceSense']] = []
            exemplos[ex['sourceSense']].append(ex['example'])
        
        # merge de exemplos e definicoes
        for gl in resultado.json()['glosses']:
            if not gl['sourceSense'] in definicoes:
                definicoes[gl['sourceSense']] = {'definicoes': []}
                if gl['sourceSense'] in exemplos:
                    ex = exemplos[gl['sourceSense']]
                    definicoes[gl['sourceSense']]['exemplos'] = ex
                else:
                    definicoes[gl['sourceSense']]['exemplos'] = []

            definicoes[gl['sourceSense']]['definicoes'].append(gl['gloss'])

        return definicoes

    def recuperar_significado_synset(self, synset_id):
        url = self.url_base + '/getSenses?lemma=%s&searchLang=EN&key=%s' % (synset_id, self.chave)
        return Utilitarios.requisicao_http(url)

class ClienteSparQL(object):
    def __init__(self):
        pass
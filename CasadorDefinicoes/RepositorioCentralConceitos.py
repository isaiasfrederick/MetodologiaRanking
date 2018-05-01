#! coding: utf-8
from nltk.stem.porter import PorterStemmer
from nltk import word_tokenize, pos_tag
from nltk.corpus import wordnet as wn
from ModuloUtilitarios.Utilitarios import Utilitarios
from ModuloOxfordAPI.ModuloClienteOxfordAPI import BaseUnificadaObjetosOxford
import re
import json

# esta classe funcionara como um "casador" de definicoes de diferentes fontes da abordagem
class CasadorConceitos:
    def __init__(self, configs, base_unificada_oxford):
        self.base_unificada_oxford = base_unificada_oxford

        # retirar esta linha
        self.base_unificada_oxford = BaseUnificadaObjetosOxford(configs)

        self.stemmer = PorterStemmer()
        self.configs = configs
        self.sep = "[-_;]"

    def e_hiperonimo(self, hiponimo, hiperonimo):
        for c in hiponimo.hypernym_paths():
            if hiperonimo in c: return True
        return False

    def cache_contem(self, lema, pos):
        try:
            dir_cache = self.configs['aplicacao']['dir_cache_casador_definicoes']
            dir_saida = dir_cache + '/%s.%s.json' % (lema, pos)

            obj = open(dir_saida, 'r')
            obj_retorno = json.loads(obj.read())
            obj.close()

            return obj_retorno
        except:
            return None

    def salvar_casamento(self, lema, pos, resultado):
        try:
            dir_cache = self.configs['aplicacao']['dir_cache_casador_definicoes']
            dir_saida = dir_cache + '/%s.%s.json' % (lema, pos)

            obj = open(dir_saida, 'w')
            obj.write(json.dumps(resultado, indent=4))

            obj.close()
            return True
        except: return False

    def iniciar_casamento(self, lema, pos):
        obj_cache = self.cache_contem(lema, pos)

        if obj_cache:
            return obj_cache

        todas_definicoes_oxford = self.base_unificada_oxford.iniciar_consulta(lema)
        todos_synsets = wn.synsets(lema, pos[0].lower())

        # definicoes sem identação por definicoes        
        todas_definicoes_oxford = self.retirar_indentacao_coleta_oxford(lema, todas_definicoes_oxford)
        # filtrando por POS-tags
        todas_definicoes_oxford = [tupla[1:2][0] for tupla in todas_definicoes_oxford if pos in tupla[0]]

        print('\n\n')

        casamentos_autoreferenciados = self.casar_autoreferenciados(lema, pos, todas_definicoes_oxford)
        casamentos_hiperonimos = self.casar_hiperonimos(lema, todos_synsets, todas_definicoes_oxford)
        casamentos_meronimos = self.casar_meronimos(lema, todos_synsets, todas_definicoes_oxford)

        resultado_final = dict()

        print('\nCasamento autoreferenciados:')
        for cas in casamentos_autoreferenciados:
            print('-> ' + str(cas))
            def_oxford, hiper, dist_cosseno = cas
            if not def_oxford in resultado_final:
                if not hiper.name() in resultado_final.values():
                    resultado_final[def_oxford] = hiper.name()
        print('\n-------')

        print('\nCasamento hiperonimos:')
        for cas in casamentos_hiperonimos:
            print('-# ' + str(cas))
            def_oxford, hiper_name, dist_cosseno = cas
            if not def_oxford in resultado_final:
                if not hiper_name in resultado_final.values():
                    resultado_final[def_oxford] = hiper_name
        print('\n-------')

        print('\nCasamento meronimos:')
        for cas in casamentos_meronimos:
            print('-@ ' + str(cas))
            def_oxford, hiper_name, dist_cosseno = cas
            def_oxford, hiper_name, dist_cosseno = cas
            if not def_oxford in resultado_final:
                if not hiper_name in resultado_final.values():
                    resultado_final[def_oxford] = hiper_name
        print('\n-------')

        print('\n\n\n')
        raw_input(resultado_final)
        print('\n\n\n')
        self.salvar_casamento(lema, pos, resultado_final)

        return resultado_final

    # dado um conceito central através de um lema, retorne um conceito mais indicado
    def buscador_conceitos_centrais(self, lema, pos, doc):
        resultado = []
        doc = self.stemizar_frase(doc)

        for s in wn.synsets(lema, pos[0].lower()):
            resultado.append((s, Utilitarios.cosseno(s.definition(), doc)))

        resultado.sort(key=lambda k: k[1], reverse=True)
                
        return resultado

    # retorna todos hiperonimos para os significados dados por lema
    def busca_todos_hiperonimos(self, lema, todos_synsets, definicoes_oxford):
        resultados_oxford = dict()
        resultados_wordnet = dict()

        substantivos_univocos = list()
        contadores_substantivos_univocos = dict()

        # hiperonimos associados as definicoes de Oxford
        for def_oxford in definicoes_oxford:
            for substantivo in self.extrair_substantivos(def_oxford):
                if not substantivo in resultados_oxford:
                    resultados_oxford[substantivo] = list()

                resultados_oxford[substantivo].append(def_oxford)
        
        for synset in todos_synsets:
            for caminho_tmp in synset.hypernym_paths():
                caminho = list(caminho_tmp)
                caminho = caminho[:-1]
                caminho.reverse()

                for hiperonimo in caminho:
                    if not hiperonimo.name() in resultados_wordnet:
                        resultados_wordnet[hiperonimo.name()] = []

                    resultados_wordnet[hiperonimo.name()].append(synset)

        return (resultados_oxford, resultados_wordnet)

    def stemizar_frase(self, frase):
        return ' '.join([self.stemmer.stem(p) for p in frase.split(' ')])

    def mesclar_wordnet_oxford(self, lemma, obj_oxford):
        todos_synsets = wn.synsets(lemma, pos)

    def assinatura_relacionados(self, conjunto, incluir_definicao=False):
        sep = self.sep
        assinatura = ""

        for s in conjunto:
            assinatura += ' '.join([' ' + re.sub(sep, ' ', n) for n in s.lemma_names()])

            if incluir_definicao:
                assinatura += ' ' + re.sub(sep, ' ', s.definition())

        if len(conjunto):
            print('\t- Conjunto: ' + str(conjunto))
            print("\t\t- Assinatura: '%s'" % assinatura)

        return assinatura

    def assinatura_synset(self, s, usar_relacoes=True, \
        stem=True, remover_duplicatas=True, incluir_def_relacionados=False):

        sep = self.sep

        assinatura = ' '.join([' ' + re.sub(sep, ' ', n) for n in s.lemma_names()])
        assinatura += ' ' + re.sub(sep, ' ', s.definition())

        if usar_relacoes:
            assinatura += ' ' + self.assinatura_relacionados(s.member_meronyms())
            assinatura += ' ' + self.assinatura_relacionados(s.member_holonyms())
            assinatura += ' ' + self.assinatura_relacionados(s.part_meronyms())
            assinatura += ' ' + self.assinatura_relacionados(s.part_holonyms())

        if stem:
            assinatura = self.stemizar_frase(assinatura)

        if remover_duplicatas:
            assinatura = ' '.join(list(set(assinatura.split(' '))))

        return assinatura.lower()

    # retira substantivos da definicao todos substantivos da definicao
    def extrair_substantivos(self, definicao):
        pos_tags = pos_tag(word_tokenize(definicao))

        return [s[0] for s in pos_tags if s[1][0] == "N"]

    # retorna todos hiperonimos que casam com os synsets indexados pelo lema
    def extrair_hiperonimos_detectados(self, lema, pos, definicao):
        todos_substantivos = self.extrair_substantivos(definicao)

        resultados = dict()

        for s in wn.synsets(lema, pos[0].lower()):
            for caminho in s.hypernym_paths():
                for substantivo in todos_substantivos:
                    for sh in wn.synsets(substantivo, pos[0].lower()):
                        if sh in caminho:
                            if not sh.name() in resultados:
                                resultados[sh.name()] = list()

                            resultados[sh.name()].append(s.name())

        return resultados

    # retira do obj json a estrutura de aninhamento entre definicoes
    def retirar_indentacao_coleta_oxford(self, lema, obj_entrada):
        resultado = []
        cont = 1
        for pos in obj_entrada.keys():
            for definicao_prim in obj_entrada[pos].keys():
                nome_def = "%s.%s.%d" % (lema, pos, cont)
                exemplos = obj_entrada[pos][definicao_prim]['exemplos']

                d = (nome_def, definicao_prim, exemplos)
                resultado.append(d)

                cont += 1

                for definicao_sec in obj_entrada[pos][definicao_prim]['def_secs']:
                    nome_def = "%s.%s.%d" % (lema, pos, cont)
                    obj_def_sec = obj_entrada[pos][definicao_prim]['def_secs'][definicao_sec]
                    exemplos = obj_def_sec['exemplos']
                    d = (nome_def, definicao_sec, exemplos)
                    resultado.append(d)

                    cont += 1

        return resultado

    # checa se, a partir de uma definição Oxford, obtida pelo lema, encontra-se uma
    # referencia implicita a um UNICO conceito Wordnet que também é indexado por lema
    def buscar_conceitos_autorefenciados(self, lema, pos, definicao_oxford):
        todos_synsets = wn.synsets(lema, pos[0].lower())
        todos_substantivos = self.extrair_substantivos(definicao_oxford)

        resultado_parcial = []
        todos_lemas_unitarios_wordnet = {}

        for synset in todos_synsets:        
            for l in synset.lemma_names():
                if not l in todos_lemas_unitarios_wordnet:
                    todos_lemas_unitarios_wordnet[l] = 0
                todos_lemas_unitarios_wordnet[l] += 1

        todos_lemas_unitarios_wordnet = [e for e in todos_lemas_unitarios_wordnet if todos_lemas_unitarios_wordnet[e] == 1]

        for lema in todos_lemas_unitarios_wordnet:
            for subs in todos_substantivos:
                if subs == lema:
                    s1 = wn.synsets(subs, pos[0].lower())
                    s2 = wn.synsets(l, pos[0].lower())
                    synset = list(set(s1) & set(s2))[0]

                    for h in synset.hypernyms():
                        resultado_parcial.append(h)

        return resultado_parcial

    # metodo que acha todos conceitos (Oxford, Wordnet) que compartilham mesmo lema
    def casar_autoreferenciados(self, lema, pos, todas_definicoes_oxford):
        casamentos_autoreferenciado = []

        for def_oxford in todas_definicoes_oxford:
            ca_tmp = self.buscar_conceitos_autorefenciados(lema, pos, def_oxford)
            for synset in ca_tmp:
                todos_lemas = Utilitarios.juntar_tokens(synset.lemma_names())
                todos_lemas = ' '.join(todos_lemas)
                def_wordnet = synset.definition() + ' ' + todos_lemas
                print('Auto-referenciado:')
                raw_input((def_oxford, synset))
                dist_cosseno = Utilitarios.cosseno(def_oxford.lower(), def_wordnet.lower())                
                casamentos_autoreferenciado.append((def_oxford, synset, dist_cosseno))

        return sorted(casamentos_autoreferenciado, key=lambda x: x[2], reverse=True)

    # metodo que acha todos conceitos (Oxford, Wordnet) que compartilham mesmo hiperonimo
    def casar_hiperonimos(self, lema, todos_synsets, todas_definicoes_oxford):
        hiper_oxford, hiper_wordnet = self.busca_todos_hiperonimos(lema, todos_synsets, todas_definicoes_oxford)
        hiper_wordnet_unitarios = [h for h in hiper_wordnet if len(hiper_wordnet[h]) == 1]

        casamentos_hiperonimos = []

        for h in hiper_oxford:
            if len(hiper_oxford[h]) == 1:
                for h_wn in hiper_wordnet_unitarios:
                    synset = wn.synset(h_wn)
                    if h in synset.lemma_names():
                        def_oxford = hiper_oxford[h][0]
                        todos_lemas = Utilitarios.juntar_tokens(wn.synset(h_wn).lemma_names())
                        def_wordnet = synset.definition() + ' ' + ' '.join(todos_lemas)
                        print('Hiperonimos:')
                        raw_input((def_oxford, synset))
                        cosseno = Utilitarios.cosseno(def_wordnet, def_oxford)
                        casamentos_hiperonimos.append((def_oxford, h_wn, cosseno))

        return sorted(casamentos_hiperonimos, key=lambda x: x[2], reverse=True)

    # metodo que acha todos conceitos (Oxford, Wordnet) que compartilham mesmo hiperonimo
    def casar_meronimos(self, lema, todos_synsets, todas_definicoes_oxford):
        hiper_oxford, hiper_wordnet = self.busca_todos_hiperonimos(lema, todos_synsets, todas_definicoes_oxford)
        todos_synsets = wn.synsets(lema)
        casamentos_meronimos = []

        hiper_oxford_filtrados = []
        hiper_wordnet_filtrados = []

        for l in hiper_oxford:
            for h in wn.synsets(l):
                for s in todos_synsets:
                    if self.e_hiperonimo(s, h):
                        hiper_oxford_filtrados.append(l)

        for h in hiper_oxford_filtrados:
            for h_wn in hiper_wordnet:
                if h in wn.synset(h_wn).lemma_names():
                    hiper_wordnet_filtrados.append(h_wn)

        hiper_oxford_filtrados = list(set(hiper_oxford_filtrados))
        hiper_wordnet_filtrados = list(set(hiper_wordnet_filtrados))

        for h in hiper_oxford_filtrados:
            for h_wn in hiper_wordnet_filtrados:
                synset = wn.synset(h_wn)
                for hiponimo in todos_synsets:
                    def_oxford = hiper_oxford[h][0]

                    todos_lemas = Utilitarios.juntar_tokens(wn.synset(h_wn).lemma_names())
                    def_wordnet = synset.definition() + ' ' + ' '.join(todos_lemas)

                    cosseno = Utilitarios.cosseno(def_wordnet, def_oxford)
                    casamentos_meronimos.append((def_oxford, h_wn, cosseno))


        raw_input('\n\n\n<ENTER>')
        return sorted(casamentos_meronimos, key=lambda x: x[2], reverse=True)
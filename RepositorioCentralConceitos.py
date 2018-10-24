#! coding: utf-8
from nltk.stem.porter import PorterStemmer
from nltk import word_tokenize, pos_tag
from nltk.corpus import wordnet as wn
from Utilitarios import Utils
from ModuloBasesLexicas.ModuloClienteOxfordAPI import BaseUnificadaOx
from pywsd.utils import lemmatize, porter, lemmatize_sentence
from nltk.corpus import stopwords, wordnet
import re
import json

# Esta classe funcionara como um "casador"
# de definicoes de diferentes fontes da abordagem
class CasadorConceitos:
    def __init__(self, configs, base_ox):
        self.base_ox = base_ox

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

    # salva o resultado de um casamento no cache
    def salvar_casamento(self, lema, pos, resultado):
        try:
            dir_cache = self.configs['aplicacao']['dir_cache_casador_definicoes']
            dir_saida = dir_cache + '/%s.%s.json' % (lema, pos)

            obj = open(dir_saida, 'w')
            obj.write(json.dumps(resultado, indent=4))

            obj.close()

            return True
        except: return False

    # salva o resultado de um casamento no cache
    def iniciar_casamento(self, lema, pos):
        obj_cache = self.cache_contem(lema, pos)

        if obj_cache:
            return obj_cache

        #todas_definicoes_oxford = self.base_ox.iniciar_consulta(lema)
        raw_input(self.base_ox)
        raw_input(type(lema))
        todas_definicoes_oxford = self.base_ox.obter_obj_unificado(lema)

        try:
            todos_synsets = wn.synsets(lema, pos[0].lower())
        except:
            import traceback
            traceback.print_stack()

        if todas_definicoes_oxford:            
            # definicoes sem identação por definicoes        
            todas_definicoes_oxford = self.retirar_indentacao_coleta_oxford(lema, todas_definicoes_oxford)
            # filtrando por POS-tags
            todas_definicoes_oxford = [tupla[1:2][0] for tupla in todas_definicoes_oxford if pos in tupla[0]]

            casamentos_autoreferenciados = self.casar_autoreferenciados(lema, pos, todas_definicoes_oxford)
            casamentos_hiperonimos = self.casar_hiperonimos(lema, pos, todos_synsets, todas_definicoes_oxford)
            casamentos_meronimos = self.casar_meronimos(lema, pos, todos_synsets, todas_definicoes_oxford)
            casamentos_hiponimos = self.casar_hiponimos(lema, pos, todos_synsets, todas_definicoes_oxford)

            resultado_final = dict()

            for cas in casamentos_autoreferenciados:
                def_oxford, synset_autoreferenciado, dist_cosseno = cas
                if not def_oxford in resultado_final:
                    if not synset_autoreferenciado.name() in resultado_final.values():
                        resultado_final[def_oxford] = synset_autoreferenciado.name()

            for cas in casamentos_hiperonimos:
                def_oxford, hiper_name, dist_cosseno = cas
                if not def_oxford in resultado_final:
                    if not hiper_name in resultado_final.values():
                        resultado_final[def_oxford] = hiper_name

            for cas in casamentos_meronimos:
                def_oxford, hiper_name, dist_cosseno = cas
                def_oxford, hiper_name, dist_cosseno = cas
                if not def_oxford in resultado_final:
                    if not hiper_name in resultado_final.values():
                        resultado_final[def_oxford] = hiper_name

            for cas in casamentos_hiponimos:
                def_oxford, hiper_name, dist_cosseno = cas
                def_oxford, hiper_name, dist_cosseno = cas
                if not def_oxford in resultado_final:
                    if not hiper_name in resultado_final.values():
                        resultado_final[def_oxford] = hiper_name

            self.salvar_casamento(lema, pos, resultado_final)
    
        else:
            print('\n\nA definicao para a palavra %s nao funcionou!\n' % lema)
            return None

        return resultado_final


    # dado um conceito central através de um lema, retorne um conceito mais indicado
    def buscador_conceitos_centrais(self, lema, pos, doc):
        resultado = [ ]
        doc = self.stemizar_frase(doc)

        for s in wn.synsets(lema, pos[0].lower()):
            resultado.append((s, Utils.cosseno(s.definition(), doc)))

        resultado.sort(key=lambda k: k[1], reverse=True)
                
        return resultado

    # busca nas definicoes de Oxford todos hiponimos de conceitos acessiveis por lema
    def busca_todos_hiponimos(self, lema, todos_synsets, definicoes_oxford):
        substantivos_oxford = dict()

        hiponimos_filtrados_oxford = dict()

        for def_oxford in definicoes_oxford:
            for substantivo in self.extrair_substantivos(def_oxford):
                if not substantivo in substantivos_oxford:
                    substantivos_oxford[substantivo] = list()

                substantivos_oxford[substantivo].append(def_oxford)

        for lema_hipo_oxf in substantivos_oxford:
            for hipo_oxf in wn.synsets(lema_hipo_oxf):
                for def_oxford in substantivos_oxford[lema_hipo_oxf]:
                    for caminho in hipo_oxf.hypernym_paths():
                        intersecao = set(caminho[:-1]) & set(todos_synsets)
                        for hiperonimo in intersecao:
                            hiponimos_filtrados_oxford[lema_hipo_oxf] = (def_oxford, hipo_oxf, hiperonimo)

        return hiponimos_filtrados_oxford

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
                        resultados_wordnet[hiperonimo.name()] = [ ]

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

        return assinatura

    def assinatura_definicao_lema(self, synset):
        todos_lemas = Utils.juntar_tokens(synset.lemma_names())
        todos_lemas = ' '.join(todos_lemas)

        definicao = synset.definition() + ' ' + todos_lemas

        return definicao

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
    def retirar_indentacao_coleta_oxford(self, lema, obj_entrada_unificado):
        if not obj_entrada_unificado:
            return None

        resultado = [ ]
        cont = 1
        for pos in obj_entrada_unificado.keys():
            for definicao_prim in obj_entrada_unificado[pos].keys():
                nome_def = "%s.%s.%d" % (lema, pos, cont)
                exemplos = obj_entrada_unificado[pos][definicao_prim]['exemplos']

                d = (nome_def, definicao_prim, exemplos)
                resultado.append(d)

                cont += 1

                for definicao_sec in obj_entrada_unificado[pos][definicao_prim]['def_secs']:
                    nome_def = "%s.%s.%d" % (lema, pos, cont)
                    obj_def_sec = obj_entrada_unificado[pos][definicao_prim]['def_secs'][definicao_sec]
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

        resultado_parcial = [ ]
        todos_lemas_unitarios_wordnet = {}

        for synset in todos_synsets:        
            for l in synset.lemma_names():
                if not l in todos_lemas_unitarios_wordnet:
                    todos_lemas_unitarios_wordnet[l] = 0
                todos_lemas_unitarios_wordnet[l] += 1

        todos_lemas_unitarios_wordnet = \
        [e for e in todos_lemas_unitarios_wordnet if todos_lemas_unitarios_wordnet[e] == 1]

        for lema in todos_lemas_unitarios_wordnet:
            for subs in todos_substantivos:
                if subs == lema:
                    s1 = wn.synsets(subs, pos[0].lower())
                    s2 = wn.synsets(l, pos[0].lower())

                    try:
                        synset = list(set(s1) & set(s2))[0]

                        for h in synset.hypernyms():
                            assinatura_synset = self.assinatura_definicao_lema(synset)
                            dist_cosseno = Utils.cosseno(definicao_oxford.lower(), assinatura_synset.lower())

                            resultado_parcial.append((definicao_oxford, synset, dist_cosseno))
                    except: pass

        return resultado_parcial

    # metodo que acha todos conceitos (Oxford, Wordnet) que compartilham mesmo lema
    def casar_autoreferenciados(self, lema, pos, todas_definicoes_oxford):
        casamentos_autoreferenciado = [ ]

        for def_oxford in todas_definicoes_oxford:
            ca_tmp = self.buscar_conceitos_autorefenciados(lema, pos, def_oxford)
            for d, synset, dist_cosseno in ca_tmp:
                assinatura_synset = self.assinatura_definicao_lema(synset)
                dist_cosseno = Utils.cosseno(def_oxford.lower(), assinatura_synset.lower())
                casamentos_autoreferenciado.append((def_oxford, synset, dist_cosseno))

        return sorted(casamentos_autoreferenciado, key=lambda x: x[2], reverse=True)


    # metodo que acha todos conceitos (Oxford, Wordnet) que compartilham mesmo hiperonimo
    def casar_hiperonimos(self, lema, pos, todos_synsets, todas_definicoes_oxford):
        todos_hiper_oxford, todos_hiper_wordnet = \
        self.busca_todos_hiperonimos(lema, todos_synsets, todas_definicoes_oxford)

        casamentos_hiperonimos = [ ]

        for hiper_oxf in todos_hiper_oxford:
            if todos_hiper_oxford[hiper_oxf].__len__() == 1:
                for lema_hiperonimo_wn in todos_hiper_wordnet:
                    if todos_hiper_wordnet[lema_hiperonimo_wn].__len__() == 1:
                        synset_hiper = wn.synset(lema_hiperonimo_wn)
                        if hiper_oxf in synset_hiper.lemma_names():
                            synset_hipo = todos_hiper_wordnet[lema_hiperonimo_wn][0]

                            def_oxford = todos_hiper_oxford[hiper_oxf][0]         
                            assinatura_wordnet = self.assinatura_definicao_lema(synset_hipo)

                            cosseno = Utils.cosseno(assinatura_wordnet, def_oxford)
                            casamentos_hiperonimos.append((def_oxford, synset_hipo.name(), cosseno))

        return sorted(casamentos_hiperonimos, key=lambda x: x[2], reverse=True)


    # metodo que acha todos conceitos (Oxford, Wordnet) que compartilham mesmo hiperonimo
    def casar_meronimos(self, lema, pos, todos_synsets, todas_definicoes_oxford):
        todos_hiper_oxford, todos_hiper_wordnet = \
        self.busca_todos_hiperonimos(lema, todos_synsets, todas_definicoes_oxford)

        casamentos_hiperonimos = [ ]

        for hiper_oxf in todos_hiper_oxford:
            for lema_hiperonimo_wn in todos_hiper_wordnet:
                synset_hiper = wn.synset(lema_hiperonimo_wn)
                if hiper_oxf in synset_hiper.lemma_names():
                    for synset_hipo in todos_hiper_wordnet[lema_hiperonimo_wn]:
                        for def_oxford in todos_hiper_oxford[hiper_oxf]:
                            assinatura_wordnet = self.assinatura_definicao_lema(synset_hipo)

                            resultado = self.maximizar_caminho(synset_hipo, synset_hiper, def_oxford)

                            cosseno = Utils.cosseno(assinatura_wordnet, def_oxford)
                            casamentos_hiperonimos.append((def_oxford, synset_hipo.name(), cosseno))

        return sorted(casamentos_hiperonimos, key=lambda x: x[2], reverse=True)


    def maximizar_caminho(self, hiponimo, hiperonimo, def_oxford):
        contadores = [ ]
        todos_caminhos = hiponimo.hypernym_paths()

        for caminho_tmp in todos_caminhos:
            try:
                caminho = list(caminho_tmp)
                caminho.reverse()
                index = caminho.index(hiperonimo) + 1 

                caminho = caminho[0:index]

                ass = ""

                for synset in caminho:
                    ass += self.assinatura_synset(synset, usar_relacoes=True)

                sobreposicoes = self.lesk(def_oxford, ass)
                contadores.append((caminho, sobreposicoes))
            except:
                pass

        return sorted(contadores, key=lambda x: x[1], reverse=True)[0]


    def lesk(self, definicao, assinatura):
        assinatura = assinatura.split(' ')

        definicao = " ".join(lemmatize_sentence(definicao))        
        definicao = definicao.split(' ')

        if True:
            definicao = [i for i in definicao if i not in stopwords.words('english')]
        if True:
            definicao = [lemmatize(i) for i in definicao]
        if True:
            definicao = [porter.stem(i) for i in definicao]

        intersecao = list(set(definicao) & set(assinatura))
        resultado = intersecao, len(definicao), len(assinatura)

        return intersecao, len(definicao), len(assinatura)

    # metodo que acha todos conceitos (Oxford, Wordnet) que compartilham mesmo hiperonimo
    def casar_hiponimos(self, lema, pos, todos_synsets, todas_definicoes_oxford):
        casamento_hiponimos = list()
        resultado_hiponimos = self.busca_todos_hiponimos(lema, todos_synsets, todas_definicoes_oxford)

        for lema_hiponimo_oxford in resultado_hiponimos:
            registro = resultado_hiponimos[lema_hiponimo_oxford]

            def_oxford, hiponimo, hiperonimo = registro

            assinatura_wordnet = self.assinatura_definicao_lema(hiperonimo)
            cosseno = Utils.cosseno(assinatura_wordnet, def_oxford)

            casamento_hiponimos.append((def_oxford, hiperonimo.name(), cosseno))

        return casamento_hiponimos

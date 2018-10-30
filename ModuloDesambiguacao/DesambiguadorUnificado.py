from ModuloBasesLexicas.ModuloClienteOxfordAPI import BaseUnificadaOx
from RepositorioCentralConceitos import CasadorConceitos
from pywsd.utils import lemmatize, porter, lemmatize_sentence
from Utilitarios import Util
from nltk.tokenize import word_tokenize
from pywsd.cosine import cosine_similarity as cos_sim
from pywsd.lesk_isaias import cosine_lesk
from ModuloBasesLexicas.ModuloClienteOxfordAPI import *
from nltk.corpus import stopwords, wordnet
from nltk import pos_tag, word_tokenize
from nltk.corpus import wordnet
from itertools import chain
import re


class DesambiguadorUnificado(object):
    def __init__(self, configs, base_ox):
        self.configs = configs
        self.base_ox = base_ox
        self.casador_conceitos = CasadorConceitos(self.configs, self.base_ox)

    # obtem hiperonimo ja casado entre as diferentes
    # fontes para compor a assinatura ho hiponimo
    def obter_assinatura_definicao_casada(self, configs, lema, pos, synset_lema):
        assinatura = [ ]

        if pos.__len__() == 1:
            pos = Util.conversor_pos_wn_oxford(pos)

        casador_conceitos = CasadorConceitos(configs, self.base_ox)
        casamentos = casador_conceitos.iniciar_casamento(lema, pos)
        def_oxford_definitiva = None;

        for def_oxford in casamentos:
            if synset_lema.name() == casamentos[def_oxford]:
                def_oxford_definitiva = def_oxford

        todas_definicoes = self.base_ox.iniciar_consulta(lema)

        for sense in todas_definicoes[pos]:
            exemplos = [ ]

            if sense == def_oxford_definitiva:
                try:
                    exemplos = todas_definicoes[pos][sense]['exemplos']
                except: exemplos = [ ]

            try:
                if not len(exemplos):
                    for subsense in todas_definicoes[pos][sense]['def_secs']:
                        exemplos = todas_definicoes[pos][sense]['def_secs'][subsense]['exemplos']
            except: pass

            assinatura += list(chain(*[self.retornar_valida(ex).split() for ex in exemplos]))
            assinatura += [p for p in word_tokenize(def_oxford_definitiva.lower()) if not p in [',', ';', '.']]

        return assinatura

    def assinaturas_significados(self, inventario, usar_exemplos, usar_ontologia):
        if not inventario:
            return None

        assinaturas = [ ]

        for registro in inventario:
            ass_tmp = ""

            try:
                for assinatura_hiper in registro['definicoes']:
                    ass_tmp += ' ' + re.sub('[-_]', ' ', assinatura_hiper)
            except TypeError: pass

            if usar_ontologia:
                for hiperonimo in registro['hiperonimos']:
                    lema = hiperonimo.lemma_names()[0]
                    ass_tmp += ' ' + re.sub('[_-]', ' ', hiperonimo.definition())
                    assinatura_hiper = self.obter_assinatura_definicao_casada(self.configs, lema, registro['pos'], hiperonimo)
                    
                    ass_tmp += ' ' + ' '.join(assinatura_hiper)

            try:
                ass_tmp += ' '.join([re.sub('[_-]', ' ', assinatura_hiper) for assinatura_hiper in registro['lemas']])
            except TypeError: pass

            ass_tmp = re.sub('[,.;]', ' ', ass_tmp)
            ass_tmp = ass_tmp.replace(')', ' ')
            ass_tmp = ass_tmp.replace('(', ' ')
            ass_tmp = re.sub('[-_]', ' ', ass_tmp)

            ass_tmp = ass_tmp.lower()
            ass_tmp = ass_tmp.split(' ')

            if usar_exemplos:
                try:
                    lista_exemplos = registro['exemplos']
                    assinatura_exemplos = list(chain(*[self.retornar_valida(ex).split() for ex in lista_exemplos]))
                    ass_tmp += assinatura_exemplos
                except: pass

            ass_tmp = [palavra.lower() for palavra in ass_tmp]
            ass_tmp = [p for p in ass_tmp if p != ""]

            try:
                assinaturas.append((registro['definicoes'], ass_tmp))
            except TypeError: pass

        return assinaturas

    def retornar_valida(self, frase):
        return Util.retornar_valida(frase)

# extrair_sinonimos(contexto, palavra, pos=pos, usar_exemplos=False, busca_ampla=True, repetir=True, coletar_todos=False)

    def BKP_extrair_sinonimos2(self, frase, palavra, pos=None, usar_exemplos=False, busca_ampla=False, repetir=False, coletar_todos=True):
        max_sinonimos = 10
        
        resultado = self.adapted_cosine_lesk(frase, palavra, pos, usar_exemplos=usar_exemplos)
        sinonimos = [ ]

        for item in resultado:
            definicao, pontuacao = item[0], item[1]

            if sinonimos.__len__() < max_sinonimos:
                obj_unificado = self.base_ox.obter_obj_unificado(palavra)
                sinonimos_tmp = self.base_ox.obter_sinonimos_fonte_obj_unificado(pos, definicao, obj_unificado)

                if not sinonimos_tmp:                    
                    sinonimos_tmp = self.base_ox.extrair_sinonimos_candidatos_definicao(definicao, pos)

                for s in [s for s in sinonimos_tmp if Util.e_multipalavra(s) == False]:
                    sinonimos.append(s)

        return sinonimos[:max_sinonimos]

    def adapted_cosine_lesk(self, lista_ctx, ambigua, pos, nbest=True, lematizar=True, stem=True, stop=True, usar_ontologia=False, usar_exemplos=False, busca_ampla=False, inventario_unificado=True):
        if inventario_unificado:
            inventario = self.construir_inventario_unificado(ambigua, pos)
        else:
            inventario = self.construir_inventario_estendido(ambigua, pos)

        todas_assinaturas = self.assinaturas_significados(inventario, usar_ontologia=usar_ontologia, usar_exemplos=usar_exemplos)

        lista_ctx = [p for p in word_tokenize(lista_ctx.lower()) if not p in [',', ';', '.']]        
        lista_ctx = Util.processar_ctx(lista_ctx, stop=True, lematizar=True, stem=True)

        pontuacao = [ ]

        if None == todas_assinaturas: todas_assinaturas = [ ]

        for a in todas_assinaturas:
            ass_tmp = a[1]
            ass_tmp = Util.processar_ctx(ass_tmp, stop=True, lematizar=True, stem=True)

            pontuacao.append((cos_sim(" ".join(lista_ctx), " ".join(ass_tmp)), a[0]))

        resultado = [(s, p) for p, s in sorted(pontuacao, reverse=True)]

        return resultado if nbest else [resultado[0]]

    def extrair_sinonimos(self, ctx, palavra, pos=None, usar_exemplos=False, busca_ampla=False, repetir=False, coletar_todos=True):
        max_sinonimos = 10

        obter_objeto_unificado_oxford = self.base_ox.obter_obj_unificado
        obter_sinonimos_oxford = self.base_ox.obter_sinonimos_fonte_obj_unificado

        try:
            resultado = self.adapted_cosine_lesk(ctx, palavra, pos, usar_exemplos=usar_exemplos, busca_ampla=busca_ampla, inventario_unificado=False)
        except Exception, e:
            resultado = [ ]

        sinonimos = [ ]

        try:
            if resultado[0][1] == 0:
                resultado = [resultado[0]]
                repetir = False
            else:
                resultado = [item for item in resultado if item[1] > 0]
        except:
            resultado = [ ]

        continuar = bool(resultado)

        while len(sinonimos) < max_sinonimos and continuar:
            len_sinonimos = len(sinonimos)

            for item in resultado:
                lista_definicoes = item[0]
                definicao_unificada, pontuacao = item[0], item[1]

                if len(sinonimos) < max_sinonimos:
                    try:                        
                        obj_unificado = obter_objeto_unificado_oxford(palavra)
                        sinonimos_tmp = None

                        indice_definicoes = 0

                        while indice_definicoes < len(lista_definicoes):
                            def_corrente = lista_definicoes[indice_definicoes]
                            sinonimos_tmp = obter_sinonimos_oxford(pos, def_corrente, obj_unificado)

                            if sinonimos_tmp: indice_definicoes = len(lista_definicoes)
                            else: indice_definicoes += 1

                        if not sinonimos_tmp:
                            for synset in wn.synsets(pos, n):
                                if synset.definition() in lista_definicoes:
                                    sinonimos_tmp = synset.lemma_names()

                        sinonimos_tmp = [s for s in sinonimos_tmp if not Util.e_multipalavra(s)]
                        sinonimos_tmp = list(set(sinonimos_tmp) - set(sinonimos))

                        if coletar_todos: sinonimos += sinonimos_tmp
                        elif sinonimos_tmp: sinonimos += [sinonimos_tmp[0]]

                    except: pass
                else: continuar = False

            if repetir == False: continuar = False
            elif len_sinonimos == len(sinonimos): continuar = False

        return sinonimos[:max_sinonimos]

    def construir_inventario_estendido(self, palavra, pos, usar_ontologia=True):
        pos = Util.conversor_pos_wn_oxford(pos)

        inventario = [ ]

        try:
            todas_definicoes_oxford = { pos: self.base_ox.obter_obj_unificado(palavra)[pos] }
            todas_definicoes_oxford = self.desindentar_coleta_oxford(palavra, todas_definicoes_oxford)
        except Exception, e:
            todas_definicoes_oxford = [ ]

        for synset in wordnet.synsets(palavra, pos[0].lower()):
            registro = {}

            registro['synset'] = synset.name()
            registro['definicoes'] = [synset.definition()]
            registro['fontes'] = ['wordnet']
            registro['exemplos'] = synset.examples()
            registro['hiperonimos'] = synset.hypernyms()
            registro['lemas'] = synset.lemma_names()
            registro['pos'] = pos[0].lower()

            inventario.append(registro)

        for reg in todas_definicoes_oxford:
            nome, def_oxford, exemplos = reg
            if True:
                registro = {}

                registro['synset'] = None
                registro['fontes'] = ['oxford']
                registro['definicoes'] = [def_oxford]
                registro['exemplos'] = exemplos
                registro['pos'] = pos[0].lower()

                if not usar_ontologia:
                    registro['hiperonimos'] = [ ]
                else:
                    registro['hiperonimos'] = [ ]

                registro['lemas'] = [ ]

                inventario.append(registro)

        return inventario

    def construir_inventario_unificado(self, palavra, pos, usar_ontologia=True):
        pos = Util.conversor_pos_wn_oxford(pos)

        inventario = [ ]
        # indexado (def_oxford, synset_name)
        casamentos = self.casador_conceitos.iniciar_casamento(palavra, pos)
        # indexado (synset_name, def_oxford)
        casamentos_invertidos = dict()

        if not casamentos:
            print('Objeto de casamentos e nulo! Abortando a funcao...')
            print('Palavra: %s\tPOS: %s' % (palavra, pos))
            
            return 

        try:
            todas_definicoes_oxford = { pos: self.base_ox.obter_obj_unificado(palavra)[pos] }
            todas_definicoes_oxford = self.desindentar_coleta_oxford(palavra, todas_definicoes_oxford)
        except Exception, e:
            traceback.print_exc()
            print(e)
            raw_input('Excecao na construcao do inventario unificado de dicionarios!')            

        for def_oxford in casamentos:
            casamentos_invertidos[casamentos[def_oxford]] = def_oxford

        for synset in wordnet.synsets(palavra, pos[0].lower()):
            registro = {}

            registro['synset'] = synset.name()
            registro['definicoes'] = [synset.definition()]
            registro['fontes'] = ['wordnet']
            registro['exemplos'] = synset.examples()
            registro['hiperonimos'] = synset.hypernyms()
            registro['lemas'] = synset.lemma_names()
            registro['pos'] = pos[0].lower()

            # inserindo o casamento no inventario
            if synset.name() in casamentos_invertidos:
                def_oxford = casamentos_invertidos[synset.name()]
                for reg in todas_definicoes_oxford:
                    if def_oxford in reg:
                        registro['fontes'].append('oxford')
                        registro['definicoes'].append(def_oxford)
                        registro['exemplos'] += reg[2]

            inventario.append(registro)

        for reg in todas_definicoes_oxford:
            nome, def_oxford, exemplos = reg
            if not def_oxford in casamentos:
                registro = {}

                registro['synset'] = None
                registro['fontes'] = ['oxford']
                registro['definicoes'] = [def_oxford]
                registro['exemplos'] = exemplos
                registro['pos'] = pos[0].lower()

                if not usar_ontologia:
                    registro['hiperonimos'] = [ ]
                else:
                    registro['hiperonimos'] = [ ]

                registro['lemas'] = [ ]

                inventario.append(registro)

        return inventario

    # retira do obj json a estrutura de aninhamento entre definicoes
    def desindentar_coleta_oxford(self, lema, obj_entrada):
        resultado = [ ]
        cont = 1
        for pos in obj_entrada.keys():
            for definicao_prim in obj_entrada[pos].keys():
                nome_def = "%s.%s.%d" % (lema, pos, cont)
                exemplos = obj_entrada[pos][definicao_prim]['exemplos']

                def_oxford = (nome_def, definicao_prim, exemplos)
                resultado.append(def_oxford)

                cont += 1

                for definicao_sec in obj_entrada[pos][definicao_prim]['def_secs']:
                    nome_def = "%s.%s.%d" % (lema, pos, cont)
                    obj_def_sec = obj_entrada[pos][definicao_prim]['def_secs'][definicao_sec]
                    exemplos = obj_def_sec['exemplos']
                    def_oxford = (nome_def, definicao_sec, exemplos)
                    resultado.append(def_oxford)

                    cont += 1

        return resultado
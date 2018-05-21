from ModuloOxfordAPI.ModuloClienteOxfordAPI import BaseUnificadaObjetosOxford
from CasadorDefinicoes.RepositorioCentralConceitos import CasadorConceitos
from pywsd.utils import lemmatize, porter, lemmatize_sentence
from ModuloUtilitarios.Utilitarios import Utilitarios
from nltk.tokenize import word_tokenize
from pywsd.cosine import cosine_similarity as cos_sim
from pywsd.lesk_isaias import cosine_lesk
from ModuloOxfordAPI.ModuloClienteOxfordAPI import *
from nltk.corpus import stopwords, wordnet
from nltk import pos_tag, word_tokenize
from nltk.corpus import wordnet
from itertools import chain
import re


class DesambiguadorUnificado(object):
    def __init__(self, configs, base_unificada_oxford):
        self.configs = configs
        self.base_unificada_oxford = base_unificada_oxford
        self.casador_conceitos = CasadorConceitos(self.configs, self.base_unificada_oxford)

    # obtem hiperonimo ja casado entre as diferentes
    # fontes para compor a assinatura ho hiponimo
    def obter_assinatura_definicao_casada(self, configs, lema, pos, synset_lema):
        assinatura = []

        if pos.__len__() == 1:
            pos = Utilitarios.conversor_pos_wn_oxford(pos)

        casador_conceitos = CasadorConceitos(configs, self.base_unificada_oxford)
        casamentos = casador_conceitos.iniciar_casamento(lema, pos)
        def_oxford_definitiva = None;

        for def_oxford in casamentos:
            if synset_lema.name() == casamentos[def_oxford]:
                def_oxford_definitiva = def_oxford

        todas_definicoes = self.base_unificada_oxford.iniciar_consulta(lema)

        for sense in todas_definicoes[pos]:
            exemplos = []

            if sense == def_oxford_definitiva:
                try:
                    exemplos = todas_definicoes[pos][sense]['exemplos']
                except: exemplos = []

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

        assinaturas = []

        for registro in inventario:
            ass_tmp = ""

            try:
                lista_exemplos = registro['exemplos']
            except:
                lista_exemplos = []
                traceback.print_exc()

            for assinatura_hiper in registro['definicoes']: ass_tmp += ' ' + re.sub('[-_]', ' ', assinatura_hiper)

            if usar_ontologia:
                for hiperonimo in registro['hiperonimos']:
                    lema = hiperonimo.lemma_names()[0]
                    ass_tmp += ' ' + re.sub('[_-]', ' ', hiperonimo.definition())
                    assinatura_hiper = self.obter_assinatura_definicao_casada(self.configs, lema, registro['pos'], hiperonimo)
                    
                    ass_tmp += ' ' + ' '.join(assinatura_hiper)

            ass_tmp += ' '.join([re.sub('[_-]', ' ', assinatura_hiper) for assinatura_hiper in registro['lemas']])

            ass_tmp = re.sub('[,.;]', ' ', ass_tmp)
            ass_tmp = ass_tmp.replace(')', ' ')
            ass_tmp = ass_tmp.replace('(', ' ')
            ass_tmp = re.sub('[-_]', ' ', ass_tmp)

            ass_tmp = ass_tmp.lower()
            ass_tmp = ass_tmp.split(' ')

            if usar_exemplos:
                ass_tmp += list(chain(*[self.retornar_valida(ex).split() for ex in lista_exemplos]))

            ass_tmp = [palavra.lower() for palavra in ass_tmp]
            ass_tmp = [p for p in ass_tmp if p != ""]

            assinaturas.append((registro['definicoes'], ass_tmp))

        return assinaturas

    def retornar_valida(self, frase):
        return Utilitarios.retornar_valida(frase)

    def extrair_sinonimos(self, frase, palavra, pos=None, usar_exemplos=False):
        max_sinonimos = 10
        
        resultado = self.adapted_cosine_lesk(frase, palavra, pos, usar_exemplos=usar_exemplos)
        sinonimos = []

        for item in resultado:
            try:
                definicao, pontuacao = item[0], item[1]
            except:
                definicao, pontuacao = item[0][0], item[1]           

            if sinonimos.__len__() < max_sinonimos:
                obj_unificado = self.base_unificada_oxford.obter_obj_unificado(palavra)
                sinonimos_tmp = self.base_unificada_oxford.obter_sinonimos_fonte_obj_unificado(pos, definicao, obj_unificado)

                if not sinonimos_tmp:                    
                    sinonimos_tmp = self.base_unificada_oxford.extrair_sinonimos_candidatos_definicao(definicao, pos)

                for s in [s for s in sinonimos_tmp if Utilitarios.multipalavra(s) == False]:
                    sinonimos.append(s)

        return sinonimos[:max_sinonimos]

    def adapted_cosine_lesk(self, lista_ctx, ambigua, pos, nbest=True, \
        lematizar=True, stem=True, stop=True, usar_ontologia=False, usar_exemplos=False):

        inventario_unificado = self.construir_inventario_unificado(ambigua, pos)

        todas_assinaturas = self.assinaturas_significados(inventario_unificado, usar_ontologia=usar_ontologia, \
        usar_exemplos=usar_exemplos)

        lista_ctx = [p for p in word_tokenize(lista_ctx.lower()) if not p in [',', ';', '.']]        
        lista_ctx = Utilitarios.processar_contexto(lista_ctx, stop=True, lematizar=True, stem=True)

        pontuacao = []

        for a in todas_assinaturas:
            ass_tmp = a[1]
            ass_tmp = Utilitarios.processar_contexto(ass_tmp, stop=True, lematizar=True, stem=True)

            pontuacao.append((cos_sim(" ".join(lista_ctx), " ".join(ass_tmp)), a[0]))

        resultado = [(s, p) for p, s in sorted(pontuacao, reverse=True)]

        return resultado if nbest else [resultado[0]]

    def construir_inventario_unificado(self, palavra, pos, usar_ontologia=True):
        pos = Utilitarios.conversor_pos_wn_oxford(pos)

        inventario = []
        # indexado (def_oxford, synset_name)
        casamentos = self.casador_conceitos.iniciar_casamento(palavra, pos)
        # indexado (synset_name, def_oxford)
        casamentos_invertidos = dict()

        if not casamentos:
            print('Objeto de casamentos e nulo! Abortando a funcao...')
            print('Palavra: %s\tPOS: %s' % (palavra, pos))
            
            return 

        try:
            todas_definicoes_oxford = { pos: self.base_unificada_oxford.obter_obj_unificado(palavra)[pos] }
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
                    registro['hiperonimos'] = []
                else:
                    registro['hiperonimos'] = []

                registro['lemas'] = []

                inventario.append(registro)

        return inventario

    # retira do obj json a estrutura de aninhamento entre definicoes
    def desindentar_coleta_oxford(self, lema, obj_entrada):
        resultado = []
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
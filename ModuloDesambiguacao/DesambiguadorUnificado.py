from CasadorDefinicoes.RepositorioCentralConceitos import CasadorConceitos
from pywsd.utils import lemmatize, porter, lemmatize_sentence
from ModuloUtilitarios.Utilitarios import Utilitarios
from pywsd.cosine import cosine_similarity as cos_sim
from pywsd.lesk_isaias import cosine_lesk
from ModuloOxfordAPI.ModuloClienteOxfordAPI import *
from nltk.corpus import stopwords, wordnet
from nltk import pos_tag, word_tokenize
from nltk.corpus import wordnet
from itertools import chain
import re
from ModuloOxfordAPI.ModuloClienteOxfordAPI import BaseUnificadaObjetosOxford


class DesambiguadorUnificado(object):
    def __init__(self, configs, base_unificada_oxford):
        self.configs = configs
        self.base_unificada_oxford = base_unificada_oxford
        self.casador_conceitos = CasadorConceitos(self.configs, self.base_unificada_oxford)

    def assinatura_significado(self, inventario, pos):
        assinaturas = []

        for registro in inventario:
            ass_tmp = ""

            for e in registro['definicoes']: ass_tmp += ' ' + re.sub('[-_]', ' ', e)
            for e in registro['hiperonimos']:
                ass_tmp += ' ' + re.sub('[_-]', ' ', e.definition())
                ass_tmp + ' '.join(e.lemma_names())

            ass_tmp += ' '.join([re.sub('[_-]', ' ', e) for e in registro['lemas']])

            ass_tmp = re.sub('[,.;]', ' ', ass_tmp)
            ass_tmp = ass_tmp.replace(')', ' ')
            ass_tmp = ass_tmp.replace('(', ' ')

            assinaturas.append((registro['definicoes'], ass_tmp.split(' ')))

        return assinaturas

    def adapted_cosine_lesk(self, frase, ambigua, pos, nbest=True, \
        lematizar=True, stem=True, stop=True, usar_ontologia=False, usar_exemplos=False):

        inventario_unificado = self.construir_inventario_unificado(ambigua, pos)
        assinaturas = self.assinatura_significado(inventario_unificado, pos)

        frase = " ".join(lemmatize_sentence(frase))
        pontuacao = []

        for a in assinaturas:
            ass_tmp = a[1]

            if stop:
                ass_tmp = [i for i in ass_tmp if i not in stopwords.words('english')]
            if lematizar:
                ass_tmp = [lemmatize(i) for i in ass_tmp]
            if stem:
                ass_tmp = [porter.stem(i) for i in ass_tmp]

            pontuacao.append((cos_sim(frase, " ".join(ass_tmp)), a[0]))

        resultado = [(s, p) for p, s in sorted(pontuacao, reverse=True)]

        return resultado if nbest else [resultado[0]]

    def construir_inventario_unificado(self, palavra, pos):
        if pos == 'n': pos = 'Noun'
        elif pos == 'v': pos = 'Verb'
        else: pos = ''

        inventario = []
        # indexado (def_oxford, synset_name)
        casamentos = self.casador_conceitos.iniciar_casamento(palavra, pos)
        # indexado (synset_name, def_oxford)
        casamentos_invertidos = dict()

        todas_definicoes_oxford = {pos: self.base_unificada_oxford.iniciar_consulta(palavra)[pos]}
        todas_definicoes_oxford = self.desindentar_coleta_oxford(palavra, todas_definicoes_oxford)

        for def_oxford in casamentos:
            casamentos_invertidos[casamentos[def_oxford]] = def_oxford

        for synset in wordnet.synsets(palavra, pos[0].lower()):
            registro = {}

            registro['definicoes'] = [synset.definition()]
            registro['fontes'] = ['wordnet']
            registro['exemplos'] = synset.examples()
            registro['hiperonimos'] = synset.hypernyms()
            registro['lemas'] = synset.lemma_names()

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
                registro['fontes'] = ['oxford']
                registro['definicoes'] = [def_oxford]
                registro['exemplos'] = exemplos
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
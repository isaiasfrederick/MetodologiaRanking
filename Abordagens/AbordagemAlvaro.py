# -*- coding: UTF-8 -*-
from nltk.corpus import wordnet
from Utilitarios import Utilitarios
from CasadorManual import CasadorManual
import CasadorManual
import traceback

from pywsd.lesk import cosine_lesk

wn = wordnet

class AbordagemAlvaro(object):
    def __init__(self, configs, base_unificada_oxford, casador_manual):
        self.configs = configs
        self.base_oxford = base_unificada_oxford
        self.casador_manual = casador_manual

    def iniciar_processo(self, palavra, pos, contexto, fontes=['wordnet'], anotar_exemplos=False, usar_fontes_secundarias=False, usar_ctx=False, candidatos=None):
        resultados = list()
        f = fontes

        todas_definicoes_candidatas = []

        if candidatos == None:
            todos_candidatos = self.selecionar_candidatos(palavra, pos, fontes=f)
            todos_candidatos = [p for p in todos_candidatos if p.istitle() == False]
        else:
            todos_candidatos = candidatos

        todos_candidatos = [p for p in todos_candidatos if not Utilitarios.representa_multipalavra(p)]


        if fontes == ['oxford']:
            for candidato in todos_candidatos:
                # obter_obj_unificado(self, candidato):
                pos_oxford = Utilitarios.conversor_pos_wn_oxford(pos)
                obj_oxford = self.base_oxford.obter_obj_unificado(palavra)[pos_oxford]

                for definicao in obj_oxford:
                    todas_definicoes_candidatas.append(definicao)
                    print('### ' + candidato)
                    raw_input('>>> ' + definicao)

        print('\n\nTODOS CANDIDATOS PARA AS FONTES %s: ' % str(fontes).upper())
        raw_input(todos_candidatos)
        print('\n\n')

        for candidato in todos_candidatos:
            for synset_sinonimo in wn.synsets(candidato, pos):
                todas_definicoes_candidatas.append(synset_sinonimo)

        # Retira os significados da palavra
        todas_definicoes_candidatas = list(set(todas_definicoes_candidatas) - set(wn.synsets(palavra, pos)))

        for synset_sinonimo in todas_definicoes_candidatas:
            if anotar_exemplos == True and fontes == ['wordnet']:
                # Solicita a anotacao dos termos para casar as definicoes, caso nao existam
                nome_synset_sinonimo = synset_sinonimo.lemma_names()[0]
                self.casador_manual.iniciar_casamento(nome_synset_sinonimo, synset_sinonimo.pos(), corrigir=False)

            try:
                todos_exemplos = synset_sinonimo.examples()
            except:
                todos_exemplos = []

            try:
                if usar_fontes_secundarias == True:
                    todos_exemplos += self.casador_manual.recuperar_exemplos(synset_sinonimo.name())
            except:
                traceback.print_exc()

            if usar_ctx == True:
                todos_exemplos.append(contexto)

            for exemplo in todos_exemplos:               
                # Cosine Lesk
                resultado = cosine_lesk(exemplo, palavra, pos=pos, nbest=True)

                for registro in resultado:
                    synset, pontuacao = registro

                    reg_tmp = synset_sinonimo.name(), synset.name(), exemplo, pontuacao
                    resultados.append(reg_tmp)

        return resultados
                

    # Seletor candidatos
    def selecionar_candidatos(self, palavra, pos, fontes=['wordnet']):
        candidatos = set()

        if fontes in [[], None]:
            return []

        if 'wordnet' in fontes:
            for s in wn.synsets(palavra, pos):
                candidatos.update(s.lemma_names())

        if 'oxford' in fontes:
            obj_unificado_oxford = self.base_oxford.obter_obj_unificado(palavra)
            todas_definicoes = self.base_oxford.obter_todas_definicoes(obj_unificado_oxford, pos)

            for definicao in todas_definicoes:
                candidatos_tmp = self.base_oxford.obter_sinonimos(pos, definicao, obj_unificado_oxford)
                candidatos.update([] if candidatos_tmp == None else candidatos_tmp)

        return list(candidatos)

    # Seletor de exemplos
    def selecionar_exemplos(self, palavra_sinonimos):
        return []

    # Calculador de peso por definição
    def calcular_peso(self, fontes):
        if fontes != ['wordnet']:
            raise Exception('As fontes utilizadas nao permitem esse tipo de uso da funcao...')

        return 0.00
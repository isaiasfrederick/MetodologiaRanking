# -*- coding: UTF-8 -*-
from nltk.corpus import wordnet
from Utilitarios import Utilitarios
from CasadorManual import CasadorManual
from ModuloDesambiguacao import DesambiguadorOxford
import CasadorManual
import traceback

from pywsd.lesk import cosine_lesk

wn = wordnet

class AbordagemAlvaro(object):
    def __init__(self, configs, base_unificada_oxford, casador_manual):
        self.configs = configs
        self.base_oxford = base_unificada_oxford
        self.casador_manual = casador_manual

    def iniciar_processo(self, palavra, pos, contexto, fontes_arg=['wordnet'], anotar_exemplos=False, usar_fontes_secundarias=False, usar_ctx=False, candidatos=None):
        resultados = list()
        contexto = None

        if set(fontes_arg) in [set(['wordnet', 'oxford']), set(['wordnet'])]:
            raise Exception("Estas duas fontes nao foram implementadas!")

        todas_definicoes_candidatas = []

        if candidatos == None:
            todos_candidatos = self.selecionar_candidatos(palavra, pos, fontes=fontes_arg)
            todos_candidatos = [p for p in todos_candidatos if p.istitle() == False]
        else:
            todos_candidatos = candidatos

        todos_candidatos = [p for p in todos_candidatos if not Utilitarios.representa_multipalavra(p)]

        if fontes_arg == ['oxford']:
            for candidato in todos_candidatos:
                todas_definicoes_candidatas += [(d, candidato) for d in self.base_oxford.obter_todas_definicoes(candidato, pos)]

            definicoes_palavra = [(d, palavra) for d in self.base_oxford.obter_todas_definicoes(palavra, pos)]

            # Retira os significados da palavra
            # (u'The creation of something as part of a physical, biological, or chemical process.', u'production')
            todas_definicoes_candidatas = list(set(todas_definicoes_candidatas) - set(definicoes_palavra))

        elif fontes_arg == ['wordnet']:
            for candidato in todos_candidatos:
                for definicao_candidata in wn.synsets(candidato, pos):
                    todas_definicoes_candidatas.append((definicao_candidata, candidato))

            definicoes_palavra = [(s, palavra) for s in wn.synsets(palavra, pos)]
            # Retira os significados da palavra
            todas_definicoes_candidatas = list(set(todas_definicoes_candidatas) - set(definicoes_palavra))

        else:
            raise Exception("Esta configuracao nao existe!")

        # Todas definicoes candidatas:
        # (u'The creation of something as part of a physical, biological, or chemical process.', u'production')
        for definicao_candidata in todas_definicoes_candidatas:
            if anotar_exemplos == True and fontes_arg == ['wordnet']:
                synset, lema = definicao_candidata
                # Solicita a anotacao dos termos para casar as definicoes, caso nao existam
                nome_synset_sinonimo = synset.lemma_names()[0]
                self.casador_manual.iniciar_casamento(nome_synset_sinonimo, synset.pos(), corrigir=False)

            todos_exemplos = []

            try:
                if fontes_arg == ['wordnet']:                    
                    def_candidata, lema = definicao_candidata
                    todos_exemplos = def_candidata.examples()
                elif fontes_arg == ['oxford']:
                    def_candidata, lema = definicao_candidata
                    todos_exemplos = self.base_oxford.obter_atributo(lema, pos, def_candidata, 'exemplos')
                else:
                    todos_exemplos = []

            except:
                import traceback
                traceback.print_exc()
                todos_exemplos = []

            try:
                if usar_fontes_secundarias == True:
                    if fontes_arg == ['wordnet']:
                        synset, lema = definicao_candidata
                        todos_exemplos += self.casador_manual.recuperar_exemplos(synset.name())
            except:
                traceback.print_exc()

            if usar_ctx == True:
                todos_exemplos.append(contexto)

            for exemplo in todos_exemplos:               
                # Cosine Lesk
                if fontes_arg == ['wordnet']:
                    resultado_desambiguador = cosine_lesk(exemplo, palavra, pos=pos, nbest=True)
                elif fontes_arg == ['oxford']:
                    desambiguador_oxford = DesambiguadorOxford.DesambiguadorOxford(self.configs, self.base_oxford)
                    resultado_desambiguador = desambiguador_oxford.cosine_lesk(exemplo, palavra, pos=pos)
                else:
                    resultado_desambiguador = []

                for registro in resultado_desambiguador:
                    synset, pontuacao = registro

                    if fontes_arg == ['wordnet']:
                        reg_ponderacao = definicao_candidata[0].name(), synset.name(), exemplo, pontuacao
                    elif fontes_arg == ['oxford']:
                        reg_ponderacao = ";".join(definicao_candidata), ";".join(synset[0:2][::-1]), exemplo, pontuacao
                        
                    resultados.append(reg_ponderacao)

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
            todas_definicoes = self.base_oxford.obter_todas_definicoes(palavra, pos)

            for definicao in todas_definicoes:
                candidatos_tmp = self.base_oxford.obter_sinonimos(palavra, definicao, pos)
                candidatos.update([] if candidatos_tmp == None else candidatos_tmp)

        return list(candidatos)
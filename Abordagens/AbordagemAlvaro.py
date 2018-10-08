# -*- coding: UTF-8 -*-
from ModuloDesambiguacao.DesambiguadorOxford import DesambiguadorOxford
from CasadorManual import CasadorManual
from Utilitarios import Utils
from nltk.corpus import wordnet
import CasadorManual
import traceback

from pywsd.lesk import cosine_lesk

wn = wordnet

class AbordagemAlvaro(object):
    def __init__(self, configs, base_ox, casador_manual):
        self.configs = configs
        self.base_oxford = base_ox
        self.casador_manual = casador_manual

    # def iniciar(self, palavra, pos, contexto, fontes_arg=['wordnet'],\
    # anotar_exemplos=False, usar_fontes_secundarias=False, usar_ctx=False, candidatos=None):
    def construir_relacao(self, palavra, pos, contexto, fontes_def='oxford', fontes_cands=['oxford', 'wordnet'], an_exemplos=False, fts_secs=False, usar_ctx=False, cands=None):
        resultados = list()
        contexto = None

        if type(fontes_def) != str:
            raise Exception("O tipo deste argumento deve ser string!")

        if cands == None:
            cands = self.selecionar_candidatos(palavra, pos, fontes=fontes_cands)
            cands = [p for p in cands if p.istitle() == False]
            raw_input("TODOS CANDIDATOS (%d): %s" % (len(cands), str(cands)))

        cands = [p for p in cands if not Utils.e_multipalavra(p)]
        todas_definicoes_candidatas = []

        if fontes_def == 'oxford':
            for candidato in cands:
                todas_definicoes_candidatas += [(d, candidato) for d in self.base_oxford.obter_todas_definicoes(candidato, pos)]
            definicoes_palavra = [(d, palavra) for d in self.base_oxford.obter_todas_definicoes(palavra, pos)]

        elif fontes_def == 'wordnet':
            for candidato in cands:
                for definicao_candidata in wn.synsets(candidato, pos):
                    todas_definicoes_candidatas.append((definicao_candidata, candidato))
            definicoes_palavra = [(d, palavra) for d in wn.synsets(palavra, pos)]

        # Retira os significados da palavra
        # (u'The creation of something as part of a physical, biological, or chemical process.', u'production')
        todas_definicoes_candidatas = list(set(todas_definicoes_candidatas) - set(definicoes_palavra))

        # Todas definicoes candidatas:
        # (u'The creation of something as part of a physical, biological, or chemical process.', u'production')
        for definicao_candidata in todas_definicoes_candidatas:
            if an_exemplos == True and fontes_def == ['wordnet'] and False:
                definicao, lema = definicao_candidata
                # Solicita a anotacao dos termos para casar as definicoes, caso nao existam
                nome_synset_sinonimo = definicao.lemma_names()[0]
                self.casador_manual.iniciar_casamento(nome_synset_sinonimo, definicao.pos(), corrigir=False)

            todos_exemplos = []

            try:
                # definicao_candidata é uma tupla no formato (definicao, palavra)
                def_candidata, lema = definicao_candidata
                if fontes_def == 'wordnet':
                    todos_exemplos = def_candidata.examples()
                elif fontes_def == 'oxford':
                    todos_exemplos = self.base_oxford.obter_atributo(lema, pos, def_candidata, 'exemplos')
            except:
                todos_exemplos = []

            try:
                if fts_secs == True:
                    if fontes_def == ['wordnet']:
                        definicao, lema = definicao_candidata
                        todos_exemplos += self.casador_manual.recuperar_exemplos(definicao.name())
            except:
                traceback.print_exc()

            # Usar contexto na estapa de discriminação (desambiguação)
            if usar_ctx == True:
                todos_exemplos.append(contexto)

            for exemplo in todos_exemplos:
                if fontes_def == 'wordnet':
                    resultado_desambiguador = []
                    try:
                        resultado_desambiguador = cosine_lesk(exemplo, palavra, pos=pos, nbest=True)
                    except KeyboardInterrupt, ke:
                        raw_input("\t\t@@@ " + str((exemplo, palavra, pos)) + "")
                elif fontes_def == 'oxford':
                    desambiguador_oxford = DesambiguadorOxford(self.configs, self.base_oxford)
                    resultado_desambiguador = desambiguador_oxford.cosine_lesk(exemplo, palavra, pos=pos)

                for registro in resultado_desambiguador:
                    # definicao = synset ou definica = (definicao, palavra)
                    definicao, pontuacao = registro

                    if fontes_def == 'wordnet':
                        reg_ponderacao = definicao_candidata[0].name(), definicao.name(), exemplo, pontuacao
                    elif fontes_def == 'oxford':
                        # (def, lema), (def, lema), exemplo, score
                        reg_ponderacao = ";".join(definicao_candidata), ";".join(definicao[0:2][::-1]), exemplo, pontuacao
                        
                    resultados.append(reg_ponderacao)

        # Retornando ordenado
        return sorted(resultados, key=lambda x: x[3], reverse=True)

    # Gabarito no formato [[palavra, voto], ...]
    def possui_moda(self, gabarito):
        todos_votos = sorted([v[1] for v in gabarito], reverse=True)
        # Se caso de entrada possui uma moda
        return todos_votos.count(todos_votos[0]) != 1

    # Seletor candidatos desconsiderando a questao da polissemia sob este aspecto
    # este metodo seleciona todos os candidatos 
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

        if 'wordembbedings' in fontes:
            pass

        return list(candidatos)
# -*- coding: UTF-8 -*-
from ModuloDesambiguacao.DesambiguadorOxford import DesOx
from CasadorManual import CasadorManual
from Utilitarios import Util
from nltk.corpus import wordnet
import CasadorManual
import traceback
import sys

from pywsd.lesk import cosine_lesk

wn = wordnet

class AbordagemAlvaro(object):
    def __init__(self, configs, base_ox, casador_manual):
        self.cfgs = configs
        self.base_ox = base_ox
        self.casador_manual = casador_manual

    # CONSTRUIR RELACAO ENTRE AS DEFINICOES
    # def iniciar(self, palavra, pos, contexto, fontes_arg=['wordnet'],\
    # anotar_exemplos=False, usar_fontes_secundarias=False, usar_ctx=False, candidatos=None):
    # max_en = maximo de exemplos utilizaveis
    def iniciar(self, palavra, pos, ctx, src_def='oxford', src_cands=['oxford', 'wordnet'], an_exemplos=False, src_secs=False, usar_ctx=False, cands=None, max_ex=sys.maxint):
        nome_arquivo_cache = "%s-%s.json" % (palavra, pos)
        dir_cache = self.cfgs['aplicacao']['dir_cache_relacao_sinonimia']
        arqs_cache = Util.list_arqs(dir_cache, caminho_completo=False)

        if nome_arquivo_cache in arqs_cache:
            resultados = Util.abrir_json(dir_cache+"/"+nome_arquivo_cache)
            if resultados == { }:
                resultados = [ ]
        else:
            resultados = list()

        if type(src_def) != str:
            raise Exception("O tipo deste argumento deve ser string!")

        # Todas definicoes candidatas
        todas_defs_cands = [ ]

        if src_def == 'oxford':
            for candidato in cands:
                todas_defs_cands += [(candidato, d) for d in self.base_ox.obter_definicoes(candidato, pos)]
            definicoes_palavra = [(palavra, d) for d in self.base_ox.obter_definicoes(palavra, pos)]
        elif src_def == 'wordnet':
            for candidato in cands:
                for def_candidata in wn.synsets(candidato, pos):
                    todas_defs_cands.append((candidato, def_candidata))
            definicoes_palavra = [(palavra, d) for d in wn.synsets(palavra, pos)]

        # Retira os significados da palavra passada como argumento
        # (u'The creation of something as part of a physical, biological, or chemical process.', u'production')
        todas_defs_cands = set(set(todas_defs_cands) - set(definicoes_palavra))
        todas_defs_cands = list(todas_defs_cands)

        # Conjunto uniao exemplos de TODAS definicoes candidatas
        conj_uniao_exemplos = [ ]

        # Todas definicoes candidatas:
        # (u'The creation of something as part of a physical, biological, or chemical process.', u'production')
        for def_candidata in todas_defs_cands:
            if an_exemplos == True and src_def == ['wordnet'] and False:
                lema, definicao = def_candidata
                # Solicita a anotacao dos termos para casar as definicoes, caso nao existam
                nome_synset_sinonimo = definicao.lemma_names()[0]
                self.casador_manual.iniciar_casamento(nome_synset_sinonimo, definicao.pos(), corrigir=False)

            exs_definicao_cand = [ ]

            try:
                # definicao_candidata é uma tupla no formato (palavra, definicao)
                lema_cand, def_cand = def_candidata
                if src_def == 'wordnet':
                    exs_definicao_cand = def_candidata.examples()
                elif src_def == 'oxford':
                    exs_definicao_cand = self.base_ox.obter_atributo(lema_cand, pos, def_cand, 'exemplos')
            except:
                pass

            if not exs_definicao_cand: exs_definicao_cand = [ ]
            exs_definicao_cand = exs_definicao_cand[:max_ex]
            conj_uniao_exemplos += exs_definicao_cand

            try:
                if src_secs == True:
                    if src_def == ['wordnet']:
                        lema, definicao = def_candidata
                        exs_definicao_cand += self.casador_manual.recuperar_exemplos(definicao.name())
            except:
                traceback.print_exc()

            # Usar contexto na estapa de discriminação (desambiguação)
            if usar_ctx == True:
                exs_definicao_cand.append(ctx)

            if exs_definicao_cand == None:
                exs_definicao_cand = [ ]

            # Resolvedor de colisao para checar se casos de
            # entrada, que sao as frases, ja estao contidos no cache
            set_cache_frases = set([reg[2] for reg in resultados])

            # Laço so processa frases de exemplos ainda nao contidas no cache
            for exemplo in set(exs_definicao_cand) - set_cache_frases:
                if src_def == 'wordnet':
                    resultado_desambiguador = [ ]
                    try:
                        resultado_desambiguador = cosine_lesk(exemplo, palavra, pos=pos, nbest=True)
                    except KeyboardInterrupt, ke:
                        raw_input("\t\t@@@ " + str((exemplo, palavra, pos)) + "")

                elif src_def == 'oxford':
                    desambiguador_ox = DesOx(self.cfgs, self.base_ox)
                    resultado_desambiguador = desambiguador_ox.cosine_lesk(exemplo, palavra, pos=pos)

                for registro in resultado_desambiguador:
                    # definicao = synset ou definica = (definicao, palavra)
                    definicao, pontuacao = registro

                    if src_def == 'wordnet':
                        reg_ponderacao = def_candidata[0].name(), definicao.name(), exemplo, pontuacao
                    elif src_def == 'oxford':
                        # self.base_ox.obter_atributo(lema, pos, def_candidata, 'exemplos')                        
                        # (def, lema), (def, lema), exemplo, score
                        # ('def;lema', 'def;lema', 'exemplo', 0.00)
                        reg_ponderacao = ";".join(def_candidata[::-1]), ";".join(definicao[:2][::-1]), exemplo, pontuacao
                        
                    resultados.append(reg_ponderacao)

        # Retornando ordenado PELA PONTUACAO
        # ('def;lema', 'def;lema', 'exemplo', 0.00)
        obj_retorno = sorted(resultados, key=lambda x: x[3], reverse=True)
        Util.salvar_json(dir_cache+"/"+nome_arquivo_cache, obj_retorno)

        # (def_sin, def_des, ex, pontuacao)
        return [reg for reg in obj_retorno if reg[2] in conj_uniao_exemplos]

    # Gabarito no formato [[palavra, voto], ...]
    def possui_moda(self, gabarito):
        todos_votos = sorted([v[1] for v in gabarito], reverse=True)
        # Se caso de entrada possui uma moda
        return todos_votos.count(todos_votos[0]) != 1

    # Seletor candidatos desconsiderando a questao da polissemia sob este aspecto
    # este metodo seleciona todos os candidatos 
    def selecionar_candidatos(self, palavra, pos, fontes=['wordnet']):
        candidatos = set()

        if fontes in [[ ], None]:
            return [ ]

        if 'wordnet' in fontes:
            for s in wn.synsets(palavra, pos):
                candidatos.update(s.lemma_names())

        if 'oxford' in fontes:
            todas_definicoes = self.base_ox.obter_definicoes(palavra, pos)

            for definicao in todas_definicoes:
                candidatos_tmp = self.base_ox.obter_sins(palavra, definicao, pos)
                candidatos.update([ ] if candidatos_tmp == None else candidatos_tmp)

        if 'wordembbedings' in fontes:
            pass

        return list(candidatos)
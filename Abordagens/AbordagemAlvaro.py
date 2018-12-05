# -*- coding: UTF-8 -*-
from ModuloDesambiguacao.DesambiguadorOxford import DesOx
from ModuloDesambiguacao.DesambiguadorWordnet import DesWordnet
from CasadorManual import CasadorManual
from Utilitarios import Util
from nltk.corpus import wordnet
import CasadorManual
import traceback
import sys

from pywsd.lesk import cosine_lesk

wn = wordnet

class AbordagemAlvaro(object):
    def __init__(self, configs, base_ox, casador_manual, rep_vetorial):
        self.cfgs = configs
        self.base_ox = base_ox
        self.casador_manual = casador_manual
        self.rep_vetorial = rep_vetorial

    # CONSTRUIR RELACAO ENTRE AS DEFINICOES
    # def iniciar(self, palavra, pos, contexto, fontes_arg=['wordnet'],\
    # anotar_exemplos=False, usar_fontes_secundarias=False, usar_ctx=False, candidatos=None):
    # max_en = maximo de exemplos utilizaveis
    def construir_sinonimia(self, palavra, pos, ctx,\
                    fontes_def='oxford', fontes_cands=['oxford', 'wordnet'],\
                    an_exemplos=False, fts_secs=False, usar_ctx=False, cands=None,\
                    max_ex=sys.maxint, usr_ex=False, med_sim='cosine'):

        """nome_arquivo_cache = "%s-%s.json" % (palavra, pos)
        dir_cache = self.cfgs['aplicacao']['dir_cache_relacao_sinonimia']
        arqs_cache = Util.list_arqs(dir_cache, caminho_completo=False)

        if nome_arquivo_cache in arqs_cache:
            raw_input("$$$\t"+dir_cache+"/"+nome_arquivo_cache)
            obj = Util.abrir_json(dir_cache+"/"+nome_arquivo_cache)"""
        
        resultados = list()
        # Todas definicoes candidatas
        todas_defs_cands = [ ]

        if fontes_def == 'oxford':
            for candidato in cands:
                todas_defs_cands += [(candidato, d) for d in self.base_ox.obter_definicoes(candidato, pos)]
            definicoes_palavra = [(palavra, d) for d in self.base_ox.obter_definicoes(palavra, pos)]
        elif fontes_def == 'wordnet':
            for candidato in cands:
                for synset in wn.synsets(candidato, pos):
                    todas_defs_cands.append((candidato, synset))
            definicoes_palavra = [(palavra, synset) for synset in wn.synsets(palavra, pos)]

        # Retira os significados da palavra passada como argumento
        # (u'The creation of something as part of a physical, biological, or chemical process.', u'production')
        todas_defs_cands = list(set(set(todas_defs_cands) - set(definicoes_palavra)))

        total_exemplos_computados = 0
        # Todas definicoes candidatas:
        # (u'The creation of something as part of a physical, biological, or chemical process.', u'production')
        for reg_def_cand in todas_defs_cands:
            #if an_exemplos == True and fontes_def == ['wordnet'] and False:
                #lema, def_des = reg_def_cand
                # Solicita a anotacao dos termos para casar as definicoes, caso nao existam
                #nome_synset_sinonimo = def_des.lemma_names()[0]
                #self.casador_manual.iniciar_casamento(nome_synset_sinonimo, def_des.pos(), corrigir=False)
            todos_exemplos = [ ]

            try:
                # definicao_candidata é uma tupla no formato (palavra, definicao)
                if fontes_def == 'wordnet':
                    lema_cand, synset = reg_def_cand
                    todos_exemplos = synset.examples()
                elif fontes_def == 'oxford':
                    lema_cand, def_cand = reg_def_cand
                    todos_exemplos = self.base_ox.obter_atributo(lema_cand, pos, def_cand, 'exemplos')
            except Exception, e:
                #raw_input(e)
                todos_exemplos = [ ]
                
            if None == todos_exemplos:
                todos_exemplos = [ ]

            todos_exemplos = todos_exemplos[:max_ex]

            # Usar contexto na estapa de discriminação (desambiguação)
            if usar_ctx == True:                
                todos_exemplos.append(ctx)
            if todos_exemplos == None:
                todos_exemplos = [ ]

            total_exemplos_computados+=len(todos_exemplos)

            for exemplo in todos_exemplos:
                if fontes_def == 'wordnet':
                    res_desambiguador = [ ]
                    try:
                        des_wn = DesWordnet(self.cfgs)
                        res_desambiguador = des_wn.cosine_lesk(exemplo, palavra, pos=pos, nbest=True, convert=False)
                    except KeyboardInterrupt, ke:
                        raw_input("\t\t@@@ ERRO " + str((exemplo, palavra, pos)) + "")

                elif fontes_def == 'oxford':
                    des_ox = DesOx(self.cfgs, self.base_ox, self.rep_vetorial)
                    res_desambiguador = des_ox.desambiguar(exemplo,\
                                        palavra, pos=pos, usr_ex=usr_ex,\
                                        med_sim=med_sim)

                for reg_def_des in res_desambiguador:
                    def_des, pontuacao = reg_def_des
                    if fontes_def == 'wordnet':
                        # ('def;lema', 'def;lema', 'exemplo', 0.00)
                        label_tuple = reg_def_cand[1].name()+";"+reg_def_cand[0], def_des.name()+";"+palavra
                        reg_ponderacao = label_tuple + (exemplo, pontuacao) # Concatenacao
                    elif fontes_def == 'oxford':
                        # self.base_ox.obter_atributo(lema, pos, def_candidata, 'exemplos')                        
                        # (def, lema), (def, lema), exemplo, score
                        # ('def;lema', 'def;lema', 'exemplo', 0.00)
                        reg_ponderacao = ";".join(reg_def_cand[::-1]), ";".join(def_des[:2][::-1]), exemplo, pontuacao

                    resultados.append(reg_ponderacao)

        if not total_exemplos_computados:
            Util.print_formatado("\nA entrada %s nao possui NENHUM exemplo!\n" % str((palavra, pos, ctx)))
            Util.print_formatado("\nTodas defs candidatas: "+str(todas_defs_cands))

        # Retornando ordenado PELA PONTUACAO
        # ('def;lema', 'def;lema', 'exemplo', 0.00)
        obj_retorno = sorted(resultados, key=lambda x: x[3], reverse=True)
        #Util.salvar_json(dir_cache + "/" + nome_arquivo_cache, obj_retorno)

        return obj_retorno


    # Obtem a palavra mais usual para o significado mais usual para uma palavra
    def sugestao_contingencia(self, palavra, pos, fontes_def='oxford'):
        if fontes_def == 'wordnet':
            for syn in wn.synsets(palavra, pos):
                for lema in syn.lemma_names():
                    if not Util.e_multipalavra(lema) and lema != palavra:
                        return [lema]
        elif fontes_def == 'oxford':
            pos_ox = Util.cvsr_pos_semeval_ox(pos)

            try:
                for def_ox in self.base_ox.obter_definicoes(palavra, pos_ox):
                    for lema in self.base_ox.obter_atributo(palavra, pos_ox, def_ox, 'sinonimos'):
                        if not Util.e_multipalavra(lema) and lema!=palavra:
                            return [lema]
            except Exception, e:
                pass

        return [""]
            
    # Gabarito no formato [[palavra, voto], ...]
    def possui_moda(self, gabarito):
        todos_votos = sorted([v[1] for v in gabarito], reverse=True)
        return todos_votos.count(todos_votos[0])!=1

    # Seletor candidatos desconsiderando a questao da polissemia sob este aspecto
    # este metodo seleciona todos os candidatos 
    def selec_candidatos(self, palavra, pos, fontes=['wordnet'], max_por_def=4):
        candidatos = set()

        if fontes in [[ ], None]:
            raise Exception("Fontes nao foram informadas!")

        if 'wordnet' in fontes:
            for s in wn.synsets(palavra, pos):
                candidatos.update(s.lemma_names()[:max_por_def])
        if 'oxford' in fontes:
            todas_definicoes = self.base_ox.obter_definicoes(palavra, pos)
            for definicao in todas_definicoes:
                candidatos_tmp = self.base_ox.obter_sins(palavra, definicao, pos)[:max_por_def]
                candidatos.update([ ] if candidatos_tmp == None else candidatos_tmp)
        if 'wordembbedings' in fontes:
            pass

        return list(candidatos)
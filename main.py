#! coding: utf-8
import gc
import itertools
import json
import os
import re
import signal
import statistics
import sys
import traceback
from operator import itemgetter
from statistics import mean as media
from sys import argv

import nltk
from nltk.corpus import wordnet
from textblob import TextBlob

# Testar Abordagem Alvaro
from Alvaro import Alvaro
from CasadorManual import CasadorManual
# Experimentacao
from DesambiguadorWordnet import DesWordnet
from DesOx import DesOx
from ExtratorWikipedia import ExtratorWikipedia
from Indexador import Whoosh
from InterfaceBases import InterfaceBases
from OxAPI import BaseOx, CliOxAPI, ExtWeb
from RepresentacaoVetorial import RepVetorial
from SemEval2007 import VlddrSemEval
from Utilitarios import Util

# Fim pacotes da Experimentacao
wn = wordnet


def exibir_bases(cfgs, fonte='wordnet', tipo='test', td_pos=['a', 'n', 'r', 'v']):
    validador = VlddrSemEval(cfgs)
    des_wn = DesWordnet(cfgs)

    casos_testes_dict, gabarito_dict = carregar_bases(cfgs, tipo)
    palavras = set()

    alvaro = Alvaro.INSTANCE

    for lexelt in set(casos_testes_dict.keys()) & set(gabarito_dict.keys()):
        p = lexelt.split(".")[0]
        palavras.add(p)

    for lexelt in [l for l in set(casos_testes_dict.keys()) & set(gabarito_dict.keys()) if casos_testes_dict[l][2] in td_pos]:
        frase, palavra, pos = casos_testes_dict[lexelt]
        frase = Util.descontrair(frase).replace("  ", " ")
        palavra = lexelt.split(".")[0]

        if palavra in palavras:
            if not 'HEROES' in frase:
                nfrase = str(frase).replace(palavra, "(%s)" % palavra)
                nfrase = frase
                Util.verbose_ativado = True
                Util.print_formatado("%s" % frase)
                Util.print_formatado("Palavra: "+palavra)
                Util.print_formatado("POS: "+pos)
                Util.print_formatado("Resposta: " +
                                     str(validador.fltr_gabarito(gabarito_dict[lexelt])))
                cands = alvaro.selec_candidatos(
                    palavra, pos, fontes=['wordnet', 'oxford'])
                print("Candidatos: " + str(cands['uniao']))
                print("\n\n")


def carregar_bases(cfgs, tipo_base, pos_avaliadas=None):
    from SemEval2007 import VlddrSemEval
    return VlddrSemEval.carregar_bases(VlddrSemEval.INSTANCE,
                                       cfgs, tipo_base, pos_avaliadas=pos_avaliadas)


# Este metodo usa a abordagem do Alvaro sobre as bases do SemEval
# Ela constroi uma relacao (score) entre diferentes definicoes, possivelmente sinonimos
#   criterio = frequencia OU alvaro OU embbedings
def predizer_sins(
    cfgs,
    criterio='frequencia',
    usar_gabarito=False,
    lexelts_filtrados=None,
    fontes_def='oxford', tipo=None,
    max_ex=-1, usr_ex=False,
    pos_avaliadas=None,
    rep_vetorial=None,
    carregar_candidatos_disco=False
):

    verbose_geral = cfgs['verbose']['geral']
    #dir_obj_candidatos = cfgs['caminho_bases']+'/'+cfgs['arquivo_candidatos']
    separador = cfgs['separador']
    med_sim = cfgs['medida_similaridade']
    saida_contigencial = cfgs['saida_contig']['habilitar']

    #obj_candidatos = Util.abrir_json(dir_obj_candidatos, criar=True)

    if fontes_def != 'oxford':
        raise Exception("Esta fonte de definicoes nao é contem exemplos...")

    if pos_avaliadas in [None, []]:
        pos_avaliadas = cfgs['semeval2007']['todas_pos']
    if type(pos_avaliadas) != list:
        raise Exception("\n\nAs POS avaliadas devem ser uma list!\n\n")

    # Construtor com carregador de modelo
    dir_modelo = "%s/%s" % (cfgs['caminho_bases'], cfgs['modelos']['default'])
    rep_vet = RepVetorial.INSTANCE

    casador_manual = None
    base_ox = BaseOx.INSTANCE
    alvaro = Alvaro.INSTANCE

    des_ox = DesOx(cfgs, base_ox, rep_vetorial=rep_vetorial)
    des_wn = DesWordnet(cfgs)

    if max_ex == -1:
        max_ex = sys.maxint

    todos_cands = {}

    # Resultado de saida <lexelt : lista>
    predicao_final = dict()

    # Fonte para selecionar as definicoes e fonte para selecionar os candidatos
    # fontes_def, fontes_cands = raw_input("Digite a fonte para definicoes: "), ['oxford', 'wordnet']
    fontes_def, fontes_cands = fontes_def, cfgs['fontes_cands']
    casos_testes_dict, gabarito_dict = carregar_bases(
        cfgs, tipo, pos_avaliadas=pos_avaliadas)

    if lexelts_filtrados in [None, []]:
        casos_testes_dict_tmp = list(casos_testes_dict.keys())
    else:
        casos_testes_dict_tmp = set(
            casos_testes_dict.keys()) & set(lexelts_filtrados)
        casos_testes_dict_tmp = list(casos_testes_dict_tmp)

    vldr_se = VlddrSemEval(cfgs)
    todos_lexelts = list(set(casos_testes_dict_tmp)
                         & set(gabarito_dict.keys()))
    indices_lexelts = [i for i in range(len(todos_lexelts))]

    palavras_invalidas = []

    cache_rel_sinonimia = dict()
    cache_seletor_candidatos = dict()
    cache_resultado_desambiguador = dict()

    usar_frases_wikipedia = cfgs['wikipedia']['usar_frases']

    if Util.CONFIGS['ngram']['usar_seletor'] == False:
        Alvaro.NGRAMS_SIGNALMEDIA = {}
        Alvaro.NGRAMS_LEIPZIG = {}
        Alvaro.NGRAMS_COCA = {}
    else:

        if "coca" in Util.CONFIGS['ngram']['fontes']:
            print("\nCarregando n-grams COCA Corpus!")
            Alvaro.NGRAMS_COCA = Util.abrir_json(cfgs['dir_coca_ngrams'])
            print("n-grams COCA Corpus carregado!")

        if "signalmedia" in Util.CONFIGS['ngram']['fontes']:
            # Abrindo ngrams SignalMedia
            arq_ngrams_tmp = {}

            with open(Util.CONFIGS['ngram']['signalmedia_5grams'], 'r') as todas_linhas:
                print("\nCarregando n-grams SignalMedia Corpus!")

                for linha_ngram in todas_linhas:
                    try:
                        tokens = linha_ngram.split(":")
                        freq_ngram = int(tokens[-1])
                        ngram = str(
                            ":".join(tokens[:-1])).strip('\t').replace("\t", " ")
                        Alvaro.NGRAMS_SIGNALMEDIA[ngram] = freq_ngram
                    except:
                        pass

                print("\nn-grams SignalMedia Corpus carregado!")

            print("\nDerivando n-grams SignalMedia Corpus!")

            ngrams_signalmedia_derivados = \
                Alvaro.derivar_ngrams_string(Alvaro.NGRAMS_SIGNALMEDIA,
                                             cfgs['ngram']['min'],
                                             cfgs['ngram']['max'])
            for ng in ngrams_signalmedia_derivados:
                Alvaro.NGRAMS_SIGNALMEDIA[ng] = ngrams_signalmedia_derivados[ng]

            print("n-grams SignalMedia Corpus derivado!")

            ngrams_signalmedia_derivados = None

    dir_palavras_indexadas = Util.CONFIGS['corpora']['dir_palavras_indexadas_exemplos']
    Alvaro.PALAVRAS_EXEMPLOS_INDEXADOS = set(
        Util.abrir_json(dir_palavras_indexadas, criarsenaoexiste=True))

    obj_candidatos = { }
    total_acertos = 0

    qtde_sugestoes_oot = Util.CONFIGS['params_exps']['qtde_sugestoes_oot'][0]
    qtde_sugestoes_oot = 200

    contador = 0

    for cont in indices_lexelts:
        lexelt = todos_lexelts[cont]
        frase, palavra, pos = casos_testes_dict[lexelt]
        frase = Util.descontrair(frase).replace("  ", " ")
        palavra = lexelt.split(".")[0]

        exemplos_ponderado = []

        if not palavra in palavras_invalidas:
            chave_seletor_candidatos = str((palavra, pos))
            interseccao_casos = list(
                set(casos_testes_dict_tmp) & set(gabarito_dict.keys()))
            gab_ordenado = Util.sort(gabarito_dict[lexelt], 1, reverse=True)

            print("\n\n\n\n\n\n")
            print("@@@ Processando a entrada " + str(lexelt))
            print("%d / %d" % (cont+1, len(interseccao_casos)))
            print("*** %s\n" % str((frase, palavra, pos)))
            print("Gabarito: %s" % str(gab_ordenado))

            if usar_gabarito == True:
                if cfgs['gabarito']['tipo'] == 'default':
                    cands = [e[0] for e in gabarito_dict[lexelt]
                             if not Util.e_mpalavra(e[0])]
                elif cfgs['gabarito']['tipo'] == 'gap':
                    cands = []
                    for l in casos_testes_dict:
                        try:
                            frasetmp, palavratmp, postmp = casos_testes_dict[l]
                            if palavratmp == palavra:
                                cands += [p1 for p1, p2 in gabarito_dict[l]]
                        except:
                            pass
                    cands = list(set(cands))
                    cands = [e[0] for e in cands if not Util.e_mpalavra(e[0])]

                top_unigrams = [(p, BaseOx.freq_modelo(
                    BaseOx.INSTANCE, p)) for p in cands]
                top_ngrams = list(top_unigrams)
                cands_brutos = list(top_unigrams)

            else:

                dir_obj_candidatos = "../Bases/Candidatos/%s.json" % lexelt

                # if carregar_candidatos_disco == False or Util.arq_existe(None, dir_obj_candidatos) == False:
                if True:
                    tripla_cands = alvaro.selec_candidatos(
                        palavra, pos, fontes=fontes_cands)

                    cands = tripla_cands['uniao']
                    cands_best = tripla_cands['best']
                    cands_oot = tripla_cands['oot']

                    todos_cands[lexelt] = tripla_cands

                    if usar_frases_wikipedia == True:
                        for cand_iter in cands:
                            wikipedia_arq = cfgs['wikipedia']['dir_generico'] % cand_iter
                            if not Util.arq_existe(None, wikipedia_arq):
                                frases_wikipedia = ExtratorWikipedia.obter_frases_exemplo(
                                    cand_iter)

                                dict_frases_wikipedia = {}

                                for reg_wkpd in frases_wikipedia:
                                    palavra_wkpd, def_wkpd, url_wkpd, frase_wkpd = reg_wkpd
                                    if not palavra_wkpd in dict_frases_wikipedia:
                                        dict_frases_wikipedia[palavra_wkpd] = {
                                        }
                                    if not def_wkpd in dict_frases_wikipedia[palavra_wkpd]:
                                        dict_frases_wikipedia[palavra_wkpd][def_wkpd] = [
                                        ]
                                    dict_frases_wikipedia[palavra_wkpd][def_wkpd].append(
                                        (url_wkpd, frase_wkpd))

                                Util.salvar_json(
                                    wikipedia_arq, dict_frases_wikipedia)
                                print(
                                    "\nObjeto frases Wikipedia para a palavra '%s' foi salvo!\n" % cand_iter)

                            else:
                                print(
                                    "\nArquivo Wikipedia %s.json existe!\n" % cand_iter)
                                frases_wikipedia = Util.abrir_json(
                                    wikipedia_arq)
                                dict_frases_wikipedia = {}

                                if type(frases_wikipedia) != dict:
                                    for reg_wkpd in frases_wikipedia:
                                        palavra_wkpd, def_wkpd, url_wkpd, frase_wkpd = reg_wkpd
                                        if not palavra_wkpd in dict_frases_wikipedia:
                                            dict_frases_wikipedia[palavra_wkpd] = {
                                            }
                                        if not def_wkpd in dict_frases_wikipedia[palavra_wkpd]:
                                            dict_frases_wikipedia[palavra_wkpd][def_wkpd] = [
                                            ]
                                        dict_frases_wikipedia[palavra_wkpd][def_wkpd].append(
                                            (url_wkpd, frase_wkpd))

                            for palavra_wkpd in dict_frases_wikipedia:
                                try:
                                    defs_ox = BaseOx.obter_definicoes(
                                        BaseOx.INSTANCE, palavra, pos=pos)
                                except:
                                    defs_ox = []

                                for def_wkpd in dict_frases_wikipedia[palavra_wkpd]:
                                    for do in defs_ox:
                                        wmd = RepVetorial.word_move_distance(
                                            RepVetorial.INSTANCE, do, def_wkpd)
                                        registros = (
                                            palavra_wkpd, def_wkpd, do, wmd)

                    # Removendo palavra
                    if palavra in cands:
                        cands.remove(palavra)

                    cands_brutos = list(cands)

                    top_unigrams = [(p, BaseOx.freq_modelo(
                        BaseOx.INSTANCE, p)) for p in cands]
                    top_unigrams = [registros for registros in sorted(
                        top_unigrams, key=lambda x: x[1], reverse=True) if registros[1] > 0]

                    if cfgs['ngram']['usar_seletor'] == True:
                        top_unigrams_tmp = [p for (p, s) in top_unigrams]
                        top_ngrams = Alvaro.selec_ngrams(
                            Alvaro.INSTANCE, palavra, frase, top_unigrams_tmp)
                        top_ngrams = [registros for registros in Util.sort(
                            top_ngrams, 1, reverse=True) if registros[1] > 0.00]
                        top_ngrams = [(p, s) for (
                            p, s) in top_ngrams if wordnet.synsets(p, pos)]
                    else:
                        top_ngrams = []

                else:
                    candidatos_rankeados_disco = Util.abrir_json(
                        dir_obj_candidatos)
                    top_ngrams = candidatos_rankeados_disco['top_ngrams']
                    top_unigrams = candidatos_rankeados_disco['top_unigrams']

                cands = [p for p in cands if Util.e_mpalavra(p) == False]

                # TOP-10 predicoes inicializados com NGRAMS
                cands = [
                    p for (p, s) in top_ngrams[:cfgs['ngram']['max_cands_filtro']]]
                # Inicializando com TOP unigramas
                cands += [p for (p, s) in top_unigrams if not p in cands]

                extwk = ExtratorWikipedia

                for c in []:
                    if c in [p for p, v in gab_ordenado]:
                        print("\t@@ " + c + " <<<<")
                    else:
                        print("\t@@ " + c)

                    inst = ExtratorWikipedia.INSTANCE
                    url_des = "https://en.wikipedia.org/wiki/%s_(disambiguation)" % c
                    todas_urls = extwk.obter_links_relevantes_desambiguacao(
                        inst, url_des, c)

                    if not todas_urls:
                        todas_urls = extwk.obter_links_relevantes_desambiguacao(
                            inst, url_des, c.upper())
                    if not todas_urls:
                        todas_urls = ["https://en.wikipedia.org/wiki/"+c]

                    for url in todas_urls:
                        print("\t" + str(gab_ordenado))
                        print("\t" + url)
                        #print("\nTEXTO (%s):\n"%c)
                        dir_arquivo = "../Bases/Cache/Wikipedia/%s.json" % c
                        if Util.arq_existe(None, dir_arquivo) == False:
                            if Alvaro.salvar_documento_wikipedia(c, url):
                                print("\tSalvo com sucesso!")
                            else:
                                print("\tSalvo sem sucesso!")
                        else:
                            print("\tPagina ja contida no banco!")
                        # print(texto)
                        # print("\n")
                        # print(Alvaro.tf_exemplos(TextBlob(texto)))
                        print("\n")

            if verbose_geral == True:
                print("\n")
                print("Candidatos brutos: (%d): %s\n" %
                      (len(cands_brutos), cands_brutos))
                print("Seletor candidatos brutos acertou: " +
                      str(gab_ordenado[0][0] in cands_brutos))
                print("\n")
                print("Candidatos selecionados: " + str(cands))
                print("Seletor candidatos acertou: " +
                      str(gab_ordenado[0][0] in cands))
                print("\n")
                print("Seletor 1-GRAMS: " +
                      str(gab_ordenado[0][0] in top_unigrams))
                print("Seletor N-GRAMS: " +
                      str(gab_ordenado[0][0] in top_ngrams))
                print("\n")
                print("\nTOP N-GRAMS: " + str(top_ngrams))
                print("\nTOP 1-GRAMS: " + str(top_unigrams))
                print("\nUNIAO: " + str(cands))

            obj_candidatos = {
                'top_ngrams': top_ngrams,
                'top_unigrams': top_ngrams
            }

            if criterio == "assembled":
                # Este FOR indexa exemplos para a palavra
                for cand_iter in cands:
                    Alvaro.indexar_exemplos(cand_iter, pos)

                try:
                    Alvaro.indexar_exemplos(palavra, pos)

                    if Alvaro.PALAVRAS_EXEMPLOS_INDEXADOS != None:
                        dir_saida = Util.CONFIGS['corpora']['dir_palavras_indexadas_exemplos']
                        Util.salvar_json(dir_saida, list(
                            Alvaro.PALAVRAS_EXEMPLOS_INDEXADOS))

                except Exception, e:
                    print("\n%s\n" % str(e))

                try:
                    melhor_substituto = gab_ordenado[0][0]
                except:
                    melhor_substituto = ""

                if melhor_substituto in cands:
                    total_acertos += 1

                if melhor_substituto in cands and cfgs['metodo_pmi']['usar_metodo'] == True:
                    pares_ponderaveis = Alvaro.gerar_pares_pmi(
                        palavra, frase, cands)

                    print("PARES:")
                    print(pares_ponderaveis)
                    print("GABARITO: ")
                    print(gab_ordenado)
                    print("\n\n<enter>\n")

                    pontuacao_definicoes = Alvaro.pontuar_frase_correlacao_pmi(
                        pares_ponderaveis, pos, palavra, frase)

                    pontuacao_definicoes_tmp = []

                    for def_iter in pontuacao_definicoes:
                        registros = (def_iter, Util.media(
                            pontuacao_definicoes[def_iter]))
                        pontuacao_definicoes_tmp.append(registros)

                    pontuacao_definicoes_tmp = Util.sort(
                        pontuacao_definicoes_tmp, 1, reverse=True)

                    try:
                        melhor_score = pontuacao_definicoes_tmp[0][1]
                        cands_ordenados_estatisticamente = [
                            d for (d, s) in pontuacao_definicoes_tmp if s == melhor_score]

                        cands_tmp = []

                        for reg in cands_ordenados_estatisticamente:
                            lema, definicao = reg.split(':::')
                            sinonimos = BaseOx.obter_sins(
                                BaseOx.INSTANCE, lema, definicao, pos)
                            for s in sinonimos:
                                if s in cands:
                                    cands_tmp.append(s)

                        for s in cands:
                            if not s in cands_tmp:
                                cands_tmp.append(s)

                        cands = list(cands_tmp)

                    except:
                        cands_ordenados_estatisticamente = []

                arvores = Alvaro.construir_arvores_definicoes(
                    Alvaro.INSTANCE, palavra, pos, 4, cands)
                caminhos_arvore = Alvaro.construir_caminho_arvore(arvores)

                """
                    caminhos_wmd = Alvaro.pontuar_relacaosinonimia_wmd(Alvaro.INSTANCE,\
                                                            palavra, pos, caminhos_arvore)"""

                try:
                    inst = Alvaro.INSTANCE
                    predicao_final[lexelt] = [
                        p for p in cands if len(p) > 1][:qtde_sugestoes_oot]
                except Exception, e:
                    predicao_final[lexelt] = []

                if Alvaro.PONDERACAO_DEFINICOES != None:
                    Alvaro.salvar_base_ponderacao_definicoes()

            # Metodo de Baseline
            elif criterio == "word_move_distance":
                conj_predicao = []
                resultado_wmd = {}

                for cand_iter in cands:
                    nova_frase = frase.replace(palavra, cand_iter)
                    pont = rep_vetorial.word_move_distance(frase, nova_frase)
                    if not pont in resultado_wmd:
                        resultado_wmd[pont] = []
                    resultado_wmd[pont].append(cand_iter)

                for pont in sorted(resultado_wmd.keys(), reverse=False):
                    conj_predicao += resultado_wmd[pont]

                predicao_final[lexelt] = [
                    p for p in conj_predicao if len(p) > 1][:qtde_sugestoes_oot]

            elif criterio == "desambiguacao_wmd":
                qtde_sugestoes_oot = cfgs['params_exps']['qtde_sugestoes_oot']

                # Escolhendo apenas o 10 melhores candidatos
                cands = [p for p in cands if not Util.e_mpalavra(
                    p)][:qtde_sugestoes_oot]
                retorno_pares = Alvaro.gerar_pares_candidatos(
                    lexelt, cands, pos)
                inventario = []

                # for reg in retorno_pares:
                #    s1, s2 = reg.split(";;;")

                #    if s1.split(":::")[0] in cands:
                #        inventario.append(s1)
                #    else:
                #        raise Exception("Erro!")
                #    if s2.split(":::")[0] in cands:
                #        inventario.append(s2)
                #    else:
                #        raise Exception("Erro!")

                # Criando inventario de sentido
                for c in cands:
                    for d in BaseOx.obter_definicoes(BaseOx.INSTANCE, c, pos):
                        inventario.append("%s:::%s" % (c, d))
                        for f in BaseOx.obter_atributo(BaseOx.INSTANCE, c, pos, d, "exemplos"):
                            pont = RepVetorial.word_move_distance(
                                RepVetorial.INSTANCE, f, frase)
                            linha = (lexelt, frase, c, d, f, pont)
                            exemplos_ponderado.append(linha)

                inventario = list(set(inventario))
                ranking_wmd = Alvaro.des_inventario_estendido_wmd(
                    lexelt, frase, inventario)

                cands_tmp = []

                for lema_def, pontuacao in ranking_wmd:
                    lema, def_reg = lema_def.split(":::")
                    if not lema in cands_tmp:
                        cands_tmp.append(lema)

                cands = list(cands_tmp)

                try:
                    inst = Alvaro.INSTANCE
                    predicao_final[lexelt] = [
                        p for p in cands if len(p) > 1][:qtde_sugestoes_oot]
                except Exception, e:
                    predicao_final[lexelt] = []

            elif criterio == 'exemplos':
                template_dir = "../Bases/Cache/Oxford/FrasesWMD/%s.frase.json"
                todos_ex = Util.abrir_json(template_dir % lexelt)

                melhor_predicao = []

                if Alvaro.possui_moda(Alvaro.INSTANCE, gab_ordenado):
                    melhor_predicao = [gab_ordenado[0][0]]

                arvores = Alvaro.construir_arvores_definicoes(
                    Alvaro.INSTANCE, palavra, pos, 4, cands)
                caminhos_arvore = Alvaro.construir_caminho_arvore(
                    Alvaro.INSTANCE, arvores, cands)

                print("Caminhos arvore:")
                Util.exibir_json(caminhos_arvore, bloquear=True)

                try:
                    pass
#                    cands_tmp = Alvaro.calc_distancia_ex(lexelt, todos_ex, (frase, palavra), melhor_predicao=melhor_predicao)
                except Exception, e:
                    pass

                    registros = []

                    for c in []:
                        for d in BaseOx.obter_definicoes(BaseOx.INSTANCE, c, pos):
                            for f in BaseOx.obter_atributo(BaseOx.INSTANCE, c, pos, d, "exemplos"):
                                # Calculando distancia do contexto para a frase de exemplo
                                dist = RepVetorial.word_move_distance(
                                    RepVetorial.INSTANCE, frase, f)
                                reg = (lexelt, frase, c, d, f, dist)
                                registros.append(reg)

                    Util.salvar_json(template_dir % lexelt, registros)

                    try:
                        pass
                        #todos_ex = Util.abrir_json(template_dir % lexelt)
                        #cands_tmp = Alvaro.calc_distancia_ex(lexelt, todos_ex, (frase, palavra), melhor_predicao=melhor_predicao)
                    except Exception, e:
                        pass

                try:
                    inst = Alvaro.INSTANCE
                    predicao_final[lexelt] = [
                        p for p in cands if len(p) > 1][:qtde_sugestoes_oot]
                except Exception, e:
                    predicao_final[lexelt] = []

            if cont + 1 < len(indices_lexelts):
                prox_lexelt = todos_lexelts[cont+1]
                prox_palavra = prox_lexelt.split(".")[0]
                if palavra != prox_palavra:
                    BaseOx.objs_unificados = None
                    BaseOx.objs_unificados = {}

            if Alvaro.PONDERACAO_DEFINICOES != None:
                Util.salvar_json(
                    "../Bases/ponderacao_definicoes.json", Alvaro.PONDERACAO_DEFINICOES)

        if exemplos_ponderado:
            Util.salvar_json("../Bases/%s.frase.json" %
                             lexelt, exemplos_ponderado)

        gc.collect()
        print("\n\n\n\n\n\n\n")

    print("\n\nTOTAL ACERTOS: %d\n\n" % total_acertos)

    # Para o Garbage Collector
    cache_rel_sinonimia = None
    cache_seletor_candidatos = None
    cache_resultado_desambiguador = None

    # Remover predicoes falhas
    predicao_final_copia = dict(predicao_final)

    for reg in predicao_final:
        if predicao_final[reg] in [[], ""]:
            del predicao_final_copia[reg]

    predicao_final = dict(predicao_final_copia)

    # Predicao, caso de entrada, gabarito
    return predicao_final, casos_testes_dict, gabarito_dict, obj_candidatos, todos_cands


def predizer_sins_caso_unico(cfgs, frase, palavra, pos, gabarito):
    verbose_geral = cfgs['verbose']['geral']
    separador = cfgs['separador']
    med_sim = cfgs['medida_similaridade']
    saida_contigencial = cfgs['saida_contig']['habilitar']

    fontes_cands = ['wordnet', 'oxford']

    lista_entradas = [(frase, palavra, pos, gabarito)]

    # Construtor com carregador de modelo
    dir_modelo = "%s/%s" % (cfgs['caminho_bases'], cfgs['modelos']['default'])
    rep_vet = RepVetorial.INSTANCE

    casador_manual = None
    base_ox = BaseOx.INSTANCE
    alvaro = Alvaro.INSTANCE

    des_ox = DesOx.INSTANCE
    des_wn = None

    todos_cands = { }

    # Resultado de saida <lexelt : lista>
    predicao_final = dict()

    vldr_se = VlddrSemEval(cfgs)

    palavras_invalidas = []

    cache_rel_sinonimia = dict()
    cache_seletor_candidatos = dict()
    cache_resultado_desambiguador = dict()

    if Util.CONFIGS['ngram']['usar_seletor'] == False:
        Alvaro.NGRAMS_SIGNALMEDIA = {}
        Alvaro.NGRAMS_LEIPZIG = {}
        Alvaro.NGRAMS_COCA = {}
    else:

        if "coca" in Util.CONFIGS['ngram']['fontes']:
            print("\nCarregando n-grams COCA Corpus!")
            Alvaro.NGRAMS_COCA = Util.abrir_json(cfgs['dir_coca_ngrams'])
            print("n-grams COCA Corpus carregado!")

        if "signalmedia" in Util.CONFIGS['ngram']['fontes']:
            # Abrindo ngrams SignalMedia
            arq_ngrams_tmp = {}

            with open(Util.CONFIGS['ngram']['signalmedia_5grams'], 'r') as todas_linhas:
                print("\nCarregando n-grams SignalMedia Corpus!")

                for linha_ngram in todas_linhas:
                    try:
                        tokens = linha_ngram.split(":")
                        freq_ngram = int(tokens[-1])
                        ngram = str(
                            ":".join(tokens[:-1])).strip('\t').replace("\t", " ")
                        Alvaro.NGRAMS_SIGNALMEDIA[ngram] = freq_ngram
                    except:
                        pass

                print("\nn-grams SignalMedia Corpus carregado!")

            print("\nDerivando n-grams SignalMedia Corpus!")

            ngrams_signalmedia_derivados = \
                Alvaro.derivar_ngrams_string(Alvaro.NGRAMS_SIGNALMEDIA,
                                             cfgs['ngram']['min'],
                                             cfgs['ngram']['max'])
            for ng in ngrams_signalmedia_derivados:
                Alvaro.NGRAMS_SIGNALMEDIA[ng] = ngrams_signalmedia_derivados[ng]

            print("n-grams SignalMedia Corpus derivado!")

            ngrams_signalmedia_derivados = None

    dir_palavras_indexadas = Util.CONFIGS['corpora']['dir_palavras_indexadas_exemplos']
    Alvaro.PALAVRAS_EXEMPLOS_INDEXADOS = set(
        Util.abrir_json(dir_palavras_indexadas, criarsenaoexiste=True))

    obj_candidatos = { }
    total_acertos = 0

    qtde_sugestoes_oot = Util.CONFIGS['params_exps']['qtde_sugestoes_oot'][0]
    qtde_sugestoes_oot = 200

    contador = 0

    for frase, palavra, pos, gab_ordenado in lista_entradas:
        lexelt = ""
        frase = Util.descontrair(frase).replace("  ", " ")

        exemplos_ponderado = [ ]

        print("\n\n\n\n\n\n")
        print("@@@ Processando a entrada " + str(lexelt))
        print("*** %s\n" % str((frase, palavra, pos)))
        print("Gabarito: %s" % str(gab_ordenado))

        tripla_cands = alvaro.selec_candidatos(
            palavra, pos, fontes=fontes_cands)

        cands = tripla_cands['uniao']
        cands_best = tripla_cands['best']
        cands_oot = tripla_cands['oot']

        todos_cands[lexelt] = tripla_cands

        # Removendo palavra
        if palavra in cands:
            cands.remove(palavra)

        cands_brutos = list(cands)

        top_unigrams = [(p, BaseOx.freq_modelo(
            BaseOx.INSTANCE, p)) for p in cands]
        top_unigrams = [registros for registros in sorted(
            top_unigrams, key=lambda x: x[1], reverse=True) if registros[1] > 0]

        if cfgs['ngram']['usar_seletor'] == True:
            top_unigrams_tmp = [p for (p, s) in top_unigrams]
            top_ngrams = Alvaro.selec_ngrams(
                Alvaro.INSTANCE, palavra, frase, top_unigrams_tmp)
            top_ngrams = [registros for registros in Util.sort(
                top_ngrams, 1, reverse=True) if registros[1] > 0.00]
            top_ngrams = [(p, s) for (
                p, s) in top_ngrams if wordnet.synsets(p, pos)]
        else:
            top_ngrams = [ ]

            cands = [p for p in cands if Util.e_mpalavra(p) == False]

            # TOP-10 predicoes inicializados com NGRAMS
            cands = [
                p for (p, s) in top_ngrams[:cfgs['ngram']['max_cands_filtro']]]
            # Inicializando com TOP unigramas
            cands += [p for (p, s) in top_unigrams if not p in cands]
        
        if verbose_geral == True:
            print("\n")
            print("Candidatos brutos: (%d): %s\n" %
                    (len(cands_brutos), cands_brutos))
            print("Seletor candidatos brutos acertou: " +
                    str(gab_ordenado[0][0] in cands_brutos))
            print("\n")
            print("Candidatos selecionados: " + str(cands))
            print("Seletor candidatos acertou: " +
                    str(gab_ordenado[0][0] in cands))
            print("\n")
            print("Seletor 1-GRAMS: " +
                    str(gab_ordenado[0][0] in top_unigrams))
            print("Seletor N-GRAMS: " +
                    str(gab_ordenado[0][0] in top_ngrams))
            print("\n")
            print("\nTOP N-GRAMS: " + str(top_ngrams))
            print("\nTOP 1-GRAMS: " + str(top_unigrams))
            print("\nUNIAO: " + str(cands))

        obj_candidatos = {
            'top_ngrams': top_ngrams,
            'top_unigrams': top_unigrams
        }

    return obj_candidatos


def testar_indexes():
    from Indexador import Whoosh
    for doc in Whoosh.consultar_documentos(['heap'], operador="AND", dir_indexes=Whoosh.DIR_INDEXES_EXEMPLOS):
        print("\n")
        print(doc['title'])
        print(doc['path'])
        print(doc['content'])
        print("\n-------------------")

    #paths = [ ]
    # for doc in Whoosh.documentos():
    #    if 'SignalMedia' in doc['path']:
     #       paths.append(doc['path'])

    #docnums = [ ]
    # for path in paths:
    #    dn = Whoosh.buscar_docnumer_bypath(path)
    #    raw_input(dn)
    #    docnums.append(dn)

    # Whoosh.remover_doc(docnums)
    # print("Deletando...")
    #print(Whoosh.deletar_bypattern('path', '*SignalMedia*'))
    # print("Deletando!")

    # for doc in Whoosh.documentos():
    #    if 'SignalMedia' in doc['path']:
    #        print(doc)

    # Whoosh.iniciar_indexacao_signalmedia("/mnt/ParticaoAlternat/Bases/Corpora/SignalMedia/alguns_arquivos.txt")
    exit(0)


def aplicar_abordagens(cfgs):
    from SemEval2007 import VlddrSemEval

    Util.verbose_ativado = False
    Util.cls()

    params_exps = cfgs['params_exps']

    Util.CONFIGS = cfgs

    #app_cfg = Util.abrir_json("./keys.json")
    #Util.CONFIGS['oxford']['app_id'] = app_cfg['app_id']
    #Util.CONFIGS['oxford']['app_key'] = app_cfg['app_key']

    # InterfaceBases.setup(cfgs)
    rep_vet = RepVetorial.INSTANCE

    ExtratorWikipedia.INSTANCE = ExtratorWikipedia(cfgs)

    caminho_bases = cfgs['caminho_bases']

    vldr_se = VlddrSemEval.INSTANCE  # Validador SemEval 2007
    rep_vet = RepVetorial.INSTANCE

    diretorio_saida_json = cfgs['dir_saida_json']
    dir_saida_abrdgm = cfgs['saida_experimentos']

    # GERANDO PARAMETROS
    todos_criterios = params_exps['todos_criterios']
    qtde_exemplos = params_exps['qtde_exemplos']
    qtde_sugestoes_best = params_exps['qtde_sugestoes_best']
    qtde_sugestoes_oot = params_exps['qtde_sugestoes_oot']
    todas_fontes_def = params_exps['todas_fontes_def']
    tipos_base = params_exps['tipos_base']

    flags_usar_gabarito = [v for v in params_exps['usar_gabarito']]
    flags_usar_exemplos = [v for v in params_exps['usar_exemplos']]

    pos_avaliadas = params_exps['pos_avaliadas'] if params_exps['pos_avaliadas'] else [
        None]
    max_indice_pos = cfgs['params_exps']['max_entradas_pos']

    parametrizacao = [
        todos_criterios,
        qtde_exemplos,
        todas_fontes_def,
        tipos_base,
        flags_usar_gabarito,
        flags_usar_exemplos,
        pos_avaliadas
    ]

    # Gerando todas combinacoes de parametros p/ reproduzir experimentos
    parametrizacao = list(itertools.product(*parametrizacao))

    # Filtra os casos de entrada por lexelt
    cfgs_se = cfgs["semeval2007"]
    caminho_raiz_semeval = "%s/%s" % (caminho_bases, cfgs_se["dir_raiz"])
    path_base_teste = "%s/%s" % (caminho_raiz_semeval,
                                 cfgs_se["test"]["input"])

    casos_filtrados_tmp = vldr_se.carregar_caso_entrada(
        path_base_teste, padrao_se=True)
    contadores = dict([(pos, 0) for pos in cfgs_se['todas_pos']])
    lexelts_filtrados = []

    for lexelt in casos_filtrados_tmp:
        pos_tmp = re.split('[\s\.]', lexelt)[1]  # 'war.n 0' => ('war', 'n', 0)
        if contadores[pos_tmp] < max_indice_pos:
            lexelts_filtrados.append(lexelt)
            contadores[pos_tmp] += 1
    # Fim do filtro de casos de entrada por lexelt

    lf = lexelts_filtrados
    res_best = vldr_se.aval_parts_orig(
        'best', pos_filtradas=pos_avaliadas[0], lexelts_filtrados=lf).values()
    res_oot = vldr_se.aval_parts_orig(
        'oot', pos_filtradas=pos_avaliadas[0], lexelts_filtrados=lf).values()

    cfg_ngram_ox = cfgs['ngram']['dir_exemplos']

    ch_ngram_plain = cfg_ngram_ox['oxford_plain']
    ch_ngram_tagueados = cfg_ngram_ox['oxford_tagueados']

    Alvaro.abrir_contadores_pmi()

    for parametros in parametrizacao:
        crit, max_ex, fontes_def, tipo, usr_gab, usr_ex, pos_avaliadas = parametros

        if type(pos_avaliadas) != list:
            raise Exception(
                "\n\nAs POS avaliadas devem ser expressas no formato de list!\n\n")

        predicao = set()
        casos = set()
        gabarito = set()

        exe = "realizar_predicao"

        if exe == "realizar_predicao":
            try:
                pred_saida = predizer_sins(
                    cfgs,
                    lexelts_filtrados=lexelts_filtrados,
                    usar_gabarito=usr_gab,
                    criterio=crit,
                    tipo=tipo,
                    max_ex=max_ex,
                    usr_ex=usr_ex,
                    fontes_def=fontes_def,
                    pos_avaliadas=pos_avaliadas,
                    rep_vetorial=rep_vet,
                    carregar_candidatos_disco=False
                )

                predicao, casos, gabarito, candidatos, todos_cands = pred_saida

                from SemEval2007 import VlddrSemEval
                todas_instancias, media = VlddrSemEval.aplicar_gap(
                    predicao, gabarito)
                print("\n\nGAP: %s\n\n" % str(media))

            except Exception, e:
                import traceback
                print("\n")
                traceback.print_exc()
                print("\n%s\n" % str(e))

                Alvaro.salvar_contadores_pmi()

                if Alvaro.PONDERACAO_DEFINICOES != None:
                    print("\nSalvando relacao entre sinonimos pontuadas via-WMD!\n")
                    Alvaro.salvar_base_ponderacao_definicoes()

        elif not exe == 'f':
            print("\n\nOpcao invalida!\nAbortando execucao...\n\n")
            exit(0)

        Alvaro.salvar_contadores_pmi()

        # GERANDO SCORE
        for cont in qtde_sugestoes_oot:
            nome_abrdgm = cfgs['padrao_nome_submissao']  # '%d-%s-%s ... %s'
            reg = (crit, usr_gab, tipo, max_ex, usr_ex, fontes_def, 'oot')
            nome_abrdgm = nome_abrdgm % reg

            predicao_oot = {}

            for lexelt in predicao:
                try:
                    sugestoes = [p for p in predicao[lexelt]
                                 if p in todos_cands[lexelt]['oot']]
                    predicao_oot[lexelt] = sugestoes
                except:
                    pass

            vldr_se.formtr_submissao(
                dir_saida_abrdgm+"/"+nome_abrdgm, predicao_oot, None, cont, ":::")

            print("\nSaida da sua abordagem: " +
                  dir_saida_abrdgm+"/"+nome_abrdgm+"\n")

            if Util.arq_existe(dir_saida_abrdgm, nome_abrdgm):
                try:
                    res_oot.append(vldr_se.obter_score(
                        dir_saida_abrdgm, nome_abrdgm))
                except Exception, reg:
                    print("\n@@@ Erro na geracao do score da abordagem '%s'" %
                          nome_abrdgm+"\n")

        nome_abrdgm = cfgs['padrao_nome_submissao']
        reg = (crit, usr_gab, tipo, max_ex, usr_ex, fontes_def, 'best')
        nome_abrdgm = nome_abrdgm % reg

        predicao_best = {}

        for lexelt in predicao:
            if lexelt in predicao_best and lexelt in predicao_oot:
                if predicao_best[lexelt] != predicao_oot[lexelt]:
                    print("\n")
                    print((predicao_best[lexelt], predicao_oot[lexelt]))
                    raw_input("\nSao diferentes!\n")

        for lexelt in predicao:
            try:
                sugestoes = [p for p in predicao[lexelt]
                             if p in todos_cands[lexelt]['best']]
                predicao_best[lexelt] = sugestoes
            except:
                pass

        print("Saida da sua abordagem: "+dir_saida_abrdgm+"/"+nome_abrdgm)
        vldr_se.formtr_submissao(
            dir_saida_abrdgm+"/"+nome_abrdgm, predicao_best, None, 1, "::")

        if Util.arq_existe(dir_saida_abrdgm, nome_abrdgm):
            try:
                res_best.append(vldr_se.obter_score(
                    dir_saida_abrdgm, nome_abrdgm))
            except:
                print("\n@@@ Erro na geracao do score da abordagem '%s'" %
                      nome_abrdgm)

    if Alvaro.PALAVRAS_EXEMPLOS_INDEXADOS != None:
        dir_saida = Util.CONFIGS['corpora']['dir_palavras_indexadas_exemplos']
        Util.salvar_json(dir_saida, list(Alvaro.PALAVRAS_EXEMPLOS_INDEXADOS))
        Alvaro.PALAVRAS_EXEMPLOS_INDEXADOS = None

    Alvaro.salvar_base_ponderacao_definicoes()

    res_tarefas = {'best': res_best, 'oot': res_oot}

    # Exibindo todas abordagens
    for nome_tarefa in res_tarefas:
        res_tarefa = res_tarefas[nome_tarefa]
        chave = ""
        while not chave in res_tarefa[0].keys():
            msg = "\nEscolha a chave pra ordenar a saida "
            chave = raw_input(msg+nome_tarefa.upper()+": " +
                              str(res_tarefa[0].keys()) + ": ")

        res_tarefa = sorted(res_tarefa, key=itemgetter(chave), reverse=True)

        Util.salvar_json("%s/%s.%s" % (diretorio_saida_json,
                                       nome_tarefa.upper(), nome_tarefa), res_tarefa)
        print("\n" + chave.upper() + "\t-----------------------")

        for reg in res_tarefa:
            print(reg['nome'])
            etmp = dict(reg)
            del etmp['nome']
            print(etmp)
            print('\n')

        print("\n")


if __name__ == '__main__':
    cfgs = Util.carregar_cfgs(argv[1])
    InterfaceBases.setup(cfgs, dir_keys="./keys.json")

    if len(argv) < 3:
        print('\nParametrizacao errada!\nTente py ./main <dir_config_file>\n\n')
        exit(0)

    elif argv[2] == 'sinonimos':
        palavra = argv[3]
        pos = argv[4]
        min_pmi = float(argv[5])

        try:
            derivar_palavras = eval(argv[6])
        except:
            derivar_palavras = False

        todas_definicoes = [(palavra, d) for d in BaseOx.obter_definicoes(
            BaseOx.INSTANCE, palavra, pos)]
        todos_sinonimos = Alvaro.obter_sinonimos_filtrados(
            todas_definicoes, pos, remover_sinonimos_replicados=True)

        for lexelt in todos_sinonimos.items():
            palavra_definicao, sinonimos = eval(lexelt[0]), lexelt[1]
            palavra, definicao = palavra_definicao

            print((palavra, definicao, sinonimos))

            inst_repvet = RepVetorial.INSTANCE

            for t in nltk.word_tokenize(definicao.lower()):
                try:
                    if not derivar_palavras:
                        soma = [ ]
                        interseccao = [ ]
                    else:
                        soma = RepVetorial.obter_palavras_relacionadas(
                            inst_repvet, positivos=[palavra, t], pos=pos, topn=200)
                        interseccao = Alvaro.interseccao_palavras(
                            t, palavra, pos)
                        soma = [p for p, s in soma]

                    pmi = Alvaro.pmi(palavra, t)
                    if pmi >= min_pmi:
                        print("\n")
                        print("\t%s: %f" % ((palavra, t), pmi))
                        print("\tSoma: " + str(soma))
                        print("\tInterseccao: " + str(interseccao))
                except:
                    pass

            print("\n\tSINONIMOS:")
            for t in sinonimos:
                try:
                    if not derivar_palavras:
                        soma = []
                        interseccao = []
                    else:
                        soma = RepVetorial.obter_palavras_relacionadas(
                            inst_repvet, positivos=[palavra, t], pos=pos, topn=200)
                        interseccao = Alvaro.interseccao_palavras(
                            t, palavra, pos)
                        soma = [p for p, s in soma]

                    pmi = Alvaro.pmi(palavra, t)
                    if pmi >= min_pmi:
                        print("\n")
                        print("\t%s: %f" % ((palavra, t), pmi))
                        print("\tSoma: " + str(soma))
                        print("\tInterseccao: " + str(interseccao))
                except:
                    pass

            print("\n")

    elif argv[2] == 'aplicar':
        gc.enable()
        aplicar_abordagens(cfgs)

    elif argv[2] == 'caso_unico':
        frase = argv[3]
        palavra = argv[4]
        pos = argv[5]
        gabarito = eval(argv[6])

        vldr_se = VlddrSemEval.INSTANCE
        entrada, gabarito = VlddrSemEval.carregar_bases(vldr_se, cfgs, 'trial')

        gabarito_tmp = dict(gabarito)

#        for lexelt in gabarito_tmp:
#            raw_input(gabarito_tmp[lexelt])

        for lexelt in entrada:
            try:
                palavra, pos, numero = re.split('[\.\s]', lexelt)
                frase = entrada[lexelt][0]

                gabarito = gabarito_tmp[lexelt]
                saida = predizer_sins_caso_unico(cfgs, frase, palavra, pos, gabarito)

                print((palavra, pos, numero))                
                print(saida['top_ngrams'])

            except Exception, e: pass

    elif argv[2] == 'indexar':
        lista_arqs = "../Bases/Corpora/SignalMedia/arquivos.txt"
        textos_repetidos = "../Bases/Corpora/SignalMedia/textos_repetidos.txt"

        Whoosh.iniciar_indexacao_signalmedia(lista_arqs, textos_repetidos)

    elif argv[2] == 'ver_base':
        tipo = argv[3]
        exibir_bases(cfgs, tipo=tipo)

    elif argv[2] == 'pmi':
        palavra1 = argv[3]
        palavra2 = argv[4]

        pmi = Alvaro.pmi(palavra1, palavra2)
        print("\nPMI para o par (%s, %s): %f" % (palavra1, palavra2, pmi))

    elif argv[2] == 'pmi_definicao':
        import nltk
        palavra = argv[3]
        pos = argv[4]

        for d in BaseOx.obter_definicoes(BaseOx.INSTANCE, palavra, pos):
            print((palavra, pos, d))
            for t in nltk.word_tokenize(d.lower()):
                try:
                    pmi = Alvaro.pmi(palavra, t)
                    print("\t%s: %f" % ((palavra, t), pmi))
                except:
                    pass
            print("\n")

    elif argv[2] == 'ver_definicoes':
        palavra, pos = argv[3], argv[4]

        for defiter in BaseOx.obter_definicoes(BaseOx.INSTANCE, palavra, pos):
            sins = BaseOx.obter_sins(BaseOx.INSTANCE, palavra, defiter, pos)
            print(defiter + ' - ' + str(sins))

    elif argv[2] == 'extrair':
        from ExtratorWikipedia import ExtratorWikipedia
        ext = ExtratorWikipedia(cfgs)

        frases_exemplo = ext.obter_frases_exemplo(argv[3])

        for f in frases_exemplo:
            print('\t- ' + str(f))

        print("\n\nComprimento: %d\n" % len(frases_exemplo))

    elif argv[2] == 'descrever':
        palavra = argv[3]
        pos = argv[4]

        print("\n\n")
        for d in BaseOx.obter_definicoes(BaseOx.INSTANCE, palavra, pos=pos):
            d_sins = BaseOx.obter_sins(BaseOx.INSTANCE, palavra, d, pos=pos)
            print((palavra, pos))
            print(d)
            correlatas = []
            for s in d_sins:
                similares_tmp = [lexelt[0]
                                 for lexelt in Alvaro.palavras_similares(s, pos)]
                correlatas.append(similares_tmp)
                #print((s, similares_tmp))
            interseccao = set(correlatas[0])
            for c in correlatas[:1]:
                interseccao = set(interseccao) & set(c)
            raw_input(("INTERSECCAO", interseccao))
            print('\n\n')

    elif argv[2] == 'correlatas':
        palavra = argv[3]
        pos = argv[4]

        for d in BaseOx.obter_definicoes(BaseOx.INSTANCE, palavra, pos):
            print(d.lower())

        inst = RepVetorial.INSTANCE
        #s1 = RepVetorial.obter_palavras_relacionadas(inst, ['vehicle', 'road', 'engine'])
        #s2 = RepVetorial.obter_palavras_relacionadas(inst, ['vehicle', 'road', 'engine'])
        s3 = RepVetorial.obter_palavras_relacionadas(
            inst, ['leftover', 'remainder'], topn=100)
        s4 = RepVetorial.obter_palavras_relacionadas(
            inst, ['leftover', 'remainder'], topn=100)

        s3 = [p for p, s in s3]
        s4 = [p for p, s in s4]

        print(s3)
        print("\n")
        print(s4)
        print("\n\n")
        print(set(s3).intersection(s4))

    elif argv[2] == 'frases_wikipedia':
        palavra = argv[3]
        for lema, desc, url, f in ExtratorWikipedia.obter_frases_exemplo(palavra):
            print((desc, f))

    print('\n\n\n\nFim do __main__\n\n\n\n')


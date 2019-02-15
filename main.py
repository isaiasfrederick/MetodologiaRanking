#! coding: utf-8
import itertools
import os
import re
import signal
import statistics
import sys
import traceback
from operator import itemgetter
from statistics import mean as media
from sys import argv
import json

from nltk.corpus import wordnet
from textblob import TextBlob

from Indexador import Whoosh

# Testar Abordagem Alvaro
from Alvaro import Alvaro
from CasadorManual import CasadorManual
# Experimentacao
from DesambiguadorWordnet import DesWordnet
from DesOx import DesOx
from InterfaceBases import InterfaceBases
from OxAPI import BaseOx, CliOxAPI, ExtWeb
from RepresentacaoVetorial import RepVetorial
from SemEval2007 import *
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
                print("Candidatos: " + str(alvaro.selec_candidatos(palavra, pos, fontes=['wordnet', 'oxford'])))
                print("\n\n")


def carregar_bases(cfgs, tipo_base, pos_avaliadas=None):
    from SemEval2007 import VlddrSemEval
    return VlddrSemEval.carregar_bases(VlddrSemEval.INSTANCE, cfgs, tipo_base, pos_avaliadas=pos_avaliadas)


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
    rep_vetorial=None):

    #dir_obj_candidatos = cfgs['caminho_bases']+'/'+cfgs['arquivo_candidatos']
    separador = cfgs['separador']
    med_sim = cfgs['medida_similaridade']
    saida_contigencial = cfgs['saida_contig']['habilitar']

    #obj_candidatos = Util.abrir_json(dir_obj_candidatos, criar=True)

    if fontes_def != 'oxford':
        raise Exception("Esta fonte de definicoes nao é contem exemplos...")

    if pos_avaliadas in [None, [ ]]:
        pos_avaliadas = cfgs['semeval2007']['todas_pos']
    if type(pos_avaliadas) != list:
        raise Exception("\n\nAs POS avaliadas devem ser uma list!\n\n")

    # Construtor com carregador de modelo
    dir_modelo = "%s/%s"%(cfgs['caminho_bases'], cfgs['modelos']['default'])
    rep_vet = RepVetorial.INSTANCE

    casador_manual = None
    base_ox = BaseOx.INSTANCE
    alvaro = Alvaro.INSTANCE

    des_ox = DesOx(cfgs, base_ox, rep_vetorial=rep_vetorial)
    des_wn = DesWordnet(cfgs)

    if max_ex == -1:
        max_ex = sys.maxint

    # Resultado de saida <lexelt : lista>
    predicao_final = dict()

    # Fonte para selecionar as definicoes e fonte para selecionar os candidatos
    # fontes_def, fontes_cands = raw_input("Digite a fonte para definicoes: "), ['oxford', 'wordnet']
    fontes_def, fontes_cands = fontes_def, cfgs['fontes_cands']
    casos_testes_dict, gabarito_dict = carregar_bases(cfgs, tipo, pos_avaliadas=pos_avaliadas)

    if lexelts_filtrados in [None, [ ]]:
        casos_testes_dict_tmp = list(casos_testes_dict.keys())
    else:
        casos_testes_dict_tmp = set(casos_testes_dict.keys())&set(lexelts_filtrados)
        casos_testes_dict_tmp = list(casos_testes_dict_tmp)

    vldr_se = VlddrSemEval(cfgs)
    todos_lexelts = list(set(casos_testes_dict_tmp)&set(gabarito_dict.keys()))
    indices_lexelts = [i for i in range(len(todos_lexelts))]

    palavras_invalidas = [ ]

    cache_rel_sinonimia = dict()
    cache_seletor_candidatos = dict()
    cache_resultado_desambiguador = dict()

    if Util.CONFIGS['ngram']['usar_seletor'] == False:
        Alvaro.NGRAMS_COCA = { }
        Alvaro.NGRAMS_SIGNALMEDIA = { }
    else:
        
        if 'coca' in Util.CONFIGS['ngram']['fontes']:
            print("\nCarregando n-grams COCA Corpus!")
            Alvaro.NGRAMS_COCA = Util.abrir_json(cfgs['dir_coca_ngrams'])
            print("n-grams COCA Corpus carregado!")

        if 'signalmedia' in Util.CONFIGS['ngram']['fontes']:
            # Abrindo ngrams SignalMedia
            arq_ngrams_tmp = { }

            with open(Util.CONFIGS['ngram']['signalmedia_5grams'], 'r') as todas_linhas:
                print("\nCarregando n-grams SignalMedia Corpus!")

                for linha_ngram in todas_linhas:
                    try:
                        tokens = linha_ngram.split(":")
                        freq_ngram = int(tokens[-1])
                        ngram = str(":".join(tokens[:-1])).strip('\t').replace("\t", " ")
                        Alvaro.NGRAMS_SIGNALMEDIA[ngram] = freq_ngram
                    except: pass

                print("\nn-grams SignalMedia Corpus carregado!")

            print("\nDerivando n-grams SignalMedia Corpus!")

            ngrams_signalmedia_derivados = \
                        Alvaro.derivar_ngrams_string(Alvaro.NGRAMS_SIGNALMEDIA,\
                                                            cfgs['ngram']['min'],\
                                                            cfgs['ngram']['max'])
            for ng in ngrams_signalmedia_derivados:
                Alvaro.NGRAMS_SIGNALMEDIA[ng] = ngrams_signalmedia_derivados[ng]

            print("n-grams SignalMedia Corpus derivado!")

            ngrams_signalmedia_derivados = None

    dir_palavras_indexadas = Util.CONFIGS['corpora']['dir_palavras_indexadas_exemplos']
    Alvaro.PALAVRAS_EXEMPLOS_INDEXADOS = set(Util.abrir_json(dir_palavras_indexadas, criarsenaoexiste=True))

    obj_candidatos = { }

    for cont in indices_lexelts:
        lexelt = todos_lexelts[cont]
        frase, palavra, pos = casos_testes_dict[lexelt]
        frase = Util.descontrair(frase).replace("  ", " ")
        palavra = lexelt.split(".")[0]

        if not palavra in palavras_invalidas:
            chave_seletor_candidatos = str((palavra, pos))
            interseccao_casos = list(set(casos_testes_dict_tmp)&set(gabarito_dict.keys()))
            gab_ordenado = Util.sort(gabarito_dict[lexelt], 1, reverse=True)

            print("\n\n\n\n\n\n")
            print("@@@ Processando a entrada " + str(lexelt))
            print("%d / %d"%(cont+1, len(interseccao_casos)))
            print("*** %s\n"%str((frase, palavra, pos)))
            print("Gabarito: %s"%str(gab_ordenado))

            if not chave_seletor_candidatos in cache_seletor_candidatos:
                if usar_gabarito == True:
                    cands = [e[0] for e in gabarito_dict[lexelt] if not Util.e_mpalavra(e[0])]
                else:

                    print("\nSelecionando candidatos...")
                    cands = alvaro.selec_candidatos(palavra, pos, fontes=fontes_cands)
                    cands = [p for p in cands if p.istitle() == False]
                    cands = [p for p in cands if not Util.e_mpalavra(p)]
                    print("\nCandidatos selecionados...")

                    if palavra in cands:
                        cands.remove(palavra)

                    cands_brutos = list(cands)

                    top_unigrams = [(p, BaseOx.freq_modelo(BaseOx.INSTANCE, p)) for p in cands]
                    top_unigrams = [r[0] for r in sorted(top_unigrams, key=lambda x: x[1], reverse=True) if r[1] > 0]

                    if cfgs['ngram']['usar_seletor'] == True:
                        top_ngrams = Alvaro.selec_ngrams(Alvaro.INSTANCE, palavra, frase, top_unigrams)
                        top_ngrams = [r[0] for r in Util.sort(top_ngrams, 1, reverse=True) if r[1] > 0.00]
                        top_ngrams = [p for p in top_ngrams if wordnet.synsets(p, pos)]
                    else:
                        top_ngrams = [ ]

                    cands = top_ngrams[:cfgs['ngram']['max_cands_filtro']]

                    for uni in top_unigrams:
                        if not uni in cands:
                            cands.append(uni)                   

            else:
                cands = cache_seletor_candidatos[chave_seletor_candidatos]

            print("\n")
            print("Candidatos brutos: (%d): %s\n"%(len(cands_brutos), cands_brutos))
            print("Seletor candidatos brutos acertou: " + str(gab_ordenado[0][0] in cands_brutos))
            print("\n")
            print("Candidatos selecionados: " + str(cands))
            print("Seletor candidatos acertou: " + str(gab_ordenado[0][0] in cands))
            print("\n")
            print("Seletor 1-GRAMS: " + str(gab_ordenado[0][0] in top_unigrams))
            print("Seletor N-GRAMS: " + str(gab_ordenado[0][0] in top_ngrams))
            print("\n")
            print("\nTOP N-GRAMS: " + str(top_ngrams))
            print("\nTOP 1-GRAMS: " + str(top_unigrams))
            print("\nUNIAO: " + str(cands))

            obj_candidatos[lexelt] = {
                'top_ngrams' : top_ngrams,
                'top_unigrams' : top_ngrams
            }

            if criterio == 'frequencia':
                cliente_ox = CliOxAPI(cfgs)

                cands_ponts = [ ]
                for sin in cands:
                    try:
                        cands_ponts.append((sin, cliente_ox.obter_frequencia(sin)))
                    except Exception, e:
                        cands_ponts.append((sin, -1))

                res_predicao = [reg[0] for reg in sorted(cands_ponts, key=lambda x:x[1], reverse=True)]
                predicao_final[lexelt] = res_predicao


            elif criterio == 'baseline_frequencia':
                uni_sins = set() # Universo sinonimos
                for d in BaseOx.obter_definicoes(base_ox, palavra, pos=pos):
                    for s in BaseOx.obter_sins(base_ox, palavra, d, pos=pos):
                        if Util.e_mpalavra(s) == False:
                            try: freq = BaseOx.obter_frequencia_oxford(base_ox, s)
                            except: freq = 0
                            uni_sins.add((s, freq))

                qtde_sugestoes_oot = Util.CONFIGS['params_exps']['qtde_sugestoes_oot'][0]
                predicao_final[lexelt] = [e[0] for e in sorted(list(uni_sins), key=lambda x: x[1], reverse=True)][:qtde_sugestoes_oot]

            elif criterio == 'embbedings':
                res_tmp = rep_vet.obter_palavras_relacionadas(positivos=[palavra], topn=200, pos=pos)
                sugestao = [sin for sin, pontuacao in res_tmp if sin in cands]

                if sugestao != [ ]:
                    predicao_final[lexelt] = sugestao
                elif saida_contigencial == True:
                    metodo = cfgs['saida_contig']['metodo']
                    predicao_final[lexelt] = alvaro.sugestao_contigencial(palavra,
                                                    pos, fontes_def,
                                                    metodo, frase, med_sim=med_sim)


            elif criterio == 'gabarito':
                # Este FOR indexa exemplos para a palavra
                for cand_iter in cands:
                    Alvaro.indexar_exemplos(cand_iter, pos)

                try:
                    Alvaro.indexar_exemplos(palavra, pos)

                    if Alvaro.PALAVRAS_EXEMPLOS_INDEXADOS != None:
                        dir_saida = Util.CONFIGS['corpora']['dir_palavras_indexadas_exemplos']
                        Util.salvar_json(dir_saida, list(Alvaro.PALAVRAS_EXEMPLOS_INDEXADOS))

                except Exception, e:
                    print("\n%s\n"%str(e))

                if gab_ordenado[0][0] in cands:
                    tokens_tagueados = nltk.pos_tag(nltk.word_tokenize(frase.lower()))
                    pos_uteis = ['N', 'J', 'V']
                    tokens_frase = [r[0] for r in tokens_tagueados if r[1][0] in pos_uteis and r[0] != palavra]

                    if palavra in tokens_frase:
                        tokens_frase.remove(palavra)

                    for t in list(tokens_frase):
                        if Util.singularize(t) != t:
                            tokens_frase.append(Util.singularize(t))

                    # Gerando pares de correlação
                    pares = list(set(list(itertools.product(*[tokens_frase, [palavra]]))))
                    pares = [reg for reg in pares if len(reg[0]) > 1 and len(reg[1]) > 1]

                    pontuacao_definicoes = { }

                    for par in pares:
                        token_frase, cand_par = par
                        indexes_ex = Whoosh.DIR_INDEXES_EXEMPLOS

                        obter_docs = Whoosh.consultar_documentos

                        if Util.singularize(token_frase) != Util.singularize(cand_par):
                            if not str(par) in Alvaro.FREQ_PMI:
                                docs_corpora = obter_docs(list(par), operador="AND", dir_indexes=Whoosh.DIR_INDEXES)
                                Alvaro.FREQ_PMI[str(par)] = len(docs_corpora)
                                frequencia_par = len(docs_corpora)
                                docs_corpora = None
                            else:
                                frequencia_par = Alvaro.FREQ_PMI[str(par)]

                            # Se o par ocorre no minimo uma vez...
                            if frequencia_par > 0:
                                token_frase, cand_par = par

                                if not token_frase in Alvaro.FREQ_PMI:
                                    docs_corpora_token = obter_docs([token_frase],
                                                                    operador="AND",
                                                                    dir_indexes=Whoosh.DIR_INDEXES)
                                    Alvaro.FREQ_PMI[token_frase] = len(docs_corpora_token)
                                    docs_corpora_token = None

                                if not cand_par in Alvaro.FREQ_PMI:
                                    docs_corpora_cand_par = obter_docs([cand_par],
                                                                    operador="AND",
                                                                    dir_indexes=Whoosh.DIR_INDEXES)
                                    Alvaro.FREQ_PMI[cand_par] = len(docs_corpora_cand_par)
                                    docs_corpora_cand_par = None

                                try:
                                    min_par = min(Alvaro.FREQ_PMI[cand_par],Alvaro.FREQ_PMI[token_frase])
                                    percentagem = float(frequencia_par)/float(min_par)
                                except:
                                    percentagem = 0.00

                                print("\n\n")
                                print((frase, palavra))
                                print("Frequencia NO CORPUS de '%s': %d"%(token_frase, Alvaro.FREQ_PMI[token_frase]))
                                print("Frequencia NO CORPUS de '%s': %d"%(cand_par, Alvaro.FREQ_PMI[cand_par]))
                                print("Porcentagem: " + str(percentagem) + "%")                            

                                if Alvaro.FREQ_PMI[token_frase] and Alvaro.FREQ_PMI[cand_par]:
                                    # Calculando PMI para palavras co-ocorrentes no Corpus
                                    pmi = Alvaro.pontwise_mutual_information(Alvaro.FREQ_PMI[token_frase],
                                                        Alvaro.FREQ_PMI[cand_par],
                                                        frequencia_par, Whoosh.DIR_INDEXES)
                                    print("PMI para '%s': %f"%(str(par), pmi))

                                    # Filtrando do corpus do dicionario documentos
                                    # referentes à definicao do candidato + POS tag
                                    docs_exemplos_tmp = obter_docs(list(par), dir_indexes=Whoosh.DIR_INDEXES_EXEMPLOS)
                                    docs_exemplos = [ ]

                                    for doc in docs_exemplos_tmp:
                                        if cand_par in doc['title'] and cand_par + '-' + pos in doc['path']:
                                            docs_exemplos.append(doc)

                                    docs_exemplos_tmp = None
                                else:
                                    docs_exemplos = [ ]

                                if docs_exemplos:
                                    for doc in docs_exemplos:
                                        if cand_par in doc['title'] and cand_par + '-' + pos in doc['path']:
                                            print('\n')
                                            print((cand_par, token_frase))
                                            print(doc['title'])
                                            print(doc['path'])
                                            print('\n')

                                            blob_ex = textblob.TextBlob(doc['content'])
        
                                            # Frequencia media
                                            fm_token_frase = Alvaro.tf(token_frase, blob_ex)/blob_ex.split(':::').__len__()
                                            f_token_frase = Alvaro.tf(token_frase, blob_ex)

                                            print("Frequencia media para '%s': %f"%(token_frase, fm_token_frase))
                                            print("Frequencia para '%s': %f"%(token_frase, f_token_frase))
                                            print("Score PMI x Frequencia: %f"%(f_token_frase * pmi))

                                            if not doc['title'] in pontuacao_definicoes:
                                                pontuacao_definicoes[doc['title']] = [ ]

                                            pontuacao_definicoes[doc['title']].append(f_token_frase * pmi)
                                else:
                                    print("Palavras %s nao sao relacionadas no dicionario!" % str(par))

                                docs_exemplos = None

                            if Util.CONFIGS['corpora']['deletar_docs_duplicados']:
                                # Usado para reconhecer documentos duplicados
                                # na indexacao e, posteriormente, deleta-los
                                set_docs_corpora = set()
                                paths_repetidos = set()
                                documentos_deletaveis = [ ]

                                try:
                                    for doc_iter in docs_corpora:
                                        if doc_iter['content'].__len__()  >  Util.CONFIGS['max_text_length']:
                                            md5_doc = Util.md5sum_string(doc_iter['content'])

                                            if not md5_doc in set_docs_corpora:
                                                set_docs_corpora.add(md5_doc)
                                            else:
                                                if not doc_iter['path'] in paths_repetidos:
                                                    documentos_deletaveis.append(Whoosh.buscar_docnum(doc_iter['path']))
                                                    paths_repetidos.add(doc_iter['path'])

                                    if documentos_deletaveis:
                                        Whoosh.remover_docs(documentos_deletaveis)

                                except Exception, e: pass
                            else:
                                docs_corpora = None

                                set_docs_corpora = None
                                paths_repetidos = None
                                documentos_deletaveis = None

                    pontuacao_definicoes_tmp = [ ]

                    for def_iter in pontuacao_definicoes:
                        pontuacao_definicoes_tmp.append((def_iter, Util.media(pontuacao_definicoes[def_iter])))

                    pontuacao_definicoes_tmp = Util.sort(pontuacao_definicoes_tmp, 1, reverse=True)

                    print("\nPontuacao definicoes baseadas em estatistica:".upper())
                    print((frase, palavra))
                    print(pontuacao_definicoes_tmp)
                    print("\n")

                    try:                        
                        melhor_score = pontuacao_definicoes_tmp[0][1]
                        cands_ordenados_estatisticamente = [d for (d, s) in pontuacao_definicoes_tmp if s == melhor_score]

                        cands_tmp = [ ]

                        for reg in cands_ordenados_estatisticamente:
                            lema, definicao = reg.split(':::')
                            sinonimos = BaseOx.obter_sins(BaseOx.INSTANCE, lema, definicao, pos)
                            for s in sinonimos:
                                if s in cands:
                                    cands_tmp.append(s)
                        for s in cands:
                            if not s in cands_tmp:
                                cands_tmp.append(s)

                        if pos in ['n', 'v']:
                            cands = list(cands_tmp)

                    except:
                        cands_ordenados_estatisticamente = [ ]

                #arvores = Alvaro.construir_arvore_definicoes(Alvaro.INSTANCE, palavra, pos, 4, cands)
                arvores = [ ]
                caminhos_arvore = [ ]

                for arvore_sinonimia in arvores:
                    for caminho in arvore_sinonimia.percorrer():
                        try:
                            cam_tmp = [tuple(reg.split(':::')) for reg in caminho.split("/")]
                            cam_tmp = [p for (p, def_p) in cam_tmp if p in cands or cands == [ ]]
                            conts_corretos = [1 for i in range(len(Counter(cam_tmp).values()))]
                            # Se todas palavras só ocorrem uma vez, entao nao existe ciclos
                            if Counter(cam_tmp).values() == conts_corretos:
                                if not caminho in caminhos_arvore:
                                    caminhos_arvore.append(caminho)

                        except ValueError, ve: pass
                    caminhos_wmd = Alvaro.pontuar_relacaosinonimia_wmd(Alvaro.INSTANCE,\
                                                            palavra, pos, caminhos_arvore)

                try:
                    qtde_sugestoes_oot = Util.CONFIGS['params_exps']['qtde_sugestoes_oot'][0]
                    predicao_final[lexelt] = [p for p in cands if len(p) > 1][:qtde_sugestoes_oot]
                except:
                    predicao_final[lexelt] = [ ]
               
                if Alvaro.PONDERACAO_DEFINICOES != None:
                    Alvaro.salvar_base_ponderacao_definicoes()


            elif criterio == 'substituicao_arvore':

                for def_iter in BaseOx.obter_definicoes(BaseOx.INSTANCE, palavra, pos=pos):
                    sinonimos = BaseOx.obter_sins(BaseOx.INSTANCE, palavra, def_iter, pos=pos)


            elif criterio == 'alvaro':
                dir_cache_rel_sinonimia = cfgs['caminho_bases']+'/'+cfgs['oxford']['cache']['sinonimia']

                obj_unificado = BaseOx.construir_objeto_unificado(base_ox, palavra)

                chave_cache_rel_sinonimia = "%s-%s.json"%(palavra, pos)
                dir_obj = dir_cache_rel_sinonimia+'/'+chave_cache_rel_sinonimia
              
                if not chave_cache_rel_sinonimia in Util.list_arqs(dir_cache_rel_sinonimia):
                    alvaro = Alvaro.INSTANCE
                    rel_defs = Alvaro.construir_relacao_definicoes(alvaro, palavra, pos, fontes='oxford')
                    Util.salvar_json(dir_obj, rel_defs)
                else:
                    rel_defs = Util.abrir_json(dir_obj, criarsenaoexiste=False)

                correlacao_definicoes = { }

                # Max sinonimos por definicao
                mxspdef = cfgs['alvaro']['mxspdef']
                idefp = 1

                for def_polissemica in rel_defs:
                    sins_relacionados = rel_defs[def_polissemica].keys()[:mxspdef]
                    if palavra in sins_relacionados: sins_relacionados.remove(palavra)
                    if len(sins_relacionados) > 1:
                        sins_relacionados = [sins_relacionados[0]]

                    isin = 1

                    for sinonimos_def in sins_relacionados:
                        idef = 1

                        for def_relacionada in rel_defs[def_polissemica][sinonimos_def]:
                            todos_exemplos = BaseOx.obter_atributo(base_ox,\
                                            sinonimos_def, pos, def_relacionada, 'exemplos')

                            if not todos_exemplos:
                                todos_exemplos = [ ]

                            todos_exemplos = todos_exemplos[:max_ex]
                            todos_exemplos.append(frase)

                            iex = 1
                            for ex in todos_exemplos:
                                ex = Util.completa_normalizacao(ex)

                                res_exemplo = DesOx.desambiguar(des_ox, ex, palavra, pos, nbest=True, med_sim=med_sim)
                                    
                                for reg, pontuacao in res_exemplo:
                                    # Definicao = Definicao polissemica
                                    label, d, exemplos_reg = reg
                                    if d == def_polissemica:
                                        chave_relacao = str((palavra, d, sinonimos_def, def_relacionada))
                                        if not chave_relacao in correlacao_definicoes:
                                            correlacao_definicoes[chave_relacao] = [ ]
                                        if ex == frase:
                                            if med_sim == 'cosine':
                                                correlacao_definicoes[chave_relacao].append(pontuacao)
                                            elif med_sim == 'word_move_distance':
                                                correlacao_definicoes[chave_relacao].append(pontuacao)

                                Util.cls()

                                print("\n\n@@@ Processando a entrada " + str(lexelt))
                                print("%s\n"%str((frase, palavra, pos)))
                                print("%d / %d"%(cont+1, len(interseccao_casos)))
                                print('Definicao polissemica %d/%d'%(idefp, len(rel_defs)))
                                print('Sinonimo relacionado %d/%d'%(isin, len(sins_relacionados)))
                                print('Definicao relacionada %d/%d'%(idef, len(rel_defs[def_polissemica][sinonimos_def])))
                                print('Sinonimo: ' + sinonimos_def + ' - ' + def_relacionada)
                                print('Indice exemplo %d/%d do par %s'%(iex, len(todos_exemplos), str((pos, def_relacionada))))
                                print('Exemplo: '+ex)                                
                                print('\n')
                              
                                iex += 1
                            idef += 1
                        isin += 1
                    idefp += 1

                correlacao_definicoes_ordenada = { }
                correlacao_definicoes = [(nome_tarefa, sum(v)/len(v)) for (nome_tarefa, v) in correlacao_definicoes.items() if len(v) > 0]
                correlacao_definicoes = sorted(correlacao_definicoes, key=lambda x: x[1], reverse=False)

                conj_predicao = set()

                try:
                    melhor_lema, melhor_definicao = eval(correlacao_definicoes[0][0])[:2]
                    nsins = BaseOx.obter_sins(melhor_lema, melhor_definicao, pos = pos)

                    # A partir do melhor significado
                    for s in nsins:
                        if s != palavra and not s in conj_predicao:
                            conj_predicao.add(s)
                    # A partir do melhor significado relacionado
                    for rdefs, pont in correlacao_definicoes:
                        l1, d1, l2, d2 = eval(rdefs)
                        if d1 == melhor_definicao:
                            nsins = BaseOx.obter_sins(l2, d2, pos = pos)
                            for s in nsins:
                                if s in conj_predicao:
                                    conj_predicao.add(s)

                    predicao_final[lexelt] = list(conj_predicao)[:Util.CONFIGS['params_exps']['qtde_sugestoes_oot']]
                except: 
                    predicao_final[lexelt] = [ ]

                print("Entrada: "+str(casos_testes_dict[lexelt]))
                print("Gabarito: "+str(gabarito_dict[lexelt]))
                print("Predicao: "+ str(predicao_final[lexelt]))

            # Metodo de Baseline
            elif criterio == 'word_move_distance':
                conj_predicao = [ ]
                resultado_wmd = { }

                for cand_iter in cands:
                    nova_frase = frase.replace(palavra, cand_iter)
                    pont = rep_vetorial.word_move_distance(frase, nova_frase)
                    if not pont in resultado_wmd:
                        resultado_wmd[pont] = [ ]
                    resultado_wmd[pont].append(cand_iter)

                for pont in sorted(resultado_wmd.keys(), reverse=False):
                    conj_predicao += resultado_wmd[pont]

                qtde_sugestoes_oot = Util.CONFIGS['params_exps']['qtde_sugestoes_oot'][0]
                predicao_final[lexelt] = [p for p in conj_predicao if len(p) > 1][:qtde_sugestoes_oot]


            elif criterio in ['desambiguador_exemplos', 'desambiguador']:
                mxspdef = cfgs['alvaro']['mxspdef']
                if criterio == 'desambiguador_exemplos':
                    res_des = DesOx.desambiguar_exemplos(des_ox, frase,\
                                    palavra, pos, profundidade=1, candidatos=cands)
                elif  criterio == 'desambiguador':
                    res_des = DesOx.desambiguar(des_ox, frase, palavra,\
                                    pos, med_sim=med_sim, cands=cands)
                    if med_sim == "cosine":
                        res_des = [(r, p) for (r, p) in res_des if p > 0.00] # (reg, pont)

                conj_predicao = [ ]

                for reg_def, pont in res_des:
                    label, defini, ex = reg_def

                    label = label.split(".")[0]
                    if label == palavra:
                        sins = BaseOx.obter_sins(base_ox, label, defini, pos=pos)
                    else:
                        sins = [label]

                    if sins == None: sins = [ ]

                    sins = [s for s in sins if not Util.e_mpalavra(s)][:mxspdef]
                    
                    sins = [p for p in list(set(sins)&set(cands)) if Util.e_mpalavra(p) == False]
                    for s in sins:
                        if not s in conj_predicao:
                            conj_predicao.append(s)

                predicao_final[lexelt] = conj_predicao

            if lexelt in predicao_final:
                tam_sugestao = len(predicao_final[lexelt])
                t = (lexelt, tam_sugestao, str(predicao_final[lexelt][:qtde_sugestoes_oot]))
                print("\nLexelt %s recebeu a sugestao (%d) %s\n"%t)
                print("Gabarito: %s"%str(gab_ordenado))
            elif saida_contigencial == True:
                metodo = cfgs['saida_contig']['metodo']
                predicao_final[lexelt] = alvaro.sugestao_contigencial(palavra,\
                                pos, fontes_def, metodo, frase, med_sim=med_sim)

                try:
                    qtde_sugestoes_oot = Util.CONFIGS['params_exps']['qtde_sugestoes_oot'][0]
                    t = (lexelt, str(predicao_final[lexelt][:qtde_sugestoes_oot]), metodo.upper())
                    print("\nLexelt %s recebeu a sugestao CONTIGENCIAL '%s' com o metodo '%s'\n"%t)
                    print("Gabarito: %s"%str(gab_ordenado))
                except: pass

            if cont + 1 < len(indices_lexelts):
                prox_lexelt = todos_lexelts[cont+1]
                prox_palavra = prox_lexelt.split(".")[0]
                if palavra != prox_palavra:
                    BaseOx.objs_unificados = None
                    BaseOx.objs_unificados = { }

            if Alvaro.PONDERACAO_DEFINICOES != None:
                Util.salvar_json("../Bases/ponderacao_definicoes.json", Alvaro.PONDERACAO_DEFINICOES)

        print("\n\n\n\n\n\n\n")

    #Util.salvar_json(dir_obj_candidatos, obj_candidatos)

    # Para o Garbage Collector
    cache_rel_sinonimia=None
    cache_seletor_candidatos=None
    cache_resultado_desambiguador=None

    # Remover predicoes falhas
    predicao_final_copia=dict(predicao_final)

    for reg in predicao_final:
        if predicao_final[reg] in [[ ], ""]:
            del predicao_final_copia[reg]

    predicao_final=dict(predicao_final_copia)

    # Predicao, caso de entrada, gabarito
    return predicao_final, casos_testes_dict, gabarito_dict, obj_candidatos


def testar_indexes():
    from Indexador import Whoosh
    for doc in Whoosh.consultar_documentos(['heap'], operador="AND", dir_indexes=Whoosh.DIR_INDEXES_EXEMPLOS):
        print("\n")
        print(doc['title'])
        print(doc['path'])
        print(doc['content'])
        print("\n-------------------")

    #paths = [ ]
    #for doc in Whoosh.documentos():
    #    if 'SignalMedia' in doc['path']:
     #       paths.append(doc['path'])

    #docnums = [ ]
    #for path in paths:
    #    dn = Whoosh.buscar_docnumer_bypath(path)
    #    raw_input(dn)
    #    docnums.append(dn)
        

    #Whoosh.remover_doc(docnums)
    #print("Deletando...")
    #print(Whoosh.deletar_bypattern('path', '*SignalMedia*'))
    #print("Deletando!")

    #for doc in Whoosh.documentos():
    #    if 'SignalMedia' in doc['path']:
    #        print(doc)

    #Whoosh.iniciar_indexacao_signalmedia("/mnt/ParticaoAlternat/Bases/Corpora/SignalMedia/alguns_arquivos.txt")
    exit(0)


def aplicar_abordagens(cfgs):
    Util.verbose_ativado = False
    Util.cls()

    params_exps = cfgs['params_exps']

    Util.CONFIGS = cfgs

    app_cfg = Util.abrir_json("./keys.json")
    Util.CONFIGS['oxford']['app_id'] = app_cfg['app_id']
    Util.CONFIGS['oxford']['app_key'] = app_cfg['app_key']

    InterfaceBases.setup(cfgs)
    rep_vet = RepVetorial.INSTANCE

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

    pos_avaliadas = params_exps['pos_avaliadas'] if params_exps['pos_avaliadas'] else [None]
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
    caminho_raiz_semeval = "%s/%s"%(caminho_bases, cfgs_se["dir_raiz"])
    path_base_teste = "%s/%s"%(caminho_raiz_semeval, cfgs_se["test"]["input"])

    casos_filtrados_tmp = vldr_se.carregar_caso_entrada(path_base_teste, padrao_se=True)
    contadores = dict([(pos, 0) for pos in cfgs_se['todas_pos']])
    lexelts_filtrados = [ ]

    for lexelt in casos_filtrados_tmp:
        pos_tmp = re.split('[\s\.]', lexelt)[1]  # 'war.n 0' => ('war', 'n', 0)
        if contadores[pos_tmp] < max_indice_pos:
            lexelts_filtrados.append(lexelt)
            contadores[pos_tmp] += 1
    # Fim do filtro de casos de entrada por lexelt

    lf = lexelts_filtrados
    res_best = vldr_se.aval_parts_orig('best', pos_filtradas=pos_avaliadas[0], lexelts_filtrados=lf).values()
    res_oot = vldr_se.aval_parts_orig('oot', pos_filtradas=pos_avaliadas[0], lexelts_filtrados=lf).values()

    cfg_ngram_ox = cfgs['ngram']['dir_exemplos']

    ch_ngram_plain = cfg_ngram_ox['oxford_plain']
    ch_ngram_tagueados = cfg_ngram_ox['oxford_tagueados']

    Alvaro.FREQ_PMI = Util.abrir_json(cfgs['corpora']['contadores_pmi'], criarsenaoexiste=False)

    for parametros in parametrizacao:
        crit, max_ex, fontes_def, tipo, usr_gab, usr_ex, pos_avaliadas = parametros

        if type(pos_avaliadas) != list:
            raise Exception("\n\nAs POS avaliadas devem ser expressas no formato de list!\n\n")

        predicao = set()
        casos = set()
        gabarito = set()

        exe = "realizar_predicao"

        if exe == "realizar_predicao":
            try:
                pred_saida = predizer_sins(
                    cfgs,\
                    lexelts_filtrados=lexelts_filtrados,\
                    usar_gabarito=False,\
                    criterio=crit,\
                    tipo=tipo,\
                    max_ex=max_ex,\
                    usr_ex=usr_ex,\
                    fontes_def=fontes_def,\
                    pos_avaliadas=pos_avaliadas,\
                    rep_vetorial=rep_vet)

                predicao, casos, gabarito, candidatos = pred_saida

            except Exception, e:
                import traceback
                print("\n")
                print(e)
                print("\n")
                traceback.print_stack()
                print("\n%s\n" % str(e))

                if Alvaro.FREQ_PMI != None:
                    Util.salvar_json(cfgs['corpora']['contadores_pmi'], Alvaro.FREQ_PMI)
                    Alvaro.FREQ_PMI = None
                    print("\nPMI salvo!\n")

                if Alvaro.PONDERACAO_DEFINICOES != None:
                    print("\nSalvando relacao entre sinonimos pontuadas via-WMD!\n")
                    Alvaro.salvar_base_ponderacao_definicoes()

        elif not exe == 'f':            
            print("\n\nOpcao invalida!\nAbortando execucao...\n\n")
            exit(0)

        if Alvaro.FREQ_PMI != None:
            Util.salvar_json(cfgs['corpora']['contadores_pmi'], Alvaro.FREQ_PMI)
            Alvaro.FREQ_PMI = None
            print("\nPMI salvo!\n")

        # GERANDO SCORE
        for cont in qtde_sugestoes_oot:
            nome_abrdgm = cfgs['padrao_nome_submissao']  # '%d-%s-%s ... %s'
            nome_abrdgm = nome_abrdgm%(crit, usr_gab, tipo, max_ex, usr_ex, fontes_def, 'oot')

            vldr_se.formtr_submissao(dir_saida_abrdgm+"/"+nome_abrdgm, predicao, None, cont, ":::")

            print("\nSaida da sua abordagem: "+dir_saida_abrdgm+"/"+nome_abrdgm+"\n")

            if Util.arq_existe(dir_saida_abrdgm, nome_abrdgm):
                try:
                    res_oot.append(vldr_se.obter_score(dir_saida_abrdgm, nome_abrdgm))
                except Exception, reg:
                    print("\n@@@ Erro na geracao do score da abordagem '%s'"%nome_abrdgm+"\n")

        nome_abrdgm = cfgs['padrao_nome_submissao']
        nome_abrdgm = nome_abrdgm%(crit, usr_gab, tipo, max_ex, usr_ex, fontes_def, 'best')

        print("Saida da sua abordagem: "+dir_saida_abrdgm+"/"+nome_abrdgm)
        vldr_se.formtr_submissao(dir_saida_abrdgm+"/"+nome_abrdgm, predicao, None, 10, "::")

        if Util.arq_existe(dir_saida_abrdgm, nome_abrdgm):
            try:
                res_best.append(vldr_se.obter_score(dir_saida_abrdgm, nome_abrdgm))
            except:
                print("\n@@@ Erro na geracao do score da abordagem '%s'"%nome_abrdgm)


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

        Util.salvar_json("%s/%s.%s"%(diretorio_saida_json, nome_tarefa.upper(), nome_tarefa), res_tarefa)
        print("\n" + chave.upper() + "\t-----------------------")

        for reg in res_tarefa:
            print(reg['nome'])
            etmp = dict(reg)
            del etmp['nome']
            print(etmp)
            print('\n')

        print("\n")


if __name__ == '__main__':
    if len(argv) < 2:
        print('\nParametrizacao errada!\nTente py ./main <dir_config_file>\n\n')
        exit(0)
    elif argv[2] == 'aplicar':
        cfgs = Util.carregar_cfgs(argv[1])
        aplicar_abordagens(cfgs)
    elif argv[2] == 'indexar':
        lista_arqs = "../Bases/Corpora/SignalMedia/arquivos.txt"
        textos_repetidos = "../Bases/Corpora/SignalMedia/textos_repetidos.txt"

        Whoosh.iniciar_indexacao_signalmedia(lista_arqs, textos_repetidos)
    elif argv[2] == 'extrair':
        from ExtratorWikipedia import ExtratorWikipedia
        cfgs = Util.carregar_cfgs(argv[1])
        ext = ExtratorWikipedia(cfgs)

        print(ext.obter_texto("https://en.wikipedia.org/wiki/Leading_actor"))

    print('\n\n\n\nFim do __main__\n\n\n\n')
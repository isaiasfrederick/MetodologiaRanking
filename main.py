#! coding: utf-8
from InterfaceBases import InterfaceBases
from statistics import mean as media
from operator import itemgetter
from Utilitarios import Util
from SemEval2007 import *
from sys import argv
import statistics
import itertools
import traceback
import re
import sys

# Experimentacao
from DesambiguadorWordnet import DesWordnet
from OxAPI import CliOxAPI, BaseOx, ExtWeb
from DesOx import DesOx
from RepresentacaoVetorial import RepVetorial
from nltk.corpus import wordnet
# Fim pacotes da Experimentacao

# Testar Abordagem Alvaro
from Alvaro import AbordagemAlvaro
from CasadorManual import CasadorManual
from textblob import TextBlob
import signal

wn = wordnet

def wmd(cfgs):
    rep_vetorial = RepVetorial.REP

    txt1 = "A road vehicle, typically with four wheels, powered by an internal combustion engine and able to carry a small number of people"
    txt2 = ""

    d = 'a self-propelled wheeled vehicle that does not run on rails'

    for txt2 in [s.definition() for s in wn.synsets('car', 'n')]+[d]:
        score = rep_vetorial.word_move_distance(txt1, txt2)

        print('1.'+str(txt1))
        print('2.'+str(txt2))
        print('\n=> SCORE: '+str(score))
        print("\n\n")


def avaliar_des(cfgs, fonte='wordnet'):
    validador = VlddrSemEval(cfgs)
    des_wn = DesWordnet(cfgs)

    des_babelfy = DesBabelfy(cfgs, BaseOx.BASE_OX)

    casos_testes_dict, gabarito_dict = carregar_bases(
        cfgs, raw_input("\n\nDigite a base> "))
    palavras = set()

    alvaro = AbordagemAlvaro.ABORDAGEM

    for lexelt in set(casos_testes_dict.keys()) & set(gabarito_dict.keys()):
        p = lexelt.split(".")[0]
        palavras.add(p)

    for lexelt in set(casos_testes_dict.keys()) & set(gabarito_dict.keys()):
        frase, palavra, pos = casos_testes_dict[lexelt]
        frase = Util.descontrair(frase).replace("  ", " ")
        palavra = lexelt.split(".")[0]

        if palavra in palavras:
            if not 'HEROES' in frase:
                nfrase = str(frase).replace(palavra, "(%s)" % palavra)
                nfrase = frase
                Util.print_formatado("%s" % frase)
                Util.print_formatado("Palavra: "+palavra)
                Util.print_formatado("POS: "+pos)
                Util.print_formatado("Resposta: " +
                      str(validador.fltr_gabarito(gabarito_dict[lexelt])))
                raw_input("<enter>\n\n\n")


def utilizar_word_embbedings(configs, usar_exemplos=True, usar_hiperonimo=True, fonte='wordnet'):
    base_ox = BaseOx.BASE_OX
    rep_vetorial = RepVetorial.REP

    while raw_input("\nContinuar? S/n: ").lower() != 'n':
        palavra = raw_input("Palavra: ")

        if fonte == 'oxford':
            todas_definicoes = base_ox.obter_definicoes(palavra)
        elif fonte == 'wordnet':
            todas_definicoes = wn.synsets(palavra)

        for definicao in todas_definicoes:
            entrada = [ ]
            todos_lemas = [ ]

            if fonte == 'oxford':
                todos_lemas = base_ox.obter_sins(palavra, definicao)
            elif fonte == 'wordnet':
                todos_lemas = definicao.lemma_names()  # Synset

            for lema in todos_lemas:
                if fonte == 'wordnet':
                    entrada += lema.split('_')
                elif fonte == 'oxford':
                    entrada += lema.split(' ')

            exemplos, hiperonimo = [ ], [ ]

            if fonte == 'oxford':
                exemplos = base_ox.obter_atributo(
                    palavra, None, definicao, 'exemplos')
                hiperonimo = [ ]
            elif fonte == 'wordnet':
                exemplos = definicao.examples()
                for lema in definicao.hypernyms()[0].lemma_names():
                    hiperonimo += lema.split('_')

            entrada += hiperonimo

            if usar_exemplos and False:
                for ex in exemplos:
                    entrada += ex.split(' ')

            entrada = list(set(entrada))
            palavras = rep_vetorial.obter_palavras_relacionadas(
                positivos=entrada, topn=30)


""" Este metodo testa a abordagem do Alvaro em carater investigativo
sobre o componente que escolhe os sinonimos a serem utilizados """
def avaliar_seletor(cfgs):
    validador = VlddrSemEval(cfgs)
    contadores = Util.abrir_json(cfgs['leipzig']['dir_contadores'])

    pos_avaliadas = ["n"]
    fontes = ['oxford', 'wordnet', 'wordembbedings']

    tarefa = raw_input("\n\nQual a tarefa? 'best' ou 'oot'? ")

    dir_saida_seletor_candidatos = "/home/isaias/saida-oot.oot"

    rep_vet = RepVetorial.REP
    rep_vet.carregar_modelo(diretorio='../Bases/'+cfgs['modelos']['default'])

    base_ox = BaseOx.BASE_OX
    alvaro = AbordagemAlvaro.ABORDAGEM

    definicoes_ordenadas = dict()

    bases_utilizadas = raw_input("Base: 'trial' ou 'test': ")
    dir_gabarito = cfgs['semeval2007'][bases_utilizadas]['gold_file']
    dir_entrada = cfgs['semeval2007'][bases_utilizadas]['input']

    gabarito_tmp = validador.carregar_gabarito("../Bases/SemEval2007/"+dir_gabarito)
    casos_testes_list, gabarito_list = [ ], [ ]

    gabarito_dict = dict()

    for lexelt in gabarito_tmp:
        lista = [ ]
        for sugestao in gabarito_tmp[lexelt]:
            voto = gabarito_tmp[lexelt][sugestao]
            lista.append([sugestao, voto])
        gabarito_list.append(lista)
        gabarito_dict[lexelt] = lista

    gabarito_tmp = None
    casos_testes_tmp = validador.carregar_caso_entrada("../Bases/SemEval2007/"+dir_entrada)
    casos_testes_dict = { }

    for lexema in casos_testes_tmp:
        for registro in casos_testes_tmp[lexema]:
            frase = registro['frase']
            palavra = registro['palavra']
            pos = lexema.split(".")[1]
            if pos in pos_avaliadas:
                casos_testes_list.append([frase, palavra, pos])
                nova_chave = "%s %s"%(lexema, registro['codigo'])
                casos_testes_dict[nova_chave] = [frase, palavra, pos]

    casos_testes_list, gabarito_list, lexemas_list = [ ], [ ], [ ]
    resultados_persistiveis = [ ]

    for lexema in casos_testes_dict:
        if lexema in casos_testes_dict and lexema in gabarito_dict:
            casos_testes_list.append(casos_testes_dict[lexema])
            gabarito_list.append(gabarito_dict[lexema])
            lexemas_list.append(lexema)

    total_com_resposta = 0
    total_sem_resposta = 0

    total_candidatos = [ ]
    lexema_candidatos = dict()

    for indice in range(len(gabarito_list)):
        if alvaro.possui_moda(gabarito_list[indice]) == True:
            candidatos = [reg[0] for reg in gabarito_list[indice]]
            contexto, palavra, pos = casos_testes_list[indice]
            palavra = palavra.lower()

            resultados_persistiveis.append(indice)
            # Extraindo candidatos que a abordagem do Alvaro escolhe atraves de dicionarios
            cands_selec_alvaro = alvaro.selec_candidatos(palavra, pos, max_por_def=4, fontes=fontes)

            try:
                p_relacionadas = rep_vet.obter_palavras_relacionadas(positivos=[palavra], pos=pos, topn=200)
                candidatos_embbedings = [p[0] for p in p_relacionadas]
            except:
                candidatos_embbedings = list(cands_selec_alvaro)

            #candidatos_selecionados_alvaro = list(set(candidatos_embbedings)&set(candidatos_selecionados_alvaro))

            total_candidatos.append(len(cands_selec_alvaro))
            cands_selec_alvaro = list(set(cands_selec_alvaro))
            cands_selec_alvaro = [p for p in cands_selec_alvaro if not Util.e_mpalavra(p)]
            cands_selec_alvaro = [p for p in cands_selec_alvaro if not '_' in p]

            # Respostas certas baseada na instancia de entrada
            gabarito_ordenado = sorted(gabarito_list[indice], key=lambda x: x[1], reverse=True)
            gabarito_ordenado = [reg[0] for reg in gabarito_ordenado]

            print("\nCASO ENTRADA: \n" + str((contexto, palavra, pos)))
            print("\nRESPOSTAS CORRETAS:\n\n%s" % str(gabarito_ordenado))

            if False:
                for c in set(cands_selec_alvaro):
                    for def_candidato in base_ox.obter_definicoes(c, pos=pos):
                        dist = rep_vet.word_move_distance(def_candidato, contexto)
                        sins = base_ox.obter_sins(c, def_candidato, pos=pos)
                        definicoes_ordenadas[dist] = (c + cfgs['separador'] + def_candidato, sins)
                for pontuacao in sorted(definicoes_ordenadas.keys(), reverse=False):
                    dfs, sins = definicoes_ordenadas[pontuacao]
                    print("%s\t-\t%s"%((str(pontuacao), dfs)))
                    print(sins)
                    print("\n")

            intersecao_tmp = list(set([gabarito_ordenado[0]]) & set(cands_selec_alvaro))
            lexema_candidatos[lexemas_list[indice]] = set(cands_selec_alvaro)

            print("\nINTERSECAO: %s" % str(intersecao_tmp))
            print("\nTOTAL SELECIONADO: " + str(len(cands_selec_alvaro)))
            print("\nCANDIDATOS: " + str(cands_selec_alvaro))

            if intersecao_tmp:
                total_com_resposta += 1
            else:
                total_sem_resposta += 1

            print("\n\n")

    arquivo_saida = open(dir_saida_seletor_candidatos, "w")

    for indice in resultados_persistiveis:
        # [['crazy', 3], ['fast', 1], ['very fast', 1], ['very quickly', 1], ['very rapidly', 1]]
        if tarefa == 'best':
            sugestoes = sorted(
                gabarito_list[indice], key=lambda x: x[1], reverse=True)[:1]
            sugestoes = [reg[0] for reg in sugestoes]
        elif tarefa == 'oot':
            sugestoes = sorted(
                gabarito_list[indice], key=lambda x: x[1], reverse=True)
            sugestoes = [[reg[0] for reg in sugestoes][0]]

            for s in lexema_candidatos[lexemas_list[indice]]:
                if not s in sugestoes:
                    sugestoes.append(s)

        arquivo_saida.write("%s %s %s\n" % (
            lexemas_list[indice], "::" if tarefa == 'best' else ":::", ";".join(sugestoes)))

    # Persistindo casos de entrada sem resposta corretamente
    for lexema in set(casos_testes_tmp.keys()) - set(lexemas_list):
        arquivo_saida.write(lexema + " ::\n")

    arquivo_saida.close()

    print("\n\nTotal com resposta: " + str(total_com_resposta))
    print("Total sem resposta: " + str(total_sem_resposta))
    f = float(float(total_com_resposta) / float(total_com_resposta+total_sem_resposta))
    print("Percentagem: %s"%(str(f)))


def carregar_bases(cfgs, tipo_base, pos_avaliadas=None):
    if pos_avaliadas in [None, [ ]]:
        pos_avaliadas = cfgs['semeval2007']['todas_pos']

    casos_testes = gabarito = None
    validador = VlddrSemEval(cfgs)

    # Carrega a base Trial para fazer os testes
    dir_bases_se = cfgs['caminho_raiz_bases']+'/'+cfgs['semeval2007']['dir_raiz']
    dir_gabarito = dir_bases_se+'/'+cfgs['semeval2007'][tipo_base]['gold_file']
    dir_entrada = dir_bases_se+'/'+cfgs['semeval2007'][tipo_base]['input']

    gabarito = validador.carregar_gabarito(dir_gabarito)
    casos_testes = validador.carregar_caso_entrada(dir_entrada)
    # gabarito_dict[lexelt cod] = [[palavra votos], [palavra votos], [palavra votos], ...]
    # casos_testes_dict[lexema cod] = [frase, palavra, pos]
    casos_testes_dict, gabarito_dict = {}, {}

    # Filtrando lexelts por chave
    chaves_casos_testes = [ ]
    for lexelt_parcial in casos_testes:
        for reg in casos_testes[lexelt_parcial]:
            chaves_casos_testes.append("%s %s" % (lexelt_parcial, reg['codigo']))
    todos_lexelts = set(chaves_casos_testes) & set(gabarito)
    todos_lexelts = [l for l in todos_lexelts if re.split('[\.\s]', l)[1] in pos_avaliadas]

    for lexelt in todos_lexelts:
        lista = [ ]
        for sugestao in gabarito[lexelt]:
            voto = gabarito[lexelt][sugestao]
            lista.append([sugestao, voto])
        gabarito_dict[lexelt] = lista

    for lexelt_iter in todos_lexelts:
        lexelt = lexelt_iter.split(" ")[0]  # 'scrap.n 104' => 'scrap.n'
        for registro in casos_testes[lexelt]:
            palavra, frase = registro['palavra'], registro['frase']
            pos = lexelt.split(".")[1]
            nova_chave = "%s %s" % (lexelt, registro['codigo'])
            casos_testes_dict[nova_chave] = [frase, palavra, pos]

    # Recomeçando as variaveis
    casos_testes, gabarito = [ ], [ ]

    for lexelt in casos_testes_dict:
        if lexelt in gabarito_dict:
            casos_testes.append(casos_testes_dict[lexelt])
            gabarito.append(gabarito_dict[lexelt])

    return casos_testes_dict, gabarito_dict


def avaliar_desambiguador(cfgs, fonte='oxford'):
    casador_manual = CasadorManual(cfgs)
    base_ox = BaseOx.BASE_OX
    alvaro = AbordagemAlvaro.ABORDAGEM

    casos_testes_dict, gabarito_dict = carregar_bases(cfgs, "test")

    contador_instancias_validas = 0
    contador_instancias_invalidas = 0

    for lexelt in set(casos_testes_dict.keys()) & set(gabarito_dict.keys()):
        frase, palavra, pos = casos_testes_dict[lexelt]
        frase = Util.descontrair(frase).replace("  ", " ")
        palavra = lexelt.split(".")[0]

        if fonte == 'oxford':
            des_ox = DesOx(cfgs, base_ox)
            res_des = des_ox.desambiguar(
                frase, palavra, pos, nbest=True, usr_ex=True)
            contador_instancias_validas += int(
                bool(sum([reg[1] for reg in res_des])))
        elif fonte == 'wordnet':
            des_wn = DesWordnet(cfgs)
            contador_instancias_validas += int(bool(
                sum([reg[1] for reg in des_wn.cosine_lesk(frase, palavra, pos, nbest=True)])))
        print("\n\nRESULTADO: " + str(contador_instancias_validas))

# Este metodo usa a abordagem do Alvaro sobre as bases do SemEval
# Ela constroi uma relacao (score) entre diferentes definicoes, possivelmente sinonimos
#   criterio = frequencia OU alvaro OU embbedings


def predizer_sins(cfgs,
                  criterio='frequencia',
                  usar_gabarito=True,
                  lexelts_filtrados=None,
                  fontes_def='oxford', tipo=None,
                  max_ex=-1, usr_ex=False,
                  pos_avaliadas=None,
                  rep_vetorial=None):

    dir_obj_candidatos = cfgs['caminho_raiz_bases']+'/'+cfgs['arquivo_candidatos']

    separador = cfgs['separador']
    obj_candidatos = Util.abrir_json(dir_obj_candidatos, criar=True)

    if fontes_def != 'oxford':
        raise Exception("Esta fonte de definicoes nao é contem exemplos...")

    if pos_avaliadas in [None, [ ]]:
        pos_avaliadas = cfgs['semeval2007']['todas_pos']
    if type(pos_avaliadas) != list:
        raise Exception("\n\nAs POS avaliadas devem ser uma list!\n\n")

    # Construtor com carregador de modelo
    dir_modelo = "%s/%s" % (cfgs['caminho_raiz_bases'],
                            cfgs['modelos']['default'])
    rep_vet = RepVetorial.REP

    casador_manual = None
    base_ox = BaseOx.BASE_OX
    alvaro = AbordagemAlvaro.ABORDAGEM

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

    for cont in indices_lexelts:
        lexelt = todos_lexelts[cont]
        frase, palavra, pos = casos_testes_dict[lexelt]
        frase = Util.descontrair(frase).replace("  ", " ")
        palavra = lexelt.split(".")[0]

        if not palavra in palavras_invalidas:
            chave_seletor_candidatos = str((palavra, pos))

            if not chave_seletor_candidatos in cache_seletor_candidatos:
                if usar_gabarito == True:
                    cands = [e[0] for e in gabarito_dict[lexelt] if not Util.e_mpalavra(e[0])]
                else:
                    cands = alvaro.selec_candidatos(palavra, pos, fontes=fontes_cands)
                    cands = [p for p in cands if p.istitle() == False]
            else:
                cands = cache_seletor_candidatos[chave_seletor_candidatos]

            cands = [p for p in cands if not Util.e_mpalavra(p)]

            if not palavra+'#'+pos in obj_candidatos:
                obj_candidatos[palavra+'#'+pos] = cands

            interseccao_casos = list(set(casos_testes_dict_tmp)&set(gabarito_dict.keys()))

            print("\n\n@@@ Processando a entrada " + str(lexelt))
            print("%d / %d"%(cont+1, len(interseccao_casos)))
            print("*** %s\n"%str((frase, palavra, pos)))
            print("Gabarito: %s"%str(sorted(gabarito_dict[lexelt], key=lambda x: x[1], reverse=True)))

            med_sim = cfgs['medida_similaridade_padrao']

            # filtrando por POS-tag
            if criterio == 'embbedings':
                res_tmp = rep_vet.obter_palavras_relacionadas(positivos=[palavra], topn=200, pos=pos)
                sugestao = [sin for sin, pontuacao in res_tmp if sin in cands]

                if sugestao != [ ]:
                    predicao_final[lexelt] = sugestao
                elif eval(cfgs['saida_contig']['habilitar']) == True:
                    metodo = cfgs['saida_contig']['metodo']
                    predicao_final[lexelt] = alvaro.sugestao_contigencial(palavra,
                                                    pos, fontes_def,
                                                    metodo, frase, med_sim=med_sim)
            elif criterio == 'alvaro':
                dir_cache_rel_sinonimia = cfgs['caminho_raiz_bases']+'/'+cfgs['oxford']['cache']['sinonimia']

                obj_unificado = base_ox.construir_objeto_unificado(palavra)

                chave_cache_rel_sinonimia = "%s-%s.json"%(palavra, pos)
                dir_obj = dir_cache_rel_sinonimia+'/'+chave_cache_rel_sinonimia

                if not chave_cache_rel_sinonimia in Util.list_arqs(dir_cache_rel_sinonimia):
                    #print("\n- Objeto de relacao de sinonimia para '%s' sera criado!\n"%palavra)
                    rel_defs = alvaro.construir_relacao_definicoes(palavra, pos, fontes='oxford')
                    #print("\n- Objeto de relacao de sinonimia para '%s' fora criado!\n"%palavra)
                    Util.salvar_json(dir_obj, rel_defs)
                else:
                    rel_defs = Util.abrir_json(dir_obj, criar=False)
                    #print("\n- Objeto de relacao de sinonimia para '%s' ja existia e foi aberto!\n"%palavra)

                correlacao_definicoes = { }

                # Max sinonimos por definicao
                mxspdef = cfgs['alvaro']['mxspdef']
                rel_defs = {  }
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
                            todos_exemplos = base_ox.obter_atributo(sinonimos_def,
                                                            pos, def_relacionada, 'exemplos')

                            if not todos_exemplos:
                                todos_exemplos = [ ]

                            todos_exemplos = todos_exemplos[:max_ex]
                            todos_exemplos.append(frase)

                            iex = 1
                            for ex in todos_exemplos:
                                ex = Util.remover_acentos(ex)

                                res_exemplo = des_ox.desambiguar(ex, palavra, pos, nbest=True, med_sim=med_sim)
                                    
                                for reg, pontuacao in res_exemplo:
                                    # Definicao = Definicao polissemica
                                    label, definicao, exemplos_reg = reg
                                    if definicao == def_polissemica:
                                        chave_relacao = str((palavra, definicao, sinonimos_def, def_relacionada))
                                        if not chave_relacao in correlacao_definicoes:
                                            correlacao_definicoes[chave_relacao] = [ ]
                                        if ex == frase:
                                            if med_sim == 'cosine':
                                                correlacao_definicoes[chave_relacao].append(pontuacao*4)
                                            elif med_sim == 'word_move_distance':
                                                correlacao_definicoes[chave_relacao].append(pontuacao/4)

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
                correlacao_definicoes = [(k, sum(v)/len(v)) for (k, v) in correlacao_definicoes.items() if len(v) > 0]
                correlacao_definicoes = sorted(correlacao_definicoes, key=lambda x: x[1], reverse=False)

                conj_predicao = set()

                try:
                    melhor_lema, melhor_definicao = eval(correlacao_definicoes[0][0])[:2]
                    nsins = base_ox.obter_sins(melhor_lema, melhor_definicao, pos = pos)

                    # A partir do melhor significado
                    for s in nsins:
                        if s != palavra and not s in conj_predicao:
                            conj_predicao.add(s)
                    # A partir do melhor significado relacionado
                    for rdefs, pont in correlacao_definicoes:
                        l1, d1, l2, d2 = eval(rdefs)
                        if d1 == melhor_definicao:
                            nsins = base_ox.obter_sins(l2, d2, pos = pos)
                            for s in nsins:
                                if s in conj_predicao:
                                    conj_predicao.add(s)

                    predicao_final[lexelt] = list(conj_predicao)[:10]
                except: 
                    predicao_final[lexelt] = [ ]

                print("Entrada: "+str(casos_testes_dict[lexelt]))
                print("Gabarito: "+str(gabarito_dict[lexelt]))
                print("Predicao: "+ str(predicao_final[lexelt]))

            # Metodo de Baseline
            elif criterio == 'wmd':
                conj_predicao = [ ]
                resultado_wmd = { }

                for c in cands:
                    nova_frase = frase.replace(palavra, c)
                    pont = rep_vetorial.word_move_distance(frase, nova_frase)
                    resultado_wmd[pont] = c
                for pont in sorted(resultado_wmd.keys(), reverse=False):
                    conj_predicao.append(resultado_wmd[pont])

                predicao_final[lexelt] = conj_predicao[:10]

            elif criterio == 'desambiguador':
                med_sim = cfgs['medida_similaridade_padrao']

                res_des = des_ox.desambiguar_exemplos(frase, palavra, pos, profundidade=1)
                conj_predicao = [ ]

                for reg_def, pont in res_des:
                    label, defini, ex = reg_def
                    sins = base_ox.obter_sins(palavra, defini, pos=pos)
                    if sins == None: sins = [ ]

                    for s in sins:
                        if not s in conj_predicao and Util.e_mpalavra(s) == False:
                            conj_predicao.append(s)

                predicao_final[lexelt] = conj_predicao

            elif criterio == 'frequencia':
                cliente_ox = CliOxAPI(cfgs)

                cands_ponts = [ ]
                for sin in cands:
                    try:
                        cands_ponts.append((sin, cliente_ox.obter_frequencia(sin)))
                    except Exception, e:
                        cands_ponts.append((sin, -1))

                res_predicao = [reg[0] for reg in sorted(cands_ponts, key=lambda x:x[1], reverse=True)]
                predicao_final[lexelt] = res_predicao


            if lexelt in predicao_final:
                tam_sugestao = len(predicao_final[lexelt])
                t = (lexelt, tam_sugestao, str(predicao_final[lexelt][:10]))
                print("Lexelt %s recebeu a sugestao (%d) %s\n"%t)
            elif eval(cfgs['saida_contig']['habilitar']) == True:
                metodo = cfgs['saida_contig']['metodo']
                predicao_final[lexelt] = alvaro.sugestao_contigencial(palavra, pos, fontes_def, metodo, frase, med_sim=med_sim)
                try:
                    t = (lexelt, str(predicao_final[lexelt][:10]), metodo.upper())
                    print("Lexelt %s recebeu a sugestao CONTIGENCIAL '%s' com o metodo '%s'\n"%t)
                except: pass

            if cont+1 < len(indices_lexelts):
                prox_lexelt = todos_lexelts[cont+1]
                prox_palavra = prox_lexelt.split(".")[0]
                if palavra != prox_palavra:
                    BaseOx.objs_unificados = None
                    BaseOx.objs_unificados = { }

    Util.salvar_json(dir_obj_candidatos, obj_candidatos)

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
    return predicao_final, casos_testes_dict, gabarito_dict


def testar_caso_(cfgs, tipo, pos_avaliadas=['a','n','r','v']):
    casos_testes_dict, gabarito_dict = carregar_bases(cfgs, tipo, pos_avaliadas=pos_avaliadas)

    casos_testes_dict_tmp = list(casos_testes_dict.keys())

    todos_lexelts = list(set(casos_testes_dict_tmp)&set(gabarito_dict.keys()))
    indices_lexelts = [i for i in range(len(todos_lexelts))]

    for cont in indices_lexelts:
        lexelt = todos_lexelts[cont]
        frase, palavra, pos = casos_testes_dict[lexelt]
        frase = Util.descontrair(frase).replace("  ", " ")
        palavra = lexelt.split(".")[0]

        print("%s\t%s"%(str(lexelt), frase))


def testar_casos(cfgs, tipo, pos_avaliadas=['a','n','r','v']):
    base_ox = BaseOx.BASE_OX

    rep_vet = RepVetorial.REP
    alvaro = AbordagemAlvaro.ABORDAGEM

    casos_testes_dict, gabarito_dict = carregar_bases(cfgs, tipo, pos_avaliadas=pos_avaliadas)
    casos_testes_dict_tmp = list(casos_testes_dict.keys())

    todos_lexelts = list(set(casos_testes_dict_tmp)&set(gabarito_dict.keys()))
    indices_lexelts = [i for i in range(len(todos_lexelts))]
    
    #lexelt = raw_input("\nDigite aqui o lexelt almejado: ")
    lexelt = 'bull.n 583'
    frase, palavra, pos = casos_testes_dict[lexelt]
    frase = Util.descontrair(frase).replace("  ", " ")
    palavra = lexelt.split(".")[0]
    gabarito = gabarito_dict[lexelt]

    print(palavra)
    print("%s\t%s"%(str(lexelt), frase))
    print(gabarito)
    print("\n")

    dir_cache_rel_sinonimia = cfgs['caminho_raiz_bases']+'/'+cfgs['oxford']['cache']['sinonimia']
    obj_unificado = base_ox.construir_objeto_unificado(palavra)

    kcache_relacao_sin = "%s-%s.json"%(palavra, pos)
    dir_obj = dir_cache_rel_sinonimia+'/'+kcache_relacao_sin

    if not kcache_relacao_sin in Util.list_arqs(dir_cache_rel_sinonimia):
        print("\n- Objeto de relacao de sinonimia para '%s' sera criado!\n"%palavra)
        rel_definicoes = alvaro.construir_relacao_definicoes(palavra, pos, fontes='oxford')
        print("\n- Objeto de relacao de sinonimia para '%s' fora criado!\n"%palavra)
        Util.salvar_json(dir_obj, rel_definicoes)
    else:
        rel_definicoes = Util.abrir_json(dir_obj, criar=False)
        print("\n- Objeto de relacao de sinonimia para '%s' ja existia e foi aberto!\n"%palavra)

    for def_polissemica in rel_definicoes:
        uniao_palavras_sem_duplicatas = set()
        uniao_palavras_com_duplicatas = list()
        exemplos_blob = [ ]
        try:
            lista_exemplos = base_ox.obter_atributo(palavra, pos, def_polissemica, 'exemplos')
            for ex in lista_exemplos:
                ex_blob = TextBlob(ex)
                exemplos_blob.append(ex_blob)
                for token in ex_blob.words:
                    if Util.is_stop_word(token.lower()) == False:
                        token_lematizado = lemmatize(token)
                        uniao_palavras_sem_duplicatas.add(token_lematizado)
                        uniao_palavras_com_duplicatas.append(token_lematizado)
        except Exception, e:
            print(e)
            exemplos = [ ]

        res = [ ]

        for p in uniao_palavras_sem_duplicatas:
            textblob_vocab = TextBlob(" ".join(uniao_palavras_com_duplicatas))
            tf = alvaro.tf(p, textblob_vocab)
            res.append((p, tf))

        for reg in sorted(res, key=lambda x: x[1], reverse=False):
            if reg[0] != palavra:
                print(reg)

        print("\n")
        print(def_polissemica)
        print(frase)
        print(gabarito)
        print("\n")

        #Util.exibir_json(exemplos, bloquear=True)


if __name__ == '__main__':
    if len(argv) < 2:
        print('\nParametrizacao errada!\nTente py ./main <dir_config_file>\n\n')
        exit(0)

    Util.verbose_ativado = False

    Util.cls()
    cfgs = Util.carregar_cfgs(argv[1])
    params_exps = cfgs['params_exps']

    InterfaceBases.setup(cfgs)
    rep_vet = RepVetorial.REP

    caminho_raiz_bases = cfgs['caminho_raiz_bases']

    vldr_se = VlddrSemEval(cfgs)  # Validador SemEval 2007

    rep_vet = RepVetorial.REP
    rep_vet.carregar_modelo(caminho_raiz_bases+'/'+cfgs['modelos']['default'], binario=True)

    # experimentalismo(cfgs)
    diretorio_saida_json = cfgs['dir_saida_json']
    dir_saida_abrdgm = cfgs['saida_experimentos']

    todos_criterios = params_exps['todos_criterios']
    qtde_exemplos = params_exps['qtde_exemplos']
    qtde_sugestoes_best = params_exps['qtde_sugestoes_best']
    qtde_sugestoes_oot = params_exps['qtde_sugestoes_oot']
    todas_fontes_def = params_exps['todas_fontes_def']
    tipos_base = params_exps['tipos_base']

    flags_usar_gabarito = [eval(v) for v in params_exps['usar_gabarito']]
    flags_usar_exemplos = [eval(v) for v in params_exps['usar_exemplos']]

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
    caminho_raiz_semeval = "%s/%s"%(caminho_raiz_bases, cfgs_se["dir_raiz"])
    path_base_teste = "%s/%s" % (caminho_raiz_semeval, cfgs_se["test"]["input"])

    casos_filtrados_tmp = vldr_se.carregar_caso_entrada(path_base_teste, padrao_se=True)
    contadores = dict([(pos, 0) for pos in cfgs_se['todas_pos']])
    lexelts_filtrados = [ ]

    for lexelt in casos_filtrados_tmp:
        pos_tmp = re.split('[\s\.]', lexelt)[1]  # 'war.n 0' => ('war', 'n', 0)
        if contadores[pos_tmp] < max_indice_pos:
            lexelts_filtrados.append(lexelt)
            contadores[pos_tmp] += 1
    # Fim do filtro de casos de entrada por lexelt

    res_best = vldr_se.aval_parts_orig('best', pos_filtradas=pos_avaliadas[0], lexelts_filtrados=lexelts_filtrados).values()
    res_oot = vldr_se.aval_parts_orig('oot', pos_filtradas=pos_avaliadas[0], lexelts_filtrados=lexelts_filtrados).values()

    for parametros in parametrizacao:
        crit, max_ex, fontes_def, tipo, usr_gab, usr_ex, pos_avaliadas = parametros

        if type(pos_avaliadas) != list:
            raise Exception("\n\nAs POS avaliadas devem ser expressas no formato de list!\n\n")

        predicao = set()
        casos = set()
        gabarito = set()

        exe = 'r'

        if exe == 'r':
            predicao, casos, gabarito\
                         = predizer_sins(cfgs, lexelts_filtrados=lexelts_filtrados,
                                usar_gabarito=usr_gab, criterio=crit, tipo=tipo,
                                max_ex=max_ex, usr_ex=usr_ex, fontes_def=fontes_def,
                                pos_avaliadas=pos_avaliadas, rep_vetorial=rep_vet)

        elif not exe == 'f':
            print("\n\nOpcao invalida!\nAbortando execucao...\n\n")
            exit(0)

        for cont in qtde_sugestoes_oot:
            nome_abrdgm = cfgs['padrao_nome_submissao']  # '%d-%s-%s ... %s'
            nome_abrdgm = nome_abrdgm%(crit, usr_gab, tipo, max_ex, usr_ex, fontes_def, 'oot')

            vldr_se.formtr_submissao(dir_saida_abrdgm+"/"+nome_abrdgm, predicao, cont, ":::")
            print("Saida da sua abordagem: "+dir_saida_abrdgm+"/"+nome_abrdgm)

            if Util.arq_existe(dir_saida_abrdgm, nome_abrdgm):
                try:
                    res_oot.append(vldr_se.obter_score(dir_saida_abrdgm, nome_abrdgm))
                except Exception, reg:
                    print("\n@@@ Erro na geracao do score da abordagem '%s'"%nome_abrdgm)

        nome_abrdgm = cfgs['padrao_nome_submissao']
        nome_abrdgm = nome_abrdgm % (
            crit, usr_gab, tipo, max_ex, usr_ex, fontes_def, 'best')

        print("Saida da sua abordagem: "+dir_saida_abrdgm+"/"+nome_abrdgm)
        vldr_se.formtr_submissao(dir_saida_abrdgm+"/"+nome_abrdgm, predicao, 10, "::")

        if Util.arq_existe(dir_saida_abrdgm, nome_abrdgm):
            try:
                res_best.append(vldr_se.obter_score(dir_saida_abrdgm, nome_abrdgm))
            except:
                print("\n@@@ Erro na geracao do score da abordagem '%s'"%nome_abrdgm)

    res_tarefas = {'best': res_best, 'oot': res_oot}

    for k in res_tarefas:
        res_tarefa = res_tarefas[k]
        chave = ""
        while not chave in res_tarefa[0].keys():
            msg = "\nEscolha a chave pra ordenar a saida "
            chave = raw_input(msg+k.upper()+": " +
                              str(res_tarefa[0].keys()) + ": ")

        res_tarefa = sorted(res_tarefa, key=itemgetter(chave), reverse=True)

        Util.salvar_json("%s/%s.%s"%(diretorio_saida_json, k.upper(), k), res_tarefa)
        print("\n" + chave.upper() + "\t-----------------------")

        for reg in res_tarefa:
            print(reg['nome'])
            etmp = dict(reg)
            del etmp['nome']
            print(etmp)
            print('\n')

        print("\n")

    print('\n\nFim do __main__\n')


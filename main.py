#! coding: utf-8
from operator import itemgetter
from Utilitarios import Util
from SemEval2007 import *
from sys import argv
from statistics import mean as media
import statistics
import itertools
import traceback
import re
import sys

# Experimentacao
from ModuloDesambiguacao.DesambiguadorOxford import DesOx
from ModuloDesambiguacao.DesambiguadorUnificado import DesambiguadorUnificado
from ModuloDesambiguacao.DesambiguadorWordnet import DesWordnet
from ModuloDesambiguacao.DesambiguadorWikipedia import DesWikipedia
from ModuloBasesLexicas.ModuloClienteOxfordAPI import BaseOx
from ModuloBasesLexicas.ModuloClienteOxfordAPI import CliOxAPI
from RepositorioCentralConceitos import CasadorConceitos
from nltk.corpus import wordnet
# Fim pacotes da Experimentacao

# Testar Abordagem Alvaro
from Abordagens.AbordagemAlvaro import AbordagemAlvaro
from Abordagens.RepresentacaoVetorial import RepVetorial
from CasadorManual import CasadorManual
from textblob import TextBlob

wn = wordnet


def avaliar_des(cfgs, fonte='wordnet'):
    validador = VlddrSemEval(cfgs)
    des_wn = DesWordnet(cfgs)

    from ModuloDesambiguacao.DesambiguadorBabelfy import DesBabelfy
    des_babelfy = DesBabelfy(cfgs, BaseOx(cfgs))

    casos_testes_dict, gabarito_dict = carregar_bases(
        cfgs, raw_input("\n\nDigite a base> "))
    palavras = set()

    alvaro = AbordagemAlvaro(cfgs, BaseOx(cfgs), None)

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


def relacionadas_embbedings(cfgs, fonte='wordnet'):
    validador = VlddrSemEval(cfgs)
    des_wn = DesWordnet(cfgs)

    casos_testes_dict, gabarito_dict = carregar_bases(cfgs, "test")
    palavras = set()

    rep_vetorial = RepVetorial(cfgs)
    rep_vetorial.carregar_modelo(cfgs['modelos']['word2vec-default'])

    alvaro = AbordagemAlvaro(cfgs, BaseOx(cfgs), None)

    for lexelt in set(casos_testes_dict.keys()) & set(gabarito_dict.keys()):
        p = lexelt.split(".")[0]
        palavras.add(p)

    minha_pos = raw_input("\nMinha POS: ")

    for lexelt in set(casos_testes_dict.keys()) & set(gabarito_dict.keys()):
        frase, palavra, pos = casos_testes_dict[lexelt]
        frase = Util.descontrair(frase).replace("  ", " ")
        palavra = lexelt.split(".")[0]

        if palavra in palavras:
            if pos == minha_pos and not 'HEROES' in frase:
                nfrase = str(frase).replace(palavra, "(%s)" % palavra)
                nfrase = frase
                resposta = validador.fltr_gabarito(gabarito_dict[lexelt])

                Util.print_formatado("%s" % frase)
                Util.print_formatado("Palavra: "+palavra)
                Util.print_formatado("POS: "+pos)
                Util.print_formatado("Resposta: "+str(resposta))
                Util.print_formatado("\n\n")

                relacionadas = rep_vetorial.obter_palavras_relacionadas(
                    [palavra], topn=500)
                relacionadas = [p[0] for p in sorted(
                    relacionadas, key=lambda x: x[1], reverse=True)]

                try:
                    if unicode(resposta[0][0]) in relacionadas:
                        msg = "\n\n@@@ A palavra %s esta no indice %d\n\n"
                        Util.print_formatado(msg%(palavra, relacionadas.index(resposta[0][0])))

                except Exception, e:
                    pass

                for p in relacionadas[:30]:
                    Util.print_formatado("\t" + str(p))
                Util.print_formatado("\n\n")
                raw_input("<enter>\n\n\n")


def relacionadas_embbedings2(cfgs):
    rep_vetorial = RepVetorial(cfgs)
    rep_vetorial.carregar_modelo("/home/isaias/Desktop/pt.bin")

    positivas = raw_input("Digite a palavra POSITIVA: ").split(',')
    negativas = raw_input("Digite a palavra NEGATIVA: ").split(',')

    relacionadas = rep_vetorial.obter_palavras_relacionadas(
        positivas, negativas, topn=600)
    relacionadas = sorted(relacionadas, key=lambda x: x[1], reverse=True)

    mpos = raw_input("POS: ")

    relacionadas = [e for e in relacionadas if wn.synsets(e[0], mpos)]

    for p in relacionadas:
        print("\t-"+str(p))

    # raw_input(relacionadas)
    #vetor = rep_vetorial.modelo[relacionadas[0]]
    #relacionadas = rep_vetorial.modelo.similar_by_vector(vetor, topn=10, restrict_vocab=1000)

    # print("\n\n")
    #print("Relacionadas: "+str(relacionadas))
    # print("\n\n")


def utilizar_word_embbedings(configs, usar_exemplos=True, usar_hiperonimo=True, fonte='wordnet'):
    base_ox = BaseOx(configs)
    rep_vetorial = RepVetorial(configs)
    rep_vetorial.carregar_modelo(configs['modelos']['word2vec-default'])

    while raw_input("\nContinuar? S/n: ").lower() != 'n':
        palavra = raw_input("Palavra: ")

        if fonte == 'oxford':
            todas_definicoes = base_ox.obter_definicoes(palavra)
        elif fonte == 'wordnet':
            todas_definicoes = wn.synsets(palavra)

        for definicao in todas_definicoes:
            entrada = []
            todos_lemas = []

            if fonte == 'oxford':
                todos_lemas = base_ox.obter_sins(palavra, definicao)
            elif fonte == 'wordnet':
                todos_lemas = definicao.lemma_names()  # Synset

            for lema in todos_lemas:
                if fonte == 'wordnet':
                    entrada += lema.split('_')
                elif fonte == 'oxford':
                    entrada += lema.split(' ')

            exemplos, hiperonimo = [], []

            if fonte == 'oxford':
                exemplos = base_ox.obter_atributo(
                    palavra, None, definicao, 'exemplos')
                hiperonimo = []
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

            print("Palavras para a definicao '%s'" % definicao)
            if fonte == 'wordnet':
                print("Definicao: %s" % definicao.definition())
            print("Sinonimos: %s" % todos_lemas)
            print("\n")
            for p in palavras:
                print("\t" + str(p))
            print("\n\n")
            raw_input("<enter>")


""" Este metodo testa a abordagem do Alvaro em carater investigativo
sobre o componente que escolhe os sinonimos a serem utilizados """


def medir_seletor_candidatos(configs):
    validador = VlddrSemEval(configs)
    contadores = Util.abrir_json(configs['leipzig']['dir_contadores'])

    #dir_saida_seletor_candidatos = raw_input("Diretorio saida arquivo seletor candidatos: ")
    dir_saida_seletor_candidatos = "/home/isaias/saida-oot.oot"

    base_ox = BaseOx(configs)
    alvaro = AbordagemAlvaro(configs, base_ox, CasadorManual(configs))

    # Abordagem com representacao vetorial das palavras
    rep_vet = RepVetorial(configs)
    rep_vet.carregar_modelo(diretorio=configs['modelos']['word2vec-default'])

    bases_utilizadas = raw_input(
        "Escolha a base para fazer a comparacao: 'trial' ou 'test': ")
    dir_gabarito = configs['semeval2007'][bases_utilizadas]['gold_file']
    dir_entrada = configs['semeval2007'][bases_utilizadas]['input']

    gabarito_tmp = validador.carregar_gabarito(dir_gabarito)

    casos_testes_list, gabarito_list = [], []

    gabarito_dict = dict()

    for lexelt in gabarito_tmp:
        lista = []
        for sugestao in gabarito_tmp[lexelt]:
            voto = gabarito_tmp[lexelt][sugestao]
            lista.append([sugestao, voto])
        gabarito_list.append(lista)
        gabarito_dict[lexelt] = lista

    gabarito_tmp = None

    validador_semeval2007 = VlddrSemEval(configs)
    casos_testes_tmp = validador_semeval2007.carregar_caso_entrada(dir_entrada)

    casos_testes_dict = {}

    for lexema in casos_testes_tmp:
        for registro in casos_testes_tmp[lexema]:
            frase = registro['frase']
            palavra = registro['palavra']
            pos = lexema.split(".")[1]
            casos_testes_list.append([frase, palavra, pos])

            nova_chave = "%s %s" % (lexema, registro['codigo'])
            casos_testes_dict[nova_chave] = [frase, palavra, pos]

    casos_testes_list, gabarito_list, lexemas_list = [], [], []

    resultados_persistiveis = []

    if len(gabarito_list) != len(casos_testes_list):
        raise Exception("A quantidade de instancias de entrada estao erradas!")

    for lexema in casos_testes_dict:
        if lexema in casos_testes_dict and lexema in gabarito_dict:
            casos_testes_list.append(casos_testes_dict[lexema])
            gabarito_list.append(gabarito_dict[lexema])
            lexemas_list.append(lexema)

    total_com_resposta = 0
    total_sem_resposta = 0

    usar_sinonimos_wordnet = usar_sinonimos_oxford = usar_sinonimos_word_embbedings = False

    if raw_input("Adicionar sinonimos Wordnet? s/N? ") == 's':
        usar_sinonimos_wordnet = True
    if raw_input("Adicionar sinonimos Oxford? s/N? ") == 's':
        usar_sinonimos_oxford = True
    if raw_input("Adicionar sinonimos WordEmbbedings? s/N? ") == 's':
        usar_sinonimos_word_embbedings = True

    total_candidatos = []

    if usar_sinonimos_word_embbedings:
        max_resultados = int(raw_input("Maximo resultados: "))
    else:
        max_resultados = 0

    tarefa = raw_input("\n\nQual a tarefa? 'best' ou 'oot'? ")
    lexema_candidatos = dict()

    for indice in range(len(gabarito_list)):
        if alvaro.possui_moda(gabarito_list[indice]) == True:
            candidatos = [e[0] for e in gabarito_list[indice]]
            contexto, palavra, pos = casos_testes_list[indice]

            resultados_persistiveis.append(indice)

            # Extraindo candidatos que a abordagem do Alvaro escolhe atraves de dicionarios
            candidatos_selecionados_alvaro = list()

            if usar_sinonimos_wordnet == True:
                candidatos_selecionados_alvaro += alvaro.selec_candidatos(
                    palavra, pos, fontes=['wordnet'])
            if usar_sinonimos_oxford == True:
                candidatos_selecionados_alvaro += alvaro.selec_candidatos(
                    palavra, pos, fontes=['oxford'])
            if usar_sinonimos_word_embbedings == True:
                palavras_relacionadas = rep_vet.obter_palavras_relacionadas(
                    positivos=[palavra], topn=max_resultados)
                palavras_relacionadas = [p[0] for p in palavras_relacionadas]
                candidatos_selecionados_alvaro += palavras_relacionadas

            total_candidatos.append(len(candidatos_selecionados_alvaro))
            candidatos_selecionados_alvaro = list(
                set(candidatos_selecionados_alvaro))

            # Respostas certas baseada na instancia de entrada
            gabarito_ordenado = sorted(
                gabarito_list[indice], key=lambda x: x[1], reverse=True)
            gabarito_ordenado = [reg[0] for reg in gabarito_ordenado]

            print("\nCASO ENTRADA: \n" + str((contexto, palavra, pos)))
            print("\nMEDIA DE SUGESTOES:\n%d" %
                  (sum(total_candidatos)/len(total_candidatos)))
            print("\nRESPOSTAS CORRETAS:\n\n%s" % str(gabarito_ordenado))

            intersecao_tmp = list(set([gabarito_ordenado[0]]) & set(
                candidatos_selecionados_alvaro))
            lexema_candidatos[lexemas_list[indice]] = set(
                candidatos_selecionados_alvaro)

            if intersecao_tmp:
                total_com_resposta += 1
                print("\nINTERSECAO: %s" % str(intersecao_tmp))
                print("\nTOTAL PREDITOS CORRETAMENTE: %d" %
                      (len(intersecao_tmp)))
            else:
                total_sem_resposta += 1

    arquivo_saida = open(dir_saida_seletor_candidatos, "w")

    for indice in resultados_persistiveis:
        # [['crazy', 3], ['fast', 1], ['very fast', 1], ['very quickly', 1], ['very rapidly', 1]]
        if tarefa == 'best':
            sugestoes = sorted(
                gabarito_list[indice], key=lambda x: x[1], reverse=True)[:1]
            sugestoes = [e[0] for e in sugestoes]
        elif tarefa == 'oot':
            sugestoes = sorted(
                gabarito_list[indice], key=lambda x: x[1], reverse=True)
            sugestoes = [[e[0] for e in sugestoes][0]]

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
    print("\nTotal sem resposta: " + str(total_sem_resposta))


def carregar_bases(cfgs, tipo_base, pos_avaliadas=None):
    if pos_avaliadas in [None, []]:
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
    chaves_casos_testes = []
    for lexelt_parcial in casos_testes:
        for reg in casos_testes[lexelt_parcial]:
            chaves_casos_testes.append(
                "%s %s" % (lexelt_parcial, reg['codigo']))
    todos_lexelts = set(chaves_casos_testes) & set(gabarito)
    todos_lexelts = [l for l in todos_lexelts if re.split('[\.\s]', l)[
        1] in pos_avaliadas]

    for lexelt in todos_lexelts:
        lista = []
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
    casos_testes, gabarito = [], []

    for lexelt in casos_testes_dict:
        if lexelt in gabarito_dict:
            casos_testes.append(casos_testes_dict[lexelt])
            gabarito.append(gabarito_dict[lexelt])

    return casos_testes_dict, gabarito_dict


def avaliar_desambiguador(cfgs, fonte='oxford'):
    casador_manual = CasadorManual(cfgs)
    base_ox = BaseOx(cfgs)
    alvaro = AbordagemAlvaro(cfgs, base_ox, casador_manual)

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


def predizer_sins(cfgs, criterio='frequencia',
                  usar_gabarito=True,
                  lexelts_filtrados=None,
                  fontes_def='oxford', tipo=None,
                  max_ex=-1, usr_ex=False,
                  pos_avaliadas=None,
                  rep_vetorial=None):

    separador = "###"

    if fontes_def != 'oxford':
        raise Exception("Esta fonte de definicoes nao é contem exemplos...")

    if pos_avaliadas in [None, []]:
        pos_avaliadas = cfgs['semeval2007']['todas_pos']
    if type(pos_avaliadas) != list:
        raise Exception("\n\nAs POS avaliadas devem ser uma list!\n\n")

    # Construtor com carregador de modelo
    dir_modelo = "%s/%s" % (cfgs['caminho_raiz_bases'],
                            cfgs['modelos']['word2vec-default'])
    rep_vet = RepVetorial(cfgs, dir_modelo, binario=True)

    casador_manual = CasadorManual(cfgs)
    base_ox = BaseOx(cfgs)
    alvaro = AbordagemAlvaro(cfgs, base_ox, casador_manual, rep_vetorial)

    des_ox = DesOx(cfgs, base_ox)
    des_wn = DesWordnet(cfgs)

    if max_ex == -1:
        max_ex = sys.maxint

    # Resultado de saida <lexelt : lista>
    predicao_final = dict()

    # Fonte para selecionar as definicoes e fonte para selecionar os candidatos
    # fontes_def, fontes_cands = raw_input("Digite a fonte para definicoes: "), ['oxford', 'wordnet']
    fontes_def, fontes_cands = fontes_def, ['oxford', 'wordnet']
    casos_testes_dict, gabarito_dict = carregar_bases(
        cfgs, tipo, pos_avaliadas=pos_avaliadas)

    if lexelts_filtrados in [None, []]:
        casos_testes_dict_tmp = list(casos_testes_dict.keys())
    else:
        casos_testes_dict_tmp = set(casos_testes_dict.keys())&set(lexelts_filtrados)
        casos_testes_dict_tmp = list(casos_testes_dict_tmp)

    vldr_se = VlddrSemEval(cfgs)
    todos_lexelts = list(set(casos_testes_dict_tmp)&set(gabarito_dict.keys()))
    indices_lexelts = [i for i in range(len(todos_lexelts))]

    palavras_invalidas = [ ]

    cache_relacao_sinonimia = dict()
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
                    cands = [e[0] for e in gabarito_dict[lexelt] if not Util.e_multipalavra(e[0])]
                else:
                    cands = alvaro.selec_candidatos(palavra, pos, fontes=fontes_cands)
                    cands = [p for p in cands if p.istitle() == False]
            else:
                cands = cache_seletor_candidatos[chave_seletor_candidatos]

            cands = [p for p in cands if not Util.e_multipalavra(p)]

            interseccao_casos = list(set(casos_testes_dict_tmp)&set(gabarito_dict.keys()))

            print("Processando a entrada " + str(lexelt))
            print("%d / %d\n"%(cont+1, len(interseccao_casos)))

            med_sim = cfgs['medida_similaridade_padrao']

            if criterio == 'embbedings' or pos in ['a', 'r']:
                # Filtrando por POS-tag
                res_tmp = rep_vet.obter_palavras_relacionadas(positivos=[lexelt.split('.')[0]], topn=200, pos=pos)
                sugestao = [sin for sin, pontuacao in res_tmp if sin in cands]

                if sugestao != [ ]:
                    predicao_final[lexelt] = sugestao
                else:
                    predicao_final[lexelt] = alvaro.sugestao_contingencia(palavra, pos, fontes_def)

            elif criterio == 'alvaro':
                res_tmp = rep_vet.obter_palavras_relacionadas(positivos=[lexelt.split('.')[0]], topn=200, pos=pos)
                cands = [sin for sin, pontuacao in res_tmp if sin in cands]

                # [[u'clean.Verb.1', u'Make clean; remove dirt, marks, or stains from.', []], 0.11]
                if fontes_def == 'oxford':
                    if med_sim == 'word_move_distance' and None == des_ox.rep_vetorial:
                        des_ox.rep_vetorial = rep_vet
                    
                    res_desambiguacao = des_ox.desambiguar(frase, palavra, pos, usr_ex=usr_ex, med_sim=med_sim)

                # [[u'huffy.s.02', u'roused to anger', []], 0.0]
                elif fontes_def == 'wordnet':
                    res_desambiguacao = des_wn.cosine_lesk(frase, palavra, pos=pos, nbest=True)

                flag_resultado_valido = False

                try:
                    melhor_resultado = res_desambiguacao[0][1]
                    if melhor_resultado > 0.00 and med_sim == "cosine":
                        flag_resultado_valido = True
                    elif med_sim == 'word_move_distance':
                        flag_resultado_valido = True
                except IndexError, ie:
                    pass

                # Se o desambiguador consegue predizer o significado da palavra
                if flag_resultado_valido:
                    chave_relacao_sinonimia = str((palavra, pos))

                    if not chave_relacao_sinonimia in cache_relacao_sinonimia:
                        rel_sinonimia = alvaro.construir_sinonimia(palavra, pos, frase,
                                                                fontes_def=fontes_def, fontes_cands=fontes_cands,
                                                                cands=cands, max_ex=max_ex, usr_ex=usr_ex,
                                                                med_sim=med_sim)

                        cache_relacao_sinonimia[chave_relacao_sinonimia] = rel_sinonimia
                    else:
                        rel_sinonimia = cache_relacao_sinonimia[chave_relacao_sinonimia]

                    rel_sinonimia.reverse()

                    # Armazena pares (label_def : [reg1, reg2, reg3])
                    res_agregado = dict()

                    if rel_sinonimia:  # Se uma relacao de sinonimia foi feita
                        # => (def_sin;lema, def_des;lema, 0.00)
                        for label_sin, label_des, frase_sin_tmp, pnt_sin in rel_sinonimia:
                            if fontes_def == 'oxford':  # WORDNET: label_des = war.n.1;war
                                # "OXFORD: definicao;war.Noun.1" -> "war.Noun.1"
                                label_des = label_des.split(";")[-1]
                            else:
                                pass

                            if not label_des in res_agregado:
                                res_agregado[label_des] = []

                            res_agregado[label_des].append(
                                (label_sin, label_des, pnt_sin))

                        saida_sinonimos_tmp = []

                        # Iterando resultado de desambiguacao
                        # [[u'def_label', u'def', []], 0.0] = oxford e wordnet
                        for rdes_tmp, ptmp in res_desambiguacao:
                            label_des, def_des = rdes_tmp[:2]

                            res_agregado_tmp = dict()

                            try:
                                rel_ordenada = sorted(
                                    res_agregado[label_des], key=lambda x: x[1], reverse=False)
                            except KeyError, ke:
                                rel_ordenada = []

                            # Iterando relacao de sinonimia computada anteriormente
                            for reg_sin in rel_ordenada:
                                reg_sin_tmp = reg_sin[0]
                                def_sin, lema_sin = reg_sin_tmp.split(
                                    ';')[:-1][0], reg_sin_tmp.split(';')[-1]
                                pont_rel = reg_sin[2]

                                ch_defs = "%s%s%s" % (
                                    reg_sin[0], separador, reg_sin[1])

                                # Agregando pontuacoes de frases de exemplos distintas
                                if not ch_defs in res_agregado_tmp:
                                    res_agregado_tmp[ch_defs] = list()

                                # Adicionando pontuacao da nova frase
                                res_agregado_tmp[ch_defs].append(pont_rel)

                            res_agregado_tmp_array = [
                                (ch_defs, Util.media(res_agregado_tmp[ch_defs])) for ch_defs in res_agregado_tmp]

                            res_agregado_tmp = sorted(
                                res_agregado_tmp_array, key=lambda x: x[1], reverse=True)

                            for reg_agregado in res_agregado_tmp:
                                def_des = reg_agregado[0].split(separador)[0]
                                def_des, lema_des = def_des.split(
                                    ';')[:-1][0], def_des.split(';')[-1]

                                pontuacao_agregado = reg_agregado[1]

                                # Se o sinonimo/por definicao tem score
                                if pontuacao_agregado > 0.00:
                                    # Wordnet: 'angry.s.02', u'furious'
                                    # Oxford: (u'Having all the necessary or appropriate parts.', u'complete')
                                    try:
                                        if fontes_def == 'oxford':
                                            sins_reg = base_ox.obter_sins(
                                                lema_des, def_des)
                                        elif fontes_def == 'wordnet':
                                            # Wordnet def_des = name synset
                                            sins_reg = wn.synset(
                                                def_des).lemma_names()
                                    except:
                                        #raw_input('\nExcecao aqui para o lema %s!' % lema_des)
                                        sins_reg = []

                                    if len(sins_reg) > 0:
                                        saida_sinonimos_tmp += sins_reg

                        saida_sins = []
                        for sin in saida_sinonimos_tmp:
                            if usar_gabarito == True:
                                if sin in [p[0] for p in gabarito_dict[lexelt]] and not sin in saida_sins:
                                    saida_sins.append(sin)
                            else:
                                saida_sins.append(sin)

                        if saida_sins:
                            predicao_final[lexelt] = saida_sins

            elif criterio == 'frequencia':
                cliente_ox = CliOxAPI(cfgs)

                cands_ponts = []
                for sin in cands:
                    try:
                        cands_ponts.append((sin, cliente_ox.obter_frequencia(sin)))
                    except Exception, e:
                        cands_ponts.append((sin, -1))

                res_predicao = [reg[0] for reg in sorted(cands_ponts, key=lambda x:x[1], reverse=True)]
                predicao_final[lexelt] = res_predicao

            if lexelt in predicao_final:
                tam_sugestao = len(predicao_final[lexelt])
                print("Lexelt %s recebeu a sugestao (%d) %s\n"%(lexelt, tam_sugestao, str(predicao_final[lexelt][:10])))
            else:
                predicao_final[lexelt] = alvaro.sugestao_contingencia(palavra, pos, fontes_def)
                print("Lexelt %s recebeu a sugestao CONTINGENCIAL %s\n"%(lexelt, str(predicao_final[lexelt][:10])))

            if cont+1 < len(indices_lexelts):
                prox_lexelt = todos_lexelts[cont+1]
                prox_palavra = prox_lexelt.split(".")[0]
                if palavra != prox_palavra:
                    BaseOx.objs_unificados = None
                    BaseOx.objs_unificados = {}

    # Para o Garbage Collector
    cache_relacao_sinonimia=None
    cache_seletor_candidatos=None
    cache_resultado_desambiguador=None

    # Remover predicoes falhas
    predicao_final_copia=dict(predicao_final)

    for reg in predicao_final:
        if predicao_final[reg] in [[], ""]:
            del predicao_final_copia[reg]

    predicao_final=dict(predicao_final_copia)

    # Predicao, caso de entrada, gabarito
    return predicao_final, casos_testes_dict, gabarito_dict

def testar_casamento(cfgs):
    base_unificada = BaseOx(cfgs)
    casador = CasadorConceitos(cfgs, base_unificada)

    palavra = raw_input('Palavra: ')
    pos = raw_input('POS: ')

    resultado = casador.iniciar_casamento(palavra, pos)
    print('\n')

    for e in resultado:
        print(e)
        print(resultado[e])
        print('\n\n\n')

    print('\n\nCheguei aqui...')


def testar_wander(configs):
    from Abordagens.Wander import PonderacaoSinonimia

    ponderacao_sinonimia = PonderacaoSinonimia.Ponderador(configs)
    print('\n\n')
    termo = raw_input('Digite a palavra: ')
    pos = raw_input('POS: ')
    contexto = 'i have been at war with other men'
    ponderacao_sinonimia.iniciar_processo(termo, pos, contexto)
    exit(0)


def testar_casamento_manual(configs):
    from CasadorManual import CasadorManual

    casador = CasadorManual(configs, configs['dir_base_casada_manualmente'])
    casador.iniciar_casamento(
        raw_input('Digite o termo: '), raw_input('POS: '))


def experimentalismo(cfgs):
    if False:
        rvet = RepVetorial(cfgs)

        path_modelo = cfgs['modelos']['word2vec-default']
        #rvet.modelo = gensim.models.KeyedVectors.load_word2vec_format(path_modelo, binary=True)
        rvet.carregar_modelo(path_modelo, binario=True)
        #s1, s2 = raw_input("S1: "), raw_input("S2: ")
        s1 = "i maked mistake"
        s2 = "i maked error"
        #s2 = "having an abundant supply of money or possessions of value"
        print("\n\nSAIDA: " + str(rvet.word_move_distance(s1, s2)) + "\n\n")
        exit(0)
    if False:
        from ModuloDesambiguacao.DesambiguadorBabelfy import DesBabelfy
        des_babelfy = DesBabelfy(cfgs, BaseOx(cfgs))
        frase, palavra = "i was fixing the engine of my car", "car"
        res = des_babelfy.desambiguar(frase, palavra)
        print("\n\n")
        import json
        res = json.dumps(res, indent=4, sort_keys=True)
        print(res)
        print("\n\n")
        exit(0)
    if False:
        relacionadas_embbedings2(cfgs)
        exit(0)
    elif False:
        relacionadas_embbedings(cfgs)
        exit(0)
    elif False:
        avaliar_des(cfgs, fonte='babelfy')
        exit(0)
    elif False:
        des_wkpedia = DesWikipedia(cfgs)
        des_wkpedia.consultar_entidade('George Mason University')
        exit(0)
    elif False:
        base_ox = BaseOx(cfgs)
        p = raw_input("Palavra: ")
        definicoes = base_ox.obter_definicoes(p, pos='Noun')
        print("\n\n")
        for d in definicoes:
            sins = base_ox.obter_sins(p, d)
            print("\t"+d+"\n\t"+str(sins)+"\n")
        print("\n\n")
        exit(0)


if __name__ == '__main__':
    if len(argv) < 2:
        print('\nParametrizacao errada!\nTente py ./main <dir_config_file>\n\n')
        exit(0)

    Util.verbose_ativado = False

    Util.cls()
    cfgs = Util.carregar_cfgs(argv[1])
    params_exps = cfgs['params_exps']

    caminho_raiz_bases = cfgs['caminho_raiz_bases']

    vldr_se = VlddrSemEval(cfgs)  # Validador SemEval 2007

    rep_vetorial = RepVetorial(cfgs)
    rep_vetorial.carregar_modelo(caminho_raiz_bases+'/'+cfgs['modelos']['word2vec-default'], binario=True)

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

    pos_avaliadas = params_exps['pos_avaliadas'] if params_exps['pos_avaliadas'] else [
        None]
    max_indice_pos = cfgs['params_exps']['max_entradas_pos']

    exe = None
    while not exe in ['r', 'f']:
        exe = raw_input("\n[R]ealizar predicao ou [F] formatar submissoes? > ").lower()

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

    casos_filtrados_tmp = vldr_se.carregar_caso_entrada(
        path_base_teste, padrao_se=True)
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

        if exe == 'r':
            predicao, casos, gabarito\
                         = predizer_sins(cfgs, lexelts_filtrados=lexelts_filtrados,
                                usar_gabarito=usr_gab, criterio=crit, tipo=tipo,
                                max_ex=max_ex, usr_ex=usr_ex, fontes_def=fontes_def,
                                pos_avaliadas=pos_avaliadas, rep_vetorial=rep_vetorial)

        elif not exe == 'f':
            print("\n\nOpcao invalida!\nAbortando execucao...\n\n")
            exit(0)

        for cont in qtde_sugestoes_oot:
            nome_abrdgm = cfgs['padrao_nome_submissao']  # '%d-%s-%s ... %s'
            nome_abrdgm = nome_abrdgm%(crit, usr_gab, tipo, max_ex, usr_ex, fontes_def, 'oot')

            vldr_se.formtr_submissao(
                dir_saida_abrdgm+"/"+nome_abrdgm, predicao, cont, ":::")

            if Util.arq_existe(dir_saida_abrdgm, nome_abrdgm):
                try:
                    res_oot.append(vldr_se.obter_score(dir_saida_abrdgm, nome_abrdgm))
                except Exception, e:
                    print("\n####\t"+dir_saida_abrdgm)
                    raw_input(e)
                    traceback.print_stack()
                    print("\n@@@ Erro na geracao do score da abordagem '%s'" %
                          nome_abrdgm)

        nome_abrdgm = cfgs['padrao_nome_submissao']
        nome_abrdgm = nome_abrdgm % (
            crit, usr_gab, tipo, max_ex, usr_ex, fontes_def, 'best')

        vldr_se.formtr_submissao(
            dir_saida_abrdgm+"/"+nome_abrdgm, predicao, 1, "::")

        if Util.arq_existe(dir_saida_abrdgm, nome_abrdgm):
            try:
                res_best.append(vldr_se.obter_score(
                    dir_saida_abrdgm, nome_abrdgm))
            except:
                print("\n@@@ Erro na geracao do score da abordagem '%s'" %
                      nome_abrdgm)

    res_tarefas = {'best': res_best, 'oot': res_oot}

    for k in res_tarefas:
        res_tarefa = res_tarefas[k]
        chave = ""
        while not chave in res_tarefa[0].keys():
            msg = "\nEscolha a chave pra ordenar a saida "
            chave = raw_input(msg+k.upper()+": " +
                              str(res_tarefa[0].keys()) + ": ")

        res_tarefa = sorted(res_tarefa, key=itemgetter(chave), reverse=True)

        Util.salvar_json("%s/%s.%s" %
                         (diretorio_saida_json, k.upper(), k), res_tarefa)
        print("\n" + chave.upper() + "\t-----------------------")

        for e in res_tarefa:
            print(e['nome'])
            etmp = dict(e)
            del etmp['nome']
            print(etmp)
            print('\n')

        print("\n")

    print('\n\nFim do __main__')

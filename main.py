#! coding: utf-8
from pywsd.lesk import cosine_lesk
from operator import itemgetter
from Utilitarios import Util
from SemEval2007 import *
from sys import argv
from statistics import mean as media
import traceback
import re
import sys

# Experimentacao
from ModuloDesambiguacao.DesambiguadorOxford import DesOx
from ModuloDesambiguacao.DesambiguadorUnificado import DesambiguadorUnificado
from ModuloDesambiguacao.DesambiguadorWordnet import DesWordnet
from ModuloBasesLexicas.ModuloClienteOxfordAPI import BaseOx
from ModuloBasesLexicas.ModuloClienteOxfordAPI import ClienteOxfordAPI
from RepositorioCentralConceitos import CasadorConceitos
from nltk.corpus import wordnet
# Fim pacotes da Experimentacao

# Carrega o gabarito o arquivo de input
from SemEval2007 import VlddrSemEval

# Testar Abordagem Alvaro
from Abordagens.AbordagemAlvaro import AbordagemAlvaro
from Abordagens.RepresentacaoVetorial import RepresentacaoVetorial
from CasadorManual import CasadorManual

wn = wordnet

    
def utilizar_word_embbedings(configs, usar_exemplos=True, usar_hiperonimo=True, fonte='wordnet'):
    base_ox = BaseOx(configs)
    rep_vetorial = RepresentacaoVetorial(configs)
    rep_vetorial.carregar_modelo(configs['modelos']['word2vec-default'])

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
                todos_lemas = definicao.lemma_names() # Synset

            for lema in todos_lemas:
                if fonte == 'wordnet': entrada += lema.split('_')
                elif fonte == 'oxford': entrada += lema.split(' ')

            exemplos, hiperonimo = [ ], [ ]

            if fonte == 'oxford':
                exemplos = base_ox.obter_atributo(palavra, None, definicao, 'exemplos')
                hiperonimo = [ ]
            elif fonte == 'wordnet':
                exemplos = definicao.examples()
                for lema in definicao.hypernyms()[0].lemma_names():
                    hiperonimo += lema.split('_')

            entrada += hiperonimo

            if usar_exemplos and False:
                for ex in exemplos: entrada += ex.split(' ')

            entrada = list(set(entrada))                
            palavras = rep_vetorial.obter_palavras_relacionadas(positivos=entrada, topn=30)

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
    rep_vet = RepresentacaoVetorial(configs)
    rep_vet.carregar_modelo(diretorio=configs['modelos']['word2vec-default'])

    bases_utilizadas = raw_input("Escolha a base para fazer a comparacao: 'trial' ou 'test': ")
    dir_gabarito = configs['semeval2007'][bases_utilizadas]['gold_file']
    dir_entrada = configs['semeval2007'][bases_utilizadas]['input']
    
    gabarito_tmp = validador.carregar_gabarito(dir_gabarito)

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

    casos_testes_list, gabarito_list, lexemas_list = [ ], [ ], [ ]

    resultados_persistiveis = [ ]

    if len(gabarito_list) != len(casos_testes_list):
        raise Exception("A quantidade de instancias de entrada estao erradas!")

    for lexema in casos_testes_dict:
        if lexema in casos_testes_dict and lexema in gabarito_dict:            
            casos_testes_list.append(casos_testes_dict[lexema])
            gabarito_list.append(gabarito_dict[lexema])
            lexemas_list.append(lexema)

    total_com_resposta = 0
    total_sem_resposta = 0

    usar_sinonimos_wordnet = usar_sinonimos_oxford = usar_sinonimos_word_embbedings= False

    if raw_input("Adicionar sinonimos Wordnet? s/N? ") == 's':
        usar_sinonimos_wordnet = True
    if raw_input("Adicionar sinonimos Oxford? s/N? ") == 's':
        usar_sinonimos_oxford = True
    if raw_input("Adicionar sinonimos WordEmbbedings? s/N? ") == 's':
        usar_sinonimos_word_embbedings = True

    total_candidatos = [ ]

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
                candidatos_selecionados_alvaro += alvaro.selec_candidatos(palavra, pos, fontes=['wordnet'])
            if usar_sinonimos_oxford == True:
                candidatos_selecionados_alvaro += alvaro.selec_candidatos(palavra, pos, fontes=['oxford'])
            if usar_sinonimos_word_embbedings == True:
                palavras_relacionadas = rep_vet.obter_palavras_relacionadas(positivos=[palavra], topn=max_resultados)
                palavras_relacionadas = [p[0] for p in palavras_relacionadas]
                candidatos_selecionados_alvaro += palavras_relacionadas

            total_candidatos.append(len(candidatos_selecionados_alvaro))
            candidatos_selecionados_alvaro = list(set(candidatos_selecionados_alvaro))

            # Respostas certas baseada na instancia de entrada
            gabarito_ordenado = sorted(gabarito_list[indice], key=lambda x: x[1], reverse=True)
            gabarito_ordenado = [reg[0] for reg in gabarito_ordenado]

            print("\nCASO ENTRADA: \n" + str((contexto, palavra, pos)))
            print("\nMEDIA DE SUGESTOES:\n%d" % (sum(total_candidatos)/len(total_candidatos)))
            print("\nRESPOSTAS CORRETAS:\n\n%s" % str(gabarito_ordenado))

            intersecao_tmp = list(set([gabarito_ordenado[0]]) & set(candidatos_selecionados_alvaro))
            lexema_candidatos[lexemas_list[indice]] = set(candidatos_selecionados_alvaro)

            if intersecao_tmp:
                total_com_resposta += 1
                print("\nINTERSECAO: %s" % str(intersecao_tmp))
                print("\nTOTAL PREDITOS CORRETAMENTE: %d" % (len(intersecao_tmp)))
            else:
                total_sem_resposta += 1

    arquivo_saida = open(dir_saida_seletor_candidatos, "w")

    for indice in resultados_persistiveis:
        # [['crazy', 3], ['fast', 1], ['very fast', 1], ['very quickly', 1], ['very rapidly', 1]]
        if tarefa == 'best':
            sugestoes = sorted(gabarito_list[indice], key=lambda x: x[1], reverse=True)[:1]
            sugestoes = [e[0] for e in sugestoes]
        elif tarefa == 'oot':
            sugestoes = sorted(gabarito_list[indice], key=lambda x: x[1], reverse=True)
            sugestoes = [[e[0] for e in sugestoes][0]]

            for s in lexema_candidatos[lexemas_list[indice]]:
                if not s in sugestoes: sugestoes.append(s)

        arquivo_saida.write("%s %s %s\n" % (lexemas_list[indice], "::" if tarefa == 'best' else ":::" ,";".join(sugestoes)))

    # Persistindo casos de entrada sem resposta corretamente
    for lexema in set(casos_testes_tmp.keys()) - set(lexemas_list):
        arquivo_saida.write(lexema + " ::\n")

    arquivo_saida.close()

    print("\n\nTotal com resposta: " + str(total_com_resposta))
    print("\nTotal sem resposta: " + str(total_sem_resposta))

def carregar_bases(configs, tipo_base):
    casos_testes = gabarito = None
    validador = VlddrSemEval(configs)

    # Carrega a base Trial para fazer os testes

    dir_gabarito = configs['semeval2007'][tipo_base]['gold_file']
    dir_entrada = configs['semeval2007'][tipo_base]['input']

    gabarito = validador.carregar_gabarito(dir_gabarito)
    casos_testes = validador.carregar_caso_entrada(dir_entrada)

    # gabarito_dict[lexelt cod] = [[palavra votos], [palavra votos], [palavra votos], ...]
    # casos_testes_dict[lexema cod] = [frase, palavra, pos]
    casos_testes_dict, gabarito_dict = {}, {}

    for lexelt in gabarito:
        lista = [ ]
        for sugestao in gabarito[lexelt]:
            voto = gabarito[lexelt][sugestao]
            lista.append([sugestao, voto])
        gabarito_dict[lexelt] = lista

    for lexelt in casos_testes:
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
    base_ox = BaseOx(cfgs)
    alvaro = AbordagemAlvaro(cfgs, base_ox, casador_manual)

    casos_testes_dict, gabarito_dict = carregar_bases(cfgs, "test")

    contador_instancias_validas = 0
    contador_instancias_invalidas = 0

    for lexelt in set(casos_testes_dict.keys())&set(gabarito_dict.keys()):
        frase, palavra, pos = casos_testes_dict[lexelt]
        frase = Util.descontrair(frase).replace("  ", " ")
        palavra = lexelt.split(".")[0]

        if fonte=='oxford':
            des_ox = DesOx(cfgs, base_ox)
            res_des = des_ox.cosine_lesk(frase, palavra, pos, nbest=True, usr_ex=True)
            contador_instancias_validas+=int(bool(sum([reg[1] for reg in res_des])))
        elif fonte=='wordnet':
            des_wn = DesWordnet(cfgs)
            contador_instancias_validas+=int(bool(sum([reg[1] for reg in des_wn.cosine_lesk(frase, palavra, pos, nbest=True)])))
        print("\n\nRESULTADO: " + str(contador_instancias_validas))

# Este metodo usa a abordagem do Alvaro sobre as bases do SemEval
# Ela constroi uma relacao (score) entre diferentes definicoes, possivelmente sinonimos
#   criterio = frequencia OU alvaro OU embbedings
def predizer_sins(cfgs, criterio='frequencia', usar_gabarito=True, indice=-1,
        fontes_def='oxford', tipo=None, max_ex=-1, usr_ex=False, aceitar_nulos=False):
    casador_manual = CasadorManual(cfgs)
    base_ox = BaseOx(cfgs)
    alvaro = AbordagemAlvaro(cfgs, base_ox, casador_manual)

    if max_ex == -1:
        max_ex = sys.maxint

    separador = "###"

    # Resultado de saida <lexelt : lista>
    predicao_final = dict()

    # Fonte para selecionar as definicoes e fonte para selecionar os candidatos
    # fontes_def, fontes_cands = raw_input("Digite a fonte para definicoes: "), ['oxford', 'wordnet']
    fontes_def, fontes_cands = fontes_def, ['oxford', 'wordnet']
    casos_testes_dict, gabarito_dict = carregar_bases(cfgs, tipo)

    if indice == -1:
        casos_testes_dict_tmp = list(casos_testes_dict.keys())    
    else: # SO O CASO DE ENTRADA INFORMADO
        casos_testes_dict_tmp = casos_testes_dict.keys()[:indice]

    vldr_se = VlddrSemEval(cfgs)
    todos_lexelts = list(set(casos_testes_dict_tmp)&set(gabarito_dict.keys()))
    indices_lexelts = [i for i in range(len(todos_lexelts))]

    for cont in indices_lexelts:
        lexelt = todos_lexelts[cont]
        frase, palavra, pos = casos_testes_dict[lexelt]
        frase = Util.descontrair(frase).replace("  ", " ")
        palavra = lexelt.split(".")[0]

        if usar_gabarito == True:
            cands = [e[0] for e in gabarito_dict[lexelt] if not Util.e_multipalavra(e[0])]
        else:
            cands = alvaro.selec_candidatos(palavra, pos, fontes=fontes_cands)
            cands = [p for p in cands if p.istitle() == False]

        cands = [p for p in cands if not Util.e_multipalavra(p)]

        print("Processando a entrada " + str(lexelt))
        print("%d / %d\n" % (cont+1, len(list(set(casos_testes_dict_tmp)&set(gabarito_dict.keys())))))

        #criterio='frequencia', usar_gabarito=True, indice=-1, fontes_def='oxford', tp=None, max_ex=-1, usr_ex=False
        #args_msg = (criterio, usar_gabarito, indice, str(fontes_def), max_ex, usr_ex)
        #print("Criterio=%s, Usar gabarito=%s, Indice=%d, Fontes Def=%s, MaxExemplos=%d, UsarExemplos=%s" % args_msg)

        if criterio == 'embbedings':
            rep_vet = RepresentacaoVetorial(cfgs)
            rep_vet.carregar_modelo(cfgs['modelos']['word2vec-default'], binario=True)

            res_tmp = rep_vet.obter_palavras_relacionadas(positivos=[lexelt.split('.')[0]], topn=200)
            predicao_final[lexelt] = [sin for sin, pontuacao in res_tmp if sin in cands]

        elif criterio == 'frequencia':
            cliente_ox = ClienteOxfordAPI(cfgs)

            cands_ponts = [ ]
            for sin in cands:
                try:
                    cands_ponts.append((sin, cliente_ox.obter_frequencia(sin)))
                except Exception, e:
                    print(e)
                    cands_ponts.append((sin, -1))

            res_predicao = [reg[0] for reg in sorted(cands_ponts, key=lambda x:x[1], reverse=True)]
            predicao_final[lexelt] = res_predicao

        elif criterio == 'alvaro':
            if fontes_def == 'oxford':
                des_ox = DesOx(cfgs, base_ox)
                res_desambiguacao = des_ox.cosine_lesk(frase, palavra, pos, usr_ex=usr_ex)
                # [[u'clean.Verb.1', u'Make clean; remove dirt, marks, or stains from.', []], 0.11]
            elif fontes_def == 'wordnet':
                des_wn = DesWordnet(cfgs)
                # [[u'huffy.s.02', u'roused to anger', []], 0.0]
                res_desambiguacao = des_wn.cosine_lesk(frase, palavra, pos=pos, nbest=True)                

            # Se o desambiguador consegue predizer o significado da palavra
            if sum([reg_des[1] for reg_des in res_desambiguacao]) > 0.00 or aceitar_nulos:
                rel_sinonimia = alvaro.iniciar(palavra, pos, frase, fontes_def=fontes_def,\
                 fontes_cands=fontes_cands, cands=cands, max_ex=max_ex, usr_ex=usr_ex)
                rel_sinonimia.reverse()

                #print((palavra, pos, frase))
                #for e in rel_sinonimia:
                #    print("\t- " + str(e))
                #raw_input("\n\n<enter>")

                res_agregado = dict()

                for res_des in res_desambiguacao:
                    label_des = res_des[0][0]
                    res_agregado[label_des] = list()

                for reg_sin in rel_sinonimia:
                    label_sin, label_des = reg_sin[:2]

                    if fontes_def == 'oxford':
                        label_des = label_des.split(";")[-1] # "definicao;war.Noun.1" -> "war.Noun.1"
                    elif fontes_def == 'wordnet':
                        label_des = label_des # label_des = war.n.1;war
                    
                    res_agregado[label_des].append(reg_sin)

                saida_sinonimos_tmp = [ ]

                # Iterando resultado de desambiguacao
                for res_des in res_desambiguacao:
                    label_des, def_des = res_des[0][:2]

                    rel_ordenada = sorted(res_agregado[label_des], key=lambda x :x[1], reverse=False)
                    res_agregado_tmp = dict()

                    # Iterando relacao de sinonimia computada anteriormente
                    for reg_sin in rel_ordenada:
                        def_sin = reg_sin[0]
                        def_sin, lema_sin = def_sin.split(';')[:-1][0], def_sin.split(';')[-1]
                        pont_rel = reg_sin[3]

                        ch_defs = "%s%s%s" % (reg_sin[0], separador, reg_sin[1])

                        # Agregando pontuacoes de frases de exemplos distintas
                        if not ch_defs in res_agregado_tmp:
                            res_agregado_tmp[ch_defs] = list()

                        # Adicionando pontuacao da nova frase
                        res_agregado_tmp[ch_defs].append(pont_rel)

                    res_agregado_tmp_array = [(ch_defs, media(res_agregado_tmp[ch_defs])) for ch_defs in res_agregado_tmp]
                    res_agregado_tmp = sorted(res_agregado_tmp_array, key=lambda x: x[1], reverse=True)

                    for reg_agregado in res_agregado_tmp:
                        def_des = reg_agregado[0].split(separador)[0]
                        def_des, lema_des = def_des.split(';')[:-1][0], def_des.split(';')[-1]

                        pontuacao_agregado = reg_agregado[1]

                        # Se o sinonimo/por definicao tem score
                        if pontuacao_agregado > 0.00 or aceitar_nulos:
                            # Wordnet: 'angry.s.02', u'furious'
                            # Oxford: (u'Having all the necessary or appropriate parts.', u'complete')
                            try:
                                if fontes_def == 'oxford':
                                    sins_reg = base_ox.obter_sins(lema_des, def_des)
                                elif fontes_def == 'wordnet':
                                    # Wordnet lema_des = name synset
                                    sins_reg = wn.synset(def_des).lemma_names()
                            except:
                                raw_input('\nExcecao aqui para o lema %s!' % lema_des)
                                sins_reg = [ ]

                            if len(sins_reg) > 0: saida_sinonimos_tmp += sins_reg

                saida_sins = [ ]
                for sin in saida_sinonimos_tmp:
                    if usar_gabarito == True:
                        if sin in [p[0] for p in gabarito_dict[lexelt]] and not sin in saida_sins:
                            saida_sins.append(sin)
                    else:
                        saida_sins.append(sin)

                predicao_final[lexelt] = saida_sins
            else:
                predicao_final[lexelt] = [ ]

            if lexelt in predicao_final:
                print("Lexelt %s recebeu a sugestao %s\n" % (lexelt, str(predicao_final[lexelt])))
            else:
                print("Lexelt %s nao possui sugestoes!")

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
    casador.iniciar_casamento(raw_input('Digite o termo: '), raw_input('POS: '))       


#807 = sem exemplos
#1669 = com exemplos
if __name__ == '__main__':
    if len(argv) < 2:
        print('\nParametrizacao errada!\nTente py ./main <dir_config_file>\n\n')
        exit(0)

    Util.cls()
    cfgs = Util.carregar_cfgs(argv[1])
    vldr_se = VlddrSemEval(cfgs) # Validador SemEval 2007

    dir_saida_abordagem = "/home/isaias/Desktop/exps"
    todos_criterios = ['alvaro']
    qtdes_exemplos = [1]
    qtde_sugestoes_best = [3]
    qtde_sugestoes_oot = [1,2,3]
    todas_fontes_def = ['oxford', 'wordnet']
    tipos_base = ['test']

    flags_usar_gabarito = [True]
    flag_aceitar_nulos = [True, False]
    flag_usr_exemplos = [False,]

    #indice = int(raw_input("Total de indices: "))
    indice = -1

    exe = raw_input("[R]ealizar predicao ou [F] formatar submissoes? > ").lower()

    if not exe in ['r', 'f']:
        raise Exception('Opcao invalida!')

    res_best = vldr_se.avaliar_parts_orig("best").values()
    res_oot = vldr_se.avaliar_parts_orig("oot").values()
    
    for crit in todos_criterios:
        for usr_gab in flags_usar_gabarito:
            for tipo in tipos_base:
                for max_ex in qtdes_exemplos:
                    for aceitar_nulos in flag_aceitar_nulos:
                        for usr_ex in flag_usr_exemplos:
                            for fonte_def in todas_fontes_def:
                                predicao=casos=gabarito = set()

                                if exe=='r':
                                    predicao, casos, gabarito = predizer_sins(cfgs, indice=indice, usar_gabarito=usr_gab, criterio=crit,\
                                    tipo=tipo, max_ex=max_ex, usr_ex=usr_ex, fontes_def=fonte_def, aceitar_nulos=aceitar_nulos)

                                for cont in qtde_sugestoes_oot:
                                    nome_abrdgm = cfgs['padrao_nome_submissao']
                                    nome_abrdgm = nome_abrdgm % (crit, usr_gab, tipo, max_ex, usr_ex, fonte_def, aceitar_nulos, 'oot')

                                    vldr_se.formtr_submissao(dir_saida_abordagem+"/"+nome_abrdgm, predicao, cont, ":::")
                                    if Util.arq_existe(dir_saida_abordagem, nome_abrdgm):
                                        try:
                                            res_oot.append(vldr_se.obter_score(dir_saida_abordagem, nome_abrdgm))
                                        except: pass
                                            
                                for cont in qtde_sugestoes_best:
                                    nome_abrdgm = cfgs['padrao_nome_submissao']
                                    nome_abrdgm = nome_abrdgm % (crit, usr_gab, tipo, max_ex, usr_ex, fonte_def, aceitar_nulos, 'best')
                                    
                                    vldr_se.formtr_submissao(dir_saida_abordagem+"/"+nome_abrdgm, predicao, 1, "::")
                                    if Util.arq_existe(dir_saida_abordagem, nome_abrdgm):
                                        try:
                                            res_best.append(vldr_se.obter_score(dir_saida_abordagem, nome_abrdgm))
                                        except: pass

    res_tarefas = {'best': res_best, 'oot': res_oot} 

    for k in res_tarefas:
        res_tarefa = res_tarefas[k]
        chave = raw_input("\nEscolha a chave pra ordenara saida "+k.upper()+": " + str(res_tarefa[0].keys()) + ": ")

        res_tarefa = sorted(res_best, key=itemgetter(chave), reverse=True) 
        print(chave.upper() + "\t-----------------------")

        for e in res_tarefa:
            print(e['nome'])
            etmp = dict(e); del etmp['nome']
            print(etmp)
            print('\n')

        print("\n")

    print('\n\nFim do __main__')
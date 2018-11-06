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

def desambiguar_word_embbedings(configs, ctx, palavra):
    rep_vetorial = RepresentacaoVetorial(configs)
    rep_vetorial.carregar_modelo(configs['modelos']['word2vec-default'])

    p = ctx.split(" ")

    palavras_correlatas = rep_vetorial.obter_palavras_relacionadas(positivos=[palavra], negativos=[ ], topn=60)
    palavras_correlatas_ctx = rep_vetorial.obter_palavras_relacionadas(positivos=p, negativos=[ ], topn=60)
    palavras_correlatas_ctx = [ ]

    for reg in palavras_correlatas:
        print("\t- " + str(reg))
    print("\n_______________________________________________________\n")
    for reg in palavras_correlatas_ctx:
        print("\t- " + str(reg))

    print("\n")


def criar_vetores_wordnet(configs):
    rep_vetorial = RepresentacaoVetorial(configs)
    rep_vetorial.carregar_modelo(configs['modelos']['word2vec-default'])

    while raw_input("\nContinuar? S/n: ").lower() != 'n':
        p = raw_input("Positivas: ").split(",")
        n = raw_input("Negativas: ").split(",")

        res = rep_vetorial.obter_palavras_relacionadas(positivos=p, negativos=None, topn= 40)

        print([e[0] for e in res])

    
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

    casos_testes_list = [ ]
    gabarito_list = [ ]
    lexemas_list = [ ]

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
                candidatos_selecionados_alvaro += alvaro.selecionar_candidatos(palavra, pos, fontes=['wordnet'])
            if usar_sinonimos_oxford == True:
                candidatos_selecionados_alvaro += alvaro.selecionar_candidatos(palavra, pos, fontes=['oxford'])
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

# Este metodo usa a abordagem do Alvaro sobre as bases do SemEval
# Ela constroi uma relacao (score) entre diferentes definicoes, possivelmente sinonimos
#   criterio = frequencia OU alvaro OU embbedings
def predizer_sins(cfgs, criterio='frequencia', usar_gabarito=True, indice=-1, fontes_def='oxford', tp=None, max_ex=-1):
    casador_manual = CasadorManual(cfgs)
    base_ox = BaseOx(cfgs)
    alvaro = AbordagemAlvaro(cfgs, base_ox, casador_manual)

    if max_ex == -1: max_ex = sys.maxint

    separador = "###"

    # Resultado de saida <lexelt : lista>
    predicao_final = dict()

    # Fonte para selecionar as definicoes e fonte para selecionar os candidatos
    # fontes_def, fontes_cands = raw_input("Digite a fonte para definicoes: "), ['oxford', 'wordnet']
    fontes_def, fontes_cands = fontes_def, ['oxford', 'wordnet']
    casos_testes_dict, gabarito_dict = carregar_bases(cfgs, tp)

    # TODOS CASOS DE ENTRADA
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
            cands = alvaro.selecionar_candidatos(palavra, pos, fontes=fontes_cands)
            cands = [p for p in cands if p.istitle() == False]

        cands = [p for p in cands if not Util.e_multipalavra(p)]

        print("Processando a entrada " + str(lexelt))
        print("%d / %d\n" % (cont+1, len(list(set(casos_testes_dict_tmp) & set(gabarito_dict.keys())))))
        cont += 1

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

            gabs = sorted(gabarito_dict[lexelt], key=lambda x: x[1], reverse=True)

            try:
                if gabs[0][0] == res_predicao[0]: certos += 1
                else: errados += 1
            except: pass

        elif criterio == 'alvaro':
            res_sinonimia = alvaro.iniciar(palavra, pos, frase, fontes_def=fontes_def, fontes_cands=fontes_cands, cands=cands, max_ex=max_ex)
            res_sinonimia.reverse()

            if fontes_def == 'oxford':
                des_ox = DesOx(cfgs, base_ox)
                res_desambiguacao = des_ox.cosine_lesk(frase, palavra, pos, usar_exemplos=False)
            elif fontes_def == 'wordnet':
                des_wn = DesWordnet(configs)
                res_desambiguacao = des_wn.cosine_lesk(frase, palavra, pos=pos, nbest=True)
                res_desambiguacao = des_wn.converter_resultado(res_desambiguacao_wn)

            res_agregado = dict()

            for res_des in res_desambiguacao:
                label_des, def_des, frases_reg, pontuacao_reg = res_des[0][0], res_des[0][1], res_des[0][2], res_des[1]
                if not label_des in res_agregado:
                    res_agregado[label_des] = list()

            for reg_sin in res_sinonimia:
                label_des = reg_sin[1].split(";")[-1]
                res_agregado[label_des].append(reg_sin)
            
            definicoes_sinonimos = set()
            saida_sinonimos_tmp = [ ]

            # ITERANDO RESULTADO DAS DESAMBIGUACAO
            for res_des in res_desambiguacao:
                label_des, def_des, frases_reg, pontuacao_reg = res_des[0][0], res_des[0][1], res_des[0][2], res_des[1]
                rel_ordenada = sorted(res_agregado[label_des], key=lambda x :x[1], reverse=False)

                res_agregado_tmp = dict()

                # ITERANDO RELACAO DE SINONIMIA COMPUTADA ANTERIORMENTE
                for reg_sin in rel_ordenada:
                    def_sin = reg_sin[0]
                    def_sin, lema_sin = def_sin.split(';')[:-1][0], def_sin.split(';')[-1]
                    pontuacao_tmp = reg_sin[3]
                    chave_definicoes = "%s%s%s" % (reg_sin[0], separador, reg_sin[1])

                    # Agregando pontuacoes de frases de exemplos distintas
                    if not chave_definicoes in res_agregado_tmp:
                        res_agregado_tmp[chave_definicoes] = list()

                    # Adicionando pontuacao da nova frase
                    res_agregado_tmp[chave_definicoes].append(pontuacao_tmp)

                # Agregando scores
                res_agregado_tmp_array = [ ]
                for chave_definicoes in res_agregado_tmp:
                    res_agregado_tmp_array.append((chave_definicoes, media(res_agregado_tmp[chave_definicoes])))

                # Ordenando agregado
                res_agregado_tmp = sorted(res_agregado_tmp_array, key=lambda x: x[1], reverse=True)

                for reg_agregado in res_agregado_tmp:
                    def_des = reg_agregado[0].split(separador)[0]
                    def_des, lema_des = def_des.split(';')[:-1][0], def_des.split(';')[-1]

                    try:
                        sins_reg = base_ox.obter_sins(lema_des, def_des)
                    except:
                        sins_reg = [ ]

                    saida_sinonimos_tmp += sins_reg

            saida_sins = [ ]
            for sin in saida_sinonimos_tmp:
                if usar_gabarito == True:
                    if sin in [p[0] for p in gabarito_dict[lexelt]] and not sin in saida_sins:
                        saida_sins.append(sin)
                else:
                    saida_sins.append(sin)

            predicao_final[lexelt] = saida_sins

    # Predicao, caso de entrada, gabarito
    return predicao_final, casos_testes_dict, gabarito_dict

def testar_casamento(configs):
    base_unificada = BaseOx(configs)
    casador = CasadorConceitos(configs, base_unificada)

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

if __name__ == '__main__':
    if len(argv) < 2:
        print('\nParametrizacao errada!')
        print('Tente py ./main <dir_config_file>\n\n')
        exit(0)

    Util.cls()
    cfgs = Util.carregar_configuracoes(argv[1])
    vldr_se = VlddrSemEval(cfgs) # Validador SemEval 2007

    if False:
        import Experimentalismo
        Experimentalismo.ler_entrada(cfgs)
        #medir_seletor_candidatos(configs)
        exit(0)
    if False:
        criar_vetores_wordnet(cfgs)
    if False:
        palavra = raw_input("Palavra: ")
        ns = raw_input(str(wn.synsets(palavra)) + ": ")
        print("\n")
        rep_vetorial = RepresentacaoVetorial(cfgs)
        rep_vetorial.carregar_modelo(cfgs['modelos']['word2vec-default'])

        for p in rep_vetorial.criar_vetor_synset(palavra, ns):
            print(p)

        exit(0)

    dir_saida_abordagem = "/home/isaias/Desktop/exps"
    todos_criterios = ['alvaro']
    flags_usar_gabarito = [True]
    qtdes_exemplos = [1,]
    qtde_sugestoes_oot = [1,2,3]
    qtde_sugestoes_best = [3]
    indice = 100

    exe = raw_input("[R]ealizar predicao? > ")

    if True:
        resultados_best = vldr_se.avaliar_parts_orig("best").values()
        resultados_oot = vldr_se.avaliar_parts_orig("oot").values()
        
        for crit in todos_criterios:
            for usar_gabarito in flags_usar_gabarito:
                # Maximo de exemplos para criar a relacao de sinonimia
                for max_ex in qtdes_exemplos:
                    predicao=casos=gabarito= set()

                    if exe=='r':
                        predicao, casos, gabarito = predizer_sins(cfgs, indice=indice, usar_gabarito=usar_gabarito, criterio=crit, tp='test', max_ex=max_ex)

                    padrao_nome_abordagem = "%s-%d-%s-Exemplos:%d.%s"

                    # Out-of-Ten (filtrando quantas predicoes sao necessarias)
                    for cont in qtde_sugestoes_oot:
                        nome_abordagem = padrao_nome_abordagem % (crit, cont, "AUTO" if usar_gabarito else "NOAUTO", max_ex, "oot")
                        vldr_se.formtr_submissao(dir_saida_abordagem+"/"+nome_abordagem, predicao, cont, ":::")
                        if Util.arq_existe(dir_saida_abordagem, nome_abordagem):
                            try:
                                resultados_oot.append(vldr_se.obter_score(dir_saida_abordagem, nome_abordagem))
                            except: pass


                    # Best
                    for cont in qtde_sugestoes_best:
                        nome_abordagem = padrao_nome_abordagem % (crit, cont, "AUTO" if usar_gabarito else "NOAUTO", max_ex, "best")
                        vldr_se.formtr_submissao(dir_saida_abordagem+"/"+nome_abordagem, predicao, 1, "::")
                        if Util.arq_existe(dir_saida_abordagem, nome_abordagem):
                            try:
                                resultados_best.append(vldr_se.obter_score(dir_saida_abordagem, nome_abordagem))
                            except: pass

    if raw_input("Calcular BEST? s/N? ") == "s":
        chave = ""
        while chave == "":
            chave = raw_input("\nEscolha a chave pra ordenara saida BEST: " + str(resultados_best[0].keys()) + ": ")
            print("\n")
        resultados_best = sorted(resultados_best, key=itemgetter(chave), reverse=True) 
        print(chave.upper() + "\t-----------------------")
        for e in resultados_best: print(e)

    print("\n\n\n")

    if raw_input("Calcular Out-of-Ten? s/N? ") == "s":
        chave = ""
        while chave == "":
            chave = raw_input("\nEscolha a chave pra ordenara saida OOT: " + str(resultados_oot[0].keys()) + ": ")
            print("\n")
        resultados_oot = sorted(resultados_oot, key=itemgetter(chave), reverse=True)        
        print(chave.upper() + "\t-----------------------")
        for e in resultados_oot:
            print(e)

    exit(0)

    if False:
        desambiguar_word_embbedings(cfgs, raw_input("Frase: "), raw_input("Palavra: "))
    exit(0)

    # Realiza o SemEval2007 para as minhas abordagens implementadas (baselines)
    #print('\nIniciando o Semantic Evaluation 2007!')
    #iniciar_se2007(configs)
    #print('\n\nSemEval2007 realizado!\n\n')
    aplicar_metrica_gap = False

    if aplicar_metrica_gap:
        validador_gap = GeneralizedAveragePrecisionMelamud(cfgs)
        # Obtem os gabaritos informados por ambos
        # anotadores no formato <palavra.pos.id -> gabarito>
        gold_rankings_se2007 = obter_gabarito_rankings_semeval(cfgs)

        # Lista todos aquivos .best ou .oot do SemEval2007
        lista_todas_submissoes_se2007 = Util.list_arqs(cfgs['dir_saidas_rankeador'])

        # Usa, originalmente, oot
        lista_todas_submissoes_se2007 = [s for s in lista_todas_submissoes_se2007 if '.oot' in s]
        submissoes_se2007_carregadas = dict()

        resultados_gap = dict()

        for dir_submissao_se2007 in lista_todas_submissoes_se2007:
            submissao_carregada = carregar_arquivo_submissao_se2007(cfgs, dir_submissao_se2007)
            nome_abordagem = dir_submissao_se2007.split('/').pop()

            submissoes_se2007_carregadas[nome_abordagem] = submissao_carregada
            resultados_gap[nome_abordagem] = dict()

        for nome_abordagem in submissoes_se2007_carregadas:
            minha_abordagem = submissoes_se2007_carregadas[nome_abordagem]
            
            for lema in gold_rankings_se2007:
                ranking_gold = [(k, gold_rankings_se2007[lema][k]) for k in gold_rankings_se2007[lema]]
                if lema in minha_abordagem:
                    meu_ranking = [(k, minha_abordagem[lema][k]) for k in minha_abordagem[lema]]
                    pontuacao_gap = validador_gap.calcular(ranking_gold, meu_ranking)

                    resultados_gap[nome_abordagem][lema] = pontuacao_gap

            # GAP medio
            resultados_gap[nome_abordagem] = statistics.mean(resultados_gap[nome_abordagem].values())

        for nome_abordagem in resultados_gap:
            gap_medio = resultados_gap[nome_abordagem]
            print('%s\t\tGAP Medio: %s' % (nome_abordagem, str(gap_medio)))

        print('\n\n\nFim do __main__')


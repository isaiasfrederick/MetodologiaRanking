#! coding: utf-8
from Utilitarios import Utils
from SemEval2007 import *
from sys import argv
import statistics
import traceback
import re
from pywsd.lesk import cosine_lesk
from operator import itemgetter
from operator import itemgetter

# Experimentacao
from ModuloDesambiguacao.DesambiguadorOxford import DesambiguadorOxford
from ModuloDesambiguacao.DesambiguadorUnificado import DesambiguadorUnificado
from ModuloDesambiguacao.DesambiguadorWordnet import DesambiguadorWordnet
from ModuloBasesLexicas.ModuloClienteOxfordAPI import BaseUnificadaOxford
from ModuloBasesLexicas.ModuloClienteOxfordAPI import ClienteOxfordAPI
from RepositorioCentralConceitos import CasadorConceitos
from nltk.corpus import wordnet
# Fim pacotes da Experimentacao

# Carrega o gabarito o arquivo de input
from SemEval2007 import ValidadorSemEval

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


def utilizar_word_embbedings(configs, usar_exemplos=True, usar_hiperonimo=True, fonte='wordnet'):
    base_ox = BaseUnificadaOxford(configs)
    rep_vetorial = RepresentacaoVetorial(configs)
    rep_vetorial.carregar_modelo(configs['modelos']['word2vec-default'])

    while raw_input("\nContinuar? S/n: ").lower() != 'n':
        palavra = raw_input("Palavra: ")

        if fonte == 'oxford':
            todas_definicoes = base_ox.obter_todas_definicoes(palavra)
        elif fonte == 'wordnet':
            todas_definicoes = wn.synsets(palavra)

        for definicao in todas_definicoes:
            entrada = [ ]
            todos_lemas = [ ]

            if fonte == 'oxford':
                todos_lemas = base_ox.obter_sinonimos(palavra, definicao)
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
    validador = ValidadorSemEval(configs)
    contadores = Utils.carregar_json(configs['leipzig']['dir_contadores'])

    #dir_saida_seletor_candidatos = raw_input("Diretorio saida arquivo seletor candidatos: ")
    dir_saida_seletor_candidatos = "/home/isaias/saida-oot.oot"

    base_ox = BaseUnificadaOxford(configs)
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

    validador_semeval2007 = ValidadorSemEval(configs)
    casos_testes_tmp = validador_semeval2007.ler_entrada_teste(dir_entrada)

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

            sugestoes = sugestoes[:10]

        arquivo_saida.write("%s %s %s\n" % (lexemas_list[indice], "::" if tarefa == 'best' else ":::" ,";".join(sugestoes)))

    # Persistindo casos de entrada sem resposta corretamente
    for lexema in set(casos_testes_tmp.keys()) - set(lexemas_list):
        arquivo_saida.write(lexema + " ::\n")

    arquivo_saida.close()

    print("\n\nTotal com resposta: " + str(total_com_resposta))
    print("\nTotal sem resposta: " + str(total_sem_resposta))


def carregar_bases(configs, tipo_base):
    casos_testes = gabarito = None
    validador = ValidadorSemEval(configs)

    # Carrega a base Trial para fazer os testes

    dir_gabarito = configs['semeval2007'][tipo_base]['gold_file']
    dir_entrada = configs['semeval2007'][tipo_base]['input']

    gabarito = validador.carregar_gabarito(dir_gabarito)
    casos_testes = validador.ler_entrada_teste(dir_entrada)

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
def predizer_sinonimos(configs, criterio='frequencia', usar_gabarito=True, indice=-1, fontes_def='oxford', tipo_base=None):
    casador_manual = CasadorManual(configs)
    base_ox = BaseUnificadaOxford(configs)
    alvaro = AbordagemAlvaro(configs, base_ox, casador_manual)

    separador = "###"

    # Resultado de saida <lexelt : lista>
    resultado_geral = dict()

    # Fonte para selecionar as definicoes e fonte para selecionar os candidatos
    # fontes_def, fontes_cands = raw_input("Digite a fonte para definicoes: "), ['oxford', 'wordnet']
    fontes_def, fontes_cands = fontes_def, ['oxford', 'wordnet']
    casos_testes_dict, gabarito_dict = carregar_bases(configs, tipo_base)

    # TODOS CASOS DE ENTRADA
    if indice == -1:
        casos_testes_dict_tmp = list(casos_testes_dict.keys())    
    else: # SO O CASO DE ENTRADA INFORMADO
        casos_testes_dict_tmp = [casos_testes_dict.keys()[indice]]

    contador_instancias_nulas = 0
    cont = 1

    # A chave tem que estar em ambos objetos para nao excecao na linha 329
    for lexelt in list(set(casos_testes_dict_tmp) & set(gabarito_dict.keys())):
        frase, palavra, pos = casos_testes_dict[lexelt]
        frase = Utils.descontrair(frase).replace("  ", " ")
        # Palavra tem que estar inflexionada
        palavra = lexelt.split(".")[0]

        if usar_gabarito == True:
            cands = [e[0] for e in gabarito_dict[lexelt] if not Utils.e_multipalavra(e[0])]
        else:
            cands = alvaro.selecionar_candidatos(palavra, pos, fontes=fontes_cands)
            cands = [p for p in cands if p.istitle() == False]

        cands = [p for p in cands if not Utils.e_multipalavra(p)]

        print("Processando a entrada " + str(lexelt))
        print("%d / %d\n" % (cont, len(list(set(casos_testes_dict_tmp) & set(gabarito_dict.keys())))))
        cont += 1

        if criterio == 'embbedings':
            rep_vet = RepresentacaoVetorial(configs)
            rep_vet.carregar_modelo(configs['modelos']['word2vec-default'], binario=True)

            res_tmp = rep_vet.obter_palavras_relacionadas(positivos=[lexelt.split('.')[0]], topn=200)
            resultado_geral[lexelt] = [sin for sin, pontuacao in res_tmp if sin in cands]

        elif criterio == 'frequencia':
            cliente_ox = ClienteOxfordAPI(configs)

            cands_ponts = [ ]
            for sin in cands:
                try:
                    cands_ponts.append((sin, cliente_ox.obter_frequencia(sin)))
                except:
                    cands_ponts.append((sin, -1))

            res_predicao = [reg[0] for reg in sorted(cands_ponts, key=lambda x:x[1], reverse=True)]
            resultado_geral[lexelt] = res_predicao

        elif criterio == 'alvaro':
            res_sinonimia = alvaro.iniciar(palavra, pos, frase, fontes_def=fontes_def, fontes_cands=fontes_cands, cands=cands)
            res_sinonimia.reverse()

            if fontes_def == 'oxford':
                desambiguador = DesambiguadorOxford(configs, base_ox)
                res_desambiguacao = desambiguador.cosine_lesk(frase, palavra, pos, usar_exemplos=False)
            elif fontes_def == 'wordnet':
                res_desambiguacao = cosine_lesk(frase, palavra, pos=pos, nbest=True)

            try:
                peso_ini, peso_fim = res_desambiguacao[0][1], res_desambiguacao[-1][1]
                if peso_ini == 0:
                    contador_instancias_nulas += 1
            except Exception, e:
                contador_instancias_nulas += 1

            resultado_agregado = dict()

            for sin in res_desambiguacao:
                definicao_label, definicao_reg, frases_reg, pontuacao_reg = sin[0][0], sin[0][1], sin[0][2], sin[1]
                if not definicao_label in resultado_agregado:
                    resultado_agregado[definicao_label] = list()

            for reg_sin in res_sinonimia:
                definicao_label = reg_sin[1].split(";")[-1]
                resultado_agregado[definicao_label].append(reg_sin)
            
            definicoes_sinonimos = set()
            saida_sinonimos_tmp = [ ]

            # ITERANDO RESULTADO DAS DESAMBIGUACAO
            for sin in res_desambiguacao:
                definicao_label, definicao_reg, frases_reg, pontuacao_reg = sin[0][0], sin[0][1], sin[0][2], sin[1]
                relacao_ordenada = sorted(resultado_agregado[definicao_label], key=lambda x :x[1], reverse=False)

                res_agregado_tmp = dict()

                # ITERANDO RELACAO DE SINONIMIA COMPUTADA ANTERIORMENTE
                for reg_sin in relacao_ordenada:
                    def_sin = reg_sin[0]
                    def_sin, lema_sin = def_sin.split(';')[:-1][0], def_sin.split(';')[-1]

                    pontuacao_tmp = reg_sin[3]
                    chave_definicoes = "%s%s%s" % (reg_sin[0], separador, reg_sin[1])

                    # AGREGANDO PONTUACOES DE FRASES DE EXEMPLOS DISTINTAS
                    if not chave_definicoes in res_agregado_tmp:
                        res_agregado_tmp[chave_definicoes] = list()

                    # ADICIONANDO PONTUACAO DA NOVA FRASE
                    res_agregado_tmp[chave_definicoes].append(pontuacao_tmp)

                # AGREGANDO SCORES NESTE LACO
                res_agregado_tmp_array = [ ]
                for chave_definicoes in res_agregado_tmp:
                    # AGREGANDO A MEDIA DA PONTUACAO DAS FRASES
                    media_tmp = sum(res_agregado_tmp[chave_definicoes]) / len(res_agregado_tmp[chave_definicoes])
                    # PAR <def1, def2> : pontuacao
                    res_agregado_tmp_array.append((chave_definicoes, media_tmp))

                # ORDENANDO AGREGADO
                res_agregado_tmp = sorted(res_agregado_tmp_array, key=lambda x: x[1], reverse=True)

                for sin in res_agregado_tmp:
                    def_reg = sin[0].split(separador)[0]
                    def_reg, lema_reg = def_reg.split(';')[:-1][0], def_reg.split(';')[-1]

                    sins_reg = base_ox.obter_sinonimos(lema_reg, def_reg)
                    if len(sins_reg) > 0:
                        saida_sinonimos_tmp += sins_reg
                        #saida_sinonimos.append(sins_reg[0]) #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

            saida_sinonimos = [ ]
            for sin in saida_sinonimos_tmp:
                if usar_gabarito == True:
                    if sin in [p[0] for p in gabarito_dict[lexelt]] and not sin in saida_sinonimos:
                        saida_sinonimos.append(sin)
                else:
                    saida_sinonimos.append(sin)

            resultado_geral[lexelt] = saida_sinonimos

    # MINHA SUGESTAO, CASO DE ENTRADA, GABARITO
    return resultado_geral, casos_testes_dict, gabarito_dict

def testar_casamento(configs):
    base_unificada = BaseUnificadaOxford(configs)
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

    Utils.limpar_console()
    configs = Utils.carregar_configuracoes(argv[1])

    if False:
        validador = ValidadorSemEval(configs)
        fonte = raw_input("Fonte: ")
        utilizar_word_embbedings(configs, usar_exemplos=True, usar_hiperonimo=True, fonte=fonte)

    validador = ValidadorSemEval(configs)

    if True:
        for criterio in ['alvaro']:#, 'embbedings', 'frequencia']:
            predicao, casos, gabarito = predizer_sinonimos(configs, usar_gabarito=False, criterio=criterio, indice=-1, tipo_base='test')
            #(self, dir_arquivo_saida, entrada, limite_resposta, separador):
            # OOT
            nome_abordagem = "%s.%s" % (criterio, "oot")
            validador.formatar_submissao_final("/home/isaias/Desktop/" + nome_abordagem, predicao, 10, ":::")
            # BEST
            nome_abordagem = "%s.%s" % (criterio, "best")
            validador.formatar_submissao_final("/home/isaias/Desktop/" + nome_abordagem, predicao, 1, "::")

    todos_resultados_best = validador.obter_score_participantes_originais("best").values()
    #todos_resultados_best.append(validador.obter_score("/home/isaias/Desktop", "embbedings.best"))
    #todos_resultados_best.append(validador.obter_score("/home/isaias/Desktop", "frequencia.best"))
    todos_resultados_best.append(validador.obter_score("/home/isaias/Desktop", "alvaro.best"))

    chave = ""
    while chave == "":
        chave = raw_input("\nEscolha a chave pra ordenar: " + str(todos_resultados_best[0].keys()) + ": ")
        print("\n")

    todos_resultados_best = sorted(todos_resultados_best, key=itemgetter(chave), reverse=True) 

    print(chave.upper() + "\t-----------------------")
    for e in  todos_resultados_best: print(e)
    raw_input("\n\n\n<enter>")

    print("\n\n\n")
    todos_resultados_oot = validador.obter_score_participantes_originais("oot").values()
    #todos_resultados_oot.append(validador.obter_score("/home/isaias/Desktop", "embbedings.oot"))
    #todos_resultados_oot.append(validador.obter_score("/home/isaias/Desktop", "frequencia.oot"))
    todos_resultados_oot.append(validador.obter_score("/home/isaias/Desktop", "alvaro.oot"))

    chave = ""
    while chave == "":
        chave = raw_input("\nEscolha a chave pra ordenar: " + str(todos_resultados_oot[0].keys()) + ": ")
        print("\n")
       
    todos_resultados_oot = sorted(todos_resultados_oot, key=itemgetter(chave), reverse=True) 

    print(chave.upper() + "\t-----------------------")
    for e in  todos_resultados_oot: print(e)
    raw_input("\n\n\n<enter>")

    exit(0)

    if False:
        desambiguar_word_embbedings(configs, raw_input("Frase: "), raw_input("Palavra: "))
    exit(0)

    # Realiza o SemEval2007 para as minhas abordagens implementadas (baselines)
    #print('\nIniciando o Semantic Evaluation 2007!')
    #iniciar_se2007(configs)
    #print('\n\nSemEval2007 realizado!\n\n')
    aplicar_metrica_gap = False

    if aplicar_metrica_gap:
        validador_gap = GeneralizedAveragePrecisionMelamud(configs)
        # Obtem os gabaritos informados por ambos
        # anotadores no formato <palavra.pos.id -> gabarito>
        gold_rankings_se2007 = obter_gabarito_rankings_semeval(configs)

        # Lista todos aquivos .best ou .oot do SemEval2007
        lista_todas_submissoes_se2007 = Utils.listar_arquivos(configs['dir_saidas_rankeador'])

        # Usa, originalmente, oot
        lista_todas_submissoes_se2007 = [s for s in lista_todas_submissoes_se2007 if '.oot' in s]
        submissoes_se2007_carregadas = dict()

        resultados_gap = dict()

        for dir_submissao_se2007 in lista_todas_submissoes_se2007:
            submissao_carregada = carregar_arquivo_submissao_se2007(configs, dir_submissao_se2007)
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


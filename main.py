#! coding: utf-8
from Utilitarios import Utilitarios
from SemEval2007 import *
from sys import argv
import statistics
import traceback
import re
from pywsd.lesk import cosine_lesk

# Experimentacao
from ModuloDesambiguacao.DesambiguadorOxford import DesambiguadorOxford
from ModuloDesambiguacao.DesambiguadorUnificado import DesambiguadorUnificado
from ModuloDesambiguacao.DesambiguadorWordnet import DesambiguadorWordnet
from ModuloBasesLexicas.ModuloClienteOxfordAPI import BaseUnificadaObjetosOxford
from RepositorioCentralConceitos import CasadorConceitos
from nltk.corpus import wordnet
# Fim pacotes da Experimentacao

# Carrega o gabarito o arquivo de input
from SemEval2007 import obter_gabarito_rankings_semeval, carregar_arquivo_submissao_se2007
from Validadores import ValidadorRankingSemEval2007

# Testar Abordagem Alvaro
from Abordagens.AbordagemAlvaro import AbordagemAlvaro
from Abordagens.RepresentacaoVetorial import RepresentacaoVetorial
from CasadorManual import CasadorManual

wn = wordnet

""" Este metodo testa a abordagem do Alvaro em carater investigativo
sobre o componente que escolhe os sinonimos a serem utilizados """
def medir_seletor_candidatos(configs):
    contadores = Utilitarios.carregar_json(configs['leipzig']['dir_contadores'])

    dir_saida_seletor_candidatos = raw_input("Diretorio saida arquivo seletor candidatos: ")

    base_unificada = BaseUnificadaObjetosOxford(configs)
    abordagem_alvaro = AbordagemAlvaro(configs, base_unificada, CasadorManual(configs))
    representacao_vetorial = RepresentacaoVetorial(configs)
    representacao_vetorial.carregar_modelo(diretorio="/mnt/ParticaoAlternat/Bases/Modelos/vectors.bin")

    bases_utilizadas = raw_input("Escolha a base para fazer a comparacao: 'trial' ou 'test': ")

    if bases_utilizadas == "trial":
        dir_gabarito = configs['semeval2007']['trial']['gold_file']
        dir_entrada = configs['semeval2007']['trial']['scorer']
    elif bases_utilizadas == "test":
        dir_gabarito = "/mnt/ParticaoAlternat/SemEval2007/task10data/scoring/gold"
        dir_entrada = "/mnt/ParticaoAlternat/SemEval2007/test/lexsub_test.xml"

    gabarito_tmp = carregar_gabarito(dir_gabarito)

    casos_testes, gabarito = [], []

    gabarito_dict = dict()

    for lexelt in gabarito_tmp:
        lista = []
        for sugestao in gabarito_tmp[lexelt]:
            voto = gabarito_tmp[lexelt][sugestao]
            lista.append([sugestao, voto])
        gabarito.append(lista)
        gabarito_dict[lexelt] = lista

    validador_semeval2007 = ValidadorRankingSemEval2007(configs)
    casos_testes_tmp = validador_semeval2007.ler_entrada_teste(dir_entrada)

    casos_testes_dict = {}

    for lexema in casos_testes_tmp:
        for registro in casos_testes_tmp[lexema]:
            frase = registro['frase']
            palavra = registro['palavra']
            pos = lexema.split(".")[1]
            casos_testes.append([frase, palavra, pos])

            nova_chave = "%s %s" % (lexema, registro['codigo'])
            casos_testes_dict[nova_chave] = [frase, palavra, pos]

    casos_testes = []
    gabarito = []
    lexemas = []

    resultados_persistiveis = []

    if len(gabarito) != len(casos_testes):
        raise Exception("A quantidade de instancias de entrada estao erradas!")

    for lexema in casos_testes_dict:
        if lexema in casos_testes_dict and lexema in gabarito_dict:            
            casos_testes.append(casos_testes_dict[lexema])
            gabarito.append(gabarito_dict[lexema])
            lexemas.append(lexema)

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

    for indice in range(len(gabarito)):
        todos_votos = sorted([v[1] for v in gabarito[indice]], reverse=True)

        # Se caso de entrada possui uma moda
        possui_moda = todos_votos.count(todos_votos[0]) == 1

        if possui_moda == True:
            candidatos = [e[0] for e in gabarito[indice]]
            contexto, palavra, pos = casos_testes[indice]

            resultados_persistiveis.append(indice)

            # Extraindo candidatos que a abordagem do Alvaro escolhe atraves de dicionarios
            candidatos_selecionados_alvaro = list()

            if usar_sinonimos_wordnet == True:
                candidatos_selecionados_alvaro += abordagem_alvaro.selecionar_candidatos(palavra, pos, fontes=['wordnet'])
            if usar_sinonimos_oxford == True:
                candidatos_selecionados_alvaro += abordagem_alvaro.selecionar_candidatos(palavra, pos, fontes=['oxford'])
            if usar_sinonimos_word_embbedings == True:
                palavras_relacionadas = representacao_vetorial.obter_palavras_relacionadas(positivos=[palavra], topn=max_resultados)
                palavras_relacionadas = [p[0] for p in palavras_relacionadas]
                candidatos_selecionados_alvaro += palavras_relacionadas

            total_candidatos.append(len(candidatos_selecionados_alvaro))
            candidatos_selecionados_alvaro = list(set(candidatos_selecionados_alvaro))

            # Respostas certas baseada na instancia de entrada
            gabarito_tmp = sorted(gabarito[indice], key=lambda x: x[1], reverse=True)
            gabarito_tmp = [reg[0] for reg in gabarito_tmp]

            print("\nCASO ENTRADA: \n" + str((contexto, palavra, pos)))
            print("\nMEDIA DE SUGESTOES:\n%d" % (sum(total_candidatos)/len(total_candidatos)))
            print("\nRESPOSTAS CORRETAS:\n\n%s" % str(gabarito_tmp))

            intersecao_tmp = list(set([gabarito_tmp[0]]) & set(candidatos_selecionados_alvaro))

            if intersecao_tmp:
                total_com_resposta += 1
                print("\nINTERSECAO: %s" % str(intersecao_tmp))
                print("\nTOTAL PREDITOS CORRETAMENTE: %d" % (len(intersecao_tmp)))
            else:
                total_sem_resposta += 1

    arquivo_saida = open(dir_saida_seletor_candidatos, "w")

    for indice in resultados_persistiveis:
        # [['crazy', 3], ['fast', 1], ['very fast', 1], ['very quickly', 1], ['very rapidly', 1]]
        sugestao = sorted(gabarito[indice], key=lambda x: x[1], reverse=True)[0][0]
        arquivo_saida.write("%s :: %s\n" % (lexemas[indice], sugestao))

    # Persistindo casos de entrada sem resposta corretamente
    for lexema in set(casos_testes_tmp.keys()) - set(lexemas):
        arquivo_saida.write(lexema + " ::\n")

    arquivo_saida.close()

    print("\n\nTotal com resposta: " + str(total_com_resposta))
    print("\nTotal sem resposta: " + str(total_sem_resposta))

def executar_abordagem_alvaro(configs, usar_desambiguador=False, usar_ctx=False):
    contadores = Utilitarios.carregar_json(configs['leipzig']['dir_contadores'])
    casos_testes = gabarito = None

    # Carrega a base Trial para fazer os testes
    dir_gabarito = configs['semeval2007']['trial']['gold_file']
    dir_entrada = configs['semeval2007']['trial']['scorer']

    gabarito_tmp = carregar_gabarito(dir_gabarito)

    casos_testes, gabarito = [], []
    gabarito_dict = {}

    for lexelt in gabarito_tmp:
        lista = []
        for sugestao in gabarito_tmp[lexelt]:
            voto = gabarito_tmp[lexelt][sugestao]
            lista.append([sugestao, voto])
        gabarito.append(lista)
        gabarito_dict[lexelt] = lista

    validador_semeval = ValidadorRankingSemEval2007(configs)
    casos_testes_tmp = validador_semeval.ler_entrada_teste(dir_entrada)

    casos_testes_dict = {}

    for lexema in casos_testes_tmp:
        for registro in casos_testes_tmp[lexema]:
            frase = registro['frase']
            palavra = registro['palavra']
            pos = lexema.split(".")[1]
            casos_testes.append([frase, palavra, pos])

            nova_chave = "%s %s" % (lexema, registro['codigo'])
            casos_testes_dict[nova_chave] = [frase, palavra, pos]

    casos_testes = []
    gabarito = []

    if len(gabarito) != len(casos_testes):
        raise Exception("A quantidade de instancias de entrada estao erradas!")

    for lexema in casos_testes_dict:
        casos_testes.append(casos_testes_dict[lexema])
        gabarito.append(gabarito_dict[lexema])

    casador_manual = CasadorManual(configs)
    base_unificada = BaseUnificadaObjetosOxford(configs)
    abordagem_alvaro = AbordagemAlvaro(configs, base_unificada, casador_manual)

    usar_gabarito = raw_input('Utilizar candidatos do gabarito? s/N: ').lower()
    #indice = int(raw_input("Digite o indice (0 - %d): " % len(gabarito)))

    for indice in range(0, len(casos_testes)):
        if usar_gabarito == 's':
            candidatos = [e[0] for e in gabarito[indice]]        
        else:
            candidatos = None

        # fontes = [raw_input("Digite a fonte desejada: 'wordnet' ou 'oxford': ")]
        fontes = ["oxford"]

        contexto, palavra, pos = casos_testes[indice]
        resultado = abordagem_alvaro.iniciar_processo(palavra, pos, contexto, fontes_arg=fontes, anotar_exemplos=True, usar_fontes_secundarias=True, usar_ctx=usar_ctx, candidatos=candidatos)

        agregacao, frases = dict(), set()

        for reg in resultado:
            if fontes == ['wordnet']:
                label_sinonimo, significado, exemplo, pontuacao = reg
            elif fontes == ['oxford']:
                label_sinonimo = reg[0]
                significado, exemplo, pontuacao = reg[1:]

            if not exemplo in frases:
                frases.add(exemplo)
                # (film.Noun.6;Cinema considered as an art or industry.#Cinema considered as an art or industry)
                label = label_sinonimo + '#' + significado

                if not label in agregacao:
                    agregacao[label] = []

                agregacao[label].append(pontuacao)

        resultado_ordenado_agregado = []

        for lexelt in agregacao:
            media = sum(agregacao[lexelt]) / len(agregacao[lexelt])
            resultado_ordenado_agregado.append((lexelt, media))

        resultado_ordenado_agregado.sort(key=lambda x: x[1], reverse=True)
        resultado = []

        todos_lemas = []

        if usar_desambiguador == True:
            if fontes == ['wordnet']:
                resultado_desambiguacao = cosine_lesk(contexto, palavra, pos=pos, nbest=True)
                resultado_desambiguacao = [r[0].name() for r in resultado_desambiguacao]

            elif fontes == ['oxford']:
                desambiguador_oxford = DesambiguadorOxford(configs, base_unificada)            
                resultado_desambiguacao = desambiguador_oxford.cosine_lesk(contexto, palavra, pos=pos, nbest=True)

                resultado_desambiguacao = ["%s#%s" % (r[0][0], r[0][1]) for r in resultado_desambiguacao]

            definicoes_processadas = set()

            for reg in resultado_ordenado_agregado:
                for reg_desambiguacao in resultado_desambiguacao:
                    if len(resultado) < 10:
                        if fontes == ['wordnet']:
                            s1, s2 = reg[0].split('#')
                        elif fontes == ['oxford']:
                            s1 = reg[0].split('#')[0]
                            s2 = reg[0].split('#')[1].split(";")[0]

                        if fontes == ['oxford']:
                            flag = not s1 in definicoes_processadas and s2 == reg_desambiguacao.split("#")[1]
                        elif fontes == ['wordnet']:                    
                            flag = not s1 in definicoes_processadas and s2 == reg_desambiguacao

                        if flag == True:
                            definicoes_processadas.add(s1)

                            if fontes == ['wordnet']:
                                todos_lemas = wn.synset(s1).lemma_names()
                            elif fontes == ['oxford']:
                                #(u'def_1.;lema_1#def_2.;lema_2', 0.0)
                                lema_s1 = s1.split(";")[-1:][0] # indice zero é pra tirar da lista
                                def_s1 = s1.split(";")[:-1][0] # indice zero é pra tirar da lista
                                todos_lemas = base_unificada.obter_sinonimos(lema_s1, def_s1)

            resultado = resultado[:10]

        else:
            for reg in resultado_ordenado_agregado:
                todos_lemas = []
                s1, s2 = reg[0].split('#')
                if fontes == ['wordnet']:
                    s1, s2 = wn.synset(s1), wn.synset(s2)
                    todos_lemas = list(set(s1.lemma_names() + s2.lemma_names()))
                elif fontes == ['oxford']:
                    def_s1, lema_s1 = s1.split(";")     # def_s2, lema_s2 = re.split("[;.]+", s2)[:2]
                    todos_lemas = base_unificada.obter_sinonimos(lema_s1, def_s1)

        for lema in todos_lemas:
            if not lema in resultado:
                if Utilitarios.representa_multipalavra(lema) == False:
                    if not lema in resultado:
                        resultado.append(lema)

            resultado = resultado[:10]

        if palavra in resultado:
            resultado.remove(palavra)

        resultado = [(p, contadores[p]) for p in resultado if p in contadores]

        #print("\nCASO DE ENTRADA PARA (%s, %s): " % (palavra, contexto))
        #print('\n\nRESULTADO: ')
        resultado.sort(key=lambda x: x[1], reverse=True)

        #print(resultado)
        #print('\n')

        #print('\nGABARITO:\n')
        #print(gabarito[indice])
        #print('\n')

        #print('\nINTERSECAO:\n')
        intersecao = set([e[0] for e in gabarito[indice]]) & set([e[0] for e in resultado])
        #print(list(intersecao))

def testar_casamento(configs):
    base_unificada = BaseUnificadaObjetosOxford(configs)
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

    Utilitarios.limpar_console()
    configs = Utilitarios.carregar_configuracoes(argv[1])

    # Realiza o SemEval2007 para as minhas abordagens implementadas (baselines)
    print('\nIniciando o Semantic Evaluation 2007!')
    realizar_se2007_metodos_desenvolvidos(configs)
    print('\n\nSemEval2007 realizado!\n\n')

    aplicar_metrica_gap = False

    if aplicar_metrica_gap:
        validador_gap = GeneralizedAveragePrecisionMelamud(configs)
        # Obtem os gabaritos informados por ambos
        # anotadores no formato <palavra.pos.id -> gabarito>
        gold_rankings_se2007 = obter_gabarito_rankings_semeval(configs)

        # Lista todos aquivos .best ou .oot do SemEval2007
        lista_todas_submissoes_se2007 = Utilitarios.listar_arquivos(configs['dir_saidas_rankeador'])

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

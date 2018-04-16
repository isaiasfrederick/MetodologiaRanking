from Abordagens.EdmondsEstatistico import IndexadorWhoosh, AbordagemEdmonds
from ModuloBabelNetAPI.ModuloClienteBabelNetAPI import ClienteBabelAPI
from ModuloOxfordAPI.ModuloClienteOxfordAPI import ClienteOxfordAPI
from ModuloExtrator.ExtratorSinonimos import ExtratorSinonimos
from ModuloUtilitarios.Utilitarios import Utilitarios
from ValidadorRanking.Validadores import *
from pywsd.lesk import cosine_lesk as cosine_lesk
from nltk.corpus import wordnet as wordnet
from sys import argv
import traceback
import re

def aplicar_se2007_sob_metodo(configs, metodo_extracao, ordenar):
    respostas_semeval = dict()

    configs_se2007 = configs['semeval2007']
    todas_metricas = configs_se2007['metricas']['limites'].keys()

    dir_contadores = configs['leipzig']['dir_contadores']

    cli_babelnet = ClienteBabelAPI(configs)
    cli_oxford = ClienteOxfordAPI(configs)

    extrator_sinonimos = ExtratorSinonimos(configs, cli_oxford, cli_babelnet, dir_contadores)
    validador_se2007 = ValidadorRankingSemEval2007(configs)

    dir_arquivo_teste = configs_se2007["dir_arquivo_teste"]
    casos_entrada = validador_se2007.ler_entrada_teste(dir_arquivo_teste)

    for metrica in todas_metricas:
        respostas_semeval[metrica] = dict()

    for lemma in casos_entrada:
        respostas_semeval[metrica][lemma] = dict()

        for id_entrada in casos_entrada[lemma]:
            palavra, pos = lemma.split('.')

            frase = id_entrada['frase']
            codigo = id_entrada['codigo']

            sinonimos = extrator_sinonimos.buscar_sinonimos(palavra, pos, metodo_extracao, contexto=frase)

            if ordenar:
                sinonimos = extrator_sinonimos.ordenar_por_frequencia(sinonimos)

            try: sinonimos.remove(palavra)
            except: pass

            for metrica in todas_metricas:
                if not lemma in respostas_semeval[metrica]:
                    respostas_semeval[metrica][lemma] = dict()

                limite_superior = int(configs_se2007['metricas']['limites'][metrica])
                respostas_semeval[metrica][lemma][codigo] = [e.replace('_', ' ') for e in sinonimos[:limite_superior]]
        
    return respostas_semeval

def exibir_todos_resultados(todos_participantes, validador_se2007):
    lista_todos_participantes = todos_participantes.values()
    todas_dimensoes = todos_participantes[todos_participantes.keys()[0]].keys()
    
    for dimensao in todas_dimensoes:
        print('DIMENSAO: ' + dimensao)
        validador_se2007.ordenar_scores(lista_todos_participantes, dimensao)

        indice = 1
        for participante in lista_todos_participantes:
            print(str(indice) + ' - ' + participante['nome'] + '  -  ' + str(participante[dimensao]))

            indice += 1

        print('\n')

# obter frases do caso de entrada
def obter_frases_da_base(validador_se2007, configs):
    entrada = validador_se2007.ler_entrada_teste(configs['semeval2007']['dir_arquivo_teste'])

    for lemma in entrada:
        for id_entrada in entrada[lemma]:
            pos = lemma.split('.')[1]
            frase = id_entrada['frase']
            palavra = id_entrada['palavra']

            resultados_desambiguador = [r for r in cosine_lesk(frase, palavra, nbest=True, pos=pos) if r[0]]

# gerar todos os metodos de extracao direcionados ao se2007
def gerar_submissoes_para_se2007(configs, validador_se2007):
    metodos_extracao = configs['aplicacao']['metodos_extracao']
    todas_metricas_se2007 = configs['semeval2007']['metricas']['separadores'].keys()

    resultados = dict()

    for metrica in todas_metricas_se2007:
        resultados[metrica] = [ ]

    for metodo in metodos_extracao:
        todas_submissoes_geradas = aplicar_se2007_sob_metodo(configs, metodo, True)
        for metrica in todas_metricas_se2007:
            print('\n\nCalculando metrica "%s" para o metodo "%s"' % (metrica, metodo))
            submissao_gerada = todas_submissoes_geradas[metrica]

            nome_minha_abordagem = configs['semeval2007']['nome_minha_abordagem'] + '-' + metodo + '.' + metrica
            nome_minha_abordagem = validador_se2007.formatar_submissao(nome_minha_abordagem, submissao_gerada)

            resultados_minha_abordagem = validador_se2007.calcular_score(configs['dir_saidas_rankeador'], nome_minha_abordagem)
            resultados[metrica].append(resultados_minha_abordagem)

    return resultados

def gerar_submissoes_para_gap(configs, medida_ranking_completo = 'oot'):
    gold_rankings = obter_gold_rankings(configs)

    total_anotadores = configs['semeval2007']['total_anotadores']
    max_sugestoes = configs['semeval2007']['max_sugestoes']
    limite_sugestoes = total_anotadores * max_sugestoes

    for lexema in gold_rankings:
        print(lexema)

    
def realizar_se2007(configs, validador_se2007):
    # gerar todas minhas abordagens de baseline
    minhas_submissoes_geradas = gerar_submissoes_para_se2007(configs, validador_se2007)

    # para cada metrica (OOT e Best)
    for metrica in minhas_submissoes_geradas.keys():
        submissao_gerada = minhas_submissoes_geradas[metrica]
        resultados_participantes = validador_se2007.obter_score_participantes_originais(metrica)

        for minha_abordagem in submissao_gerada:
            resultados_participantes[minha_abordagem['nome']] = minha_abordagem

        exibir_todos_resultados(resultados_participantes, validador_se2007)
        print('\n\n')

# carregar gold file
def obter_gold_rankings(configs):
    dir_gold_file = configs['semeval2007']['trial']['gold_file']

    arquivo_gold = open(dir_gold_file, 'r')
    todas_linhas = arquivo_gold.readlines()
    arquivo_gold.close()

    saida = dict()
    separador = " :: "

    for linha in todas_linhas:
        resposta_linha = dict()
        try:
            ltmp = str(linha)
            ltmp = ltmp.replace('\n', '')
            chave, sugestoes = ltmp.split(separador)
            sugestoes = [s for s in sugestoes.split(';') if s]

            for sinonimo in sugestoes:
                sinonimo_lista = str(sinonimo).split(' ')
                votos = int(sinonimo_lista.pop())
                sinonimo_final = ' '.join(sinonimo_lista)
            
                resposta_linha[sinonimo_final] = votos
            saida[chave] = resposta_linha
        except:
            traceback.print_exc()
    
    return saida

def aplicar_metrica_gap_participantes_semeval2007(configs):
    gerar_submissoes_para_gap(configs)

def carregar_arquivo_submissao_se2007(configs, dir_arquivo, medida="oot"):
    arquivo_gold = open(dir_arquivo, 'r')
    todas_linhas = arquivo_gold.readlines()
    arquivo_gold.close()

    saida = dict()

    separador = configs['semeval2007']['metricas']['separadores'][medida]
    separador = " " + separador + " "

    total_sugestoes = 0

    for linha in todas_linhas:
        resposta_linha = dict()
        try:
            ltmp = str(linha)
            ltmp = ltmp.replace('\n', '')

            chave, sugestoes = ltmp.split(separador)
            todos_candidatos = sugestoes.split(';')
            indice = 0

            for sinonimo in todos_candidatos:
                if sinonimo != "":
                    sinonimo_lista = sinonimo
                    votos = len(todos_candidatos) - indice           
                    resposta_linha[sinonimo] = votos

                indice += 1

            saida[chave] = resposta_linha
        except:
            traceback.print_exc()
    
    return saida


def testar_indexador_whoosh(configs):
    indexador_whoosh = IndexadorWhoosh.IndexadorWhoosh(configs['leipzig']['dir_indexes_whoosh'])
    contadores = Utilitarios.carregar_json(configs['leipzig']['dir_contadores'])

    abordagem_edmonds = AbordagemEdmonds.AbordagemEdmonds(configs, indexador_whoosh, contadores)
    raizes = ['car', 'vehicle']
    abordagem_edmonds.construir_rede(raizes, 2, 1)


if __name__ == '__main__':
    Utilitarios.limpar_console()
    # arg[1] = diretorio das configuracoes.json
    configs = Utilitarios.carregar_configuracoes(argv[1])
#    testar_indexador_whoosh(configs)

    validador_se2007 = ValidadorRankingSemEval2007(configs)
    validador_gap = GeneralizedAveragePrecisionMelamud()

    realizar_se2007(configs, validador_se2007)

    raw_input('\n<ENTER>')

    gerar_submissoes_para_gap(configs)

    gold_rankings_se2007 = obter_gold_rankings(configs)

    lista_todas_submissoes_se2007 = Utilitarios.listar_arquivos(configs['dir_saidas_rankeador'])

    # Usa, originalmente, OOT
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
        for lexema in gold_rankings_se2007:
            ranking_gold = [(k, gold_rankings_se2007[lexema][k]) for k in gold_rankings_se2007[lexema]]
            if lexema in minha_abordagem:
                print('Abordagem: [%s]\t\tFrase: [%s]' % (nome_abordagem, lexema))
                meu_ranking = [(k, minha_abordagem[lexema][k]) for k in minha_abordagem[lexema]]
                gap_score = validador_gap.calc(ranking_gold, meu_ranking)
                print('Meu ranking')
                print(meu_ranking)
                print('Ranking gold')
                print(ranking_gold)
                print('\n')

                resultados_gap[nome_abordagem][lexema] = gap_score

        amostra_gaps = resultados_gap[nome_abordagem].values()
        gap_medio = sum(amostra_gaps) / len(amostra_gaps)

        resultados_gap[nome_abordagem] = gap_medio

    for nome_abordagem in resultados_gap:
        gap_medio = resultados_gap[nome_abordagem]
        print('[%s]\tGAP Medio: %s' % (nome_abordagem, str(gap_medio)))

    print('\n\n\nFim do __main__')
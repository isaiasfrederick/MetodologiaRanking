#! coding: utf-8
from CasadorDefinicoes.RepositorioCentralConceitos import BaseUnificadaObjetosOxford
from Abordagens.EdmondsEstatistico import IndexadorWhoosh, AbordagemEdmonds
from ModuloBabelNetAPI.ModuloClienteBabelNetAPI import ClienteBabelAPI
from ModuloExtrator.InterfaceAbordagens import InterfaceAbordagens
from ModuloUtilitarios.Utilitarios import Utilitarios
from ModuloOxfordAPI.ModuloClienteOxfordAPI import *
from pywsd.lesk import cosine_lesk as cosine_lesk
from ValidadorRanking.Validadores import *
from nltk.corpus import wordnet as wordnet
from sys import argv
import traceback
import re

# Aplicar o SemEval2007 por método de extração
def aplicar_se2007_sob_metodo(configs, metodo_extracao, ordenar):
    base_unificada_oxford = BaseUnificadaObjetosOxford(configs)
    
    configs_se2007 = configs['semeval2007']
    todas_metricas = configs_se2007['metricas']['limites'].keys()

    respostas_semeval = dict()

    for metrica in todas_metricas:
        respostas_semeval[metrica] = dict()

    dir_contadores = configs['leipzig']['dir_contadores']

    cli_babelnet = ClienteBabelAPI(configs)
    cli_oxford = ClienteOxfordAPI(configs)

    extrator_sinonimos = InterfaceAbordagens(configs, cli_oxford, cli_babelnet, dir_contadores, base_unificada_oxford)
    validador_se2007 = ValidadorRankingSemEval2007(configs)

    dir_arquivo_teste = configs_se2007["dir_arquivo_teste"]
    casos_entrada = validador_se2007.ler_entrada_teste(dir_arquivo_teste)

    for lema in casos_entrada:
        respostas_semeval[metrica][lema] = dict()

        for id_entrada in casos_entrada[lema]:
            palavra, pos = lema.split('.')

            frase, codigo = id_entrada['frase'], id_entrada['codigo']

            try:
                sinonimos = extrator_sinonimos.buscar_sinonimos(palavra, pos, metodo_extracao, contexto=frase)
            except:
                sinonimos = []
                print('\n\n')
                print('Erro para a extracao de sinonimos para:\n(%s, %s, %s)\n' % (palavra, pos, contexto))
                traceback.print_stack()
                print('\n\n')

            if ordenar and sinonimos:
                sinonimos = extrator_sinonimos.ordenar_por_frequencia(sinonimos)

            try:
                sinonimos.remove(palavra)
            except: pass

            for metrica in todas_metricas:
                if not lema in respostas_semeval[metrica]:
                    respostas_semeval[metrica][lema] = dict()

                limite_superior = int(configs_se2007['metricas']['limites'][metrica])
                sinonimos = [e.replace('_', ' ') for e in sinonimos[:limite_superior]]
                respostas_semeval[metrica][lema][codigo] = sinonimos
        
    return respostas_semeval

# Exibir todos participantes do SemEval2007
def exibir_todos_resultados(todos_participantes, validador_se2007):
    lista_todos_participantes = todos_participantes.values()
    todas_dimensoes = ['Attempted', 'Precision', 'TotalWithMode', 'Recall', 'Total']

    participantes_ordenados = {}

    for dimensao in todas_dimensoes:
        participantes_ordenados[dimensao] = dict()

        for participante in lista_todos_participantes:
            try:
                participante = participante['nome']
                pontuacao = participante[dimensao]

                if not pontuacao in participantes_ordenados[dimensao]:
                    participantes_ordenados[dimensao][pontuacao].append(participante)
            except: pass

    indice = 0
    for dimensao in participantes_ordenados:
        print('DIMENSAO: ' + dimensao)

        for pontuacao in sorted(participantes_ordenados[dimensao], reverse=True):
            indice += 1
            for participante in participantes_ordenados[dimensao][pontuacao]:
                print('%d\t-\t%s\t%f' % (indice, participante, pontuacao))

# Obter frases do caso de entrada do caso do SemEval2007
def obter_frases_da_base(validador_se2007, configs):
    entrada = validador_se2007.ler_entrada_teste(configs['semeval2007']['dir_arquivo_teste'])

    for lemma in entrada:
        for id_entrada in entrada[lemma]:
            pos = lemma.split('.')[1]
            frase = id_entrada['frase']
            palavra = id_entrada['palavra']

            resultados_desambiguador = [r for r in cosine_lesk(frase, palavra, nbest=True, pos=pos) if r[0]]

# Gerar todos os metodos de extracao direcionados ao SemEval2007
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
 
# Realizar o SemEval2007 exclusivamente para os métodos que desenvolvi
def realizar_se2007_metodos_desenvolvidos(configs):
    validador_se2007 = ValidadorRankingSemEval2007(configs)
    # gerar todas minhas abordagens de baseline
    minhas_submissoes_geradas = gerar_submissoes_para_se2007(configs, validador_se2007)

    # para cada metrica (oot e best)
    for metrica in minhas_submissoes_geradas.keys():
        submissao_gerada = minhas_submissoes_geradas[metrica]
        resultados_participantes = validador_se2007.obter_score_participantes_originais(metrica)

        for minha_abordagem in submissao_gerada:
            resultados_participantes[minha_abordagem['nome']] = minha_abordagem

        exibir_todos_resultados(resultados_participantes, validador_se2007)
        print('\n\n')

# Carregar gold file
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

# Aplica a métrica GAP
def aplicar_metrica_gap_participantes_semeval2007(configs):
    gerar_submissoes_para_gap(configs)

# Carregar arquivos Submissão SemEval 2007
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
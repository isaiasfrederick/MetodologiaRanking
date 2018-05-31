#! coding: utf-8
from Experimentacao.ValidadorResultados import ValidadorInventarioWordnet
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
    
    gabaritos = obter_gabarito_rankings(configs)

    configs_se2007 = configs['semeval2007']
    todas_metricas = configs_se2007['metricas']['limites'].keys()

    respostas_semeval = dict()

    for tarefa in todas_metricas:
        respostas_semeval[tarefa] = dict()

    dir_contadores = configs['leipzig']['dir_contadores']

    cli_babelnet = ClienteBabelAPI(configs)
    cli_oxford = ClienteOxfordAPI(configs)

    extrator_sinonimos = InterfaceAbordagens(configs, cli_oxford, cli_babelnet, dir_contadores, base_unificada_oxford)
    validador_se2007 = ValidadorRankingSemEval2007(configs)

    dir_arquivo_teste = configs_se2007["dir_arquivo_teste"]
    casos_entrada = validador_se2007.ler_entrada_teste(dir_arquivo_teste)

    for lema in casos_entrada:
        respostas_semeval[tarefa][lema] = dict()

        for id_entrada in casos_entrada[lema]:
            palavra, pos = lema.split('.')

            frase, codigo = id_entrada['frase'], id_entrada['codigo']

            try:
                sinonimos = extrator_sinonimos.buscar_sinonimos(palavra, pos, metodo_extracao, contexto=frase)
            except:
                print('\n')
                traceback.print_exc()
                sinonimos = []
                print('\n')

            try:
                sinonimos.remove(palavra)
            except: pass

            if ordenar and sinonimos:
                try:
                    sinonimos = extrator_sinonimos.ordenar_por_frequencia(sinonimos)
                except:
                    print(sinonimos)
                    raw_input('EXCECAO no metodo ' + metodo_extracao)
            
            for tarefa in todas_metricas:
                if not lema in respostas_semeval[tarefa]:
                    respostas_semeval[tarefa][lema] = dict()

                limite_superior = int(configs_se2007['metricas']['limites'][tarefa])
                sinonimos = [e.replace('_', ' ') for e in sinonimos[:limite_superior]]
                respostas_semeval[tarefa][lema][codigo] = sinonimos

            print('Entrada: %s - %s - %s - %s: %s' % (metodo_extracao, tarefa, lema, codigo, str(sinonimos)))
        
    return respostas_semeval

# Exibir todos participantes do SemEval2007
def exibir_todos_resultados(todos_participantes, validador_se2007):
    Utilitarios.limpar_console()

    lista_todos_participantes = todos_participantes.values()
    todas_dimensoes = []

    participantes_ordenados = {}

    for participante in lista_todos_participantes:
        try:
            if participante.keys().__len__() > todas_dimensoes:
                todas_dimensoes = participante.keys()
        except: pass

    todas_dimensoes = ['Total', 'Attempted', 'Precision', 'Recall']
    todas_dimensoes += ['TotalWithMode', 'Attempted', 'ModePrecision', 'ModeRecall']

    try:
        todas_dimensoes.remove('nome')
    except: pass

    for dimensao in todas_dimensoes:
        try:
            participantes_ordenados[dimensao] = dict()

            for participante in lista_todos_participantes:
                try:
                    nome_participante = participante['nome']
                    pontuacao = participante[dimensao]

                    if not pontuacao in participantes_ordenados[dimensao]:
                        participantes_ordenados[dimensao][pontuacao] = []

                    participantes_ordenados[dimensao][pontuacao].append(nome_participante)

                except Exception, e: pass
        except: pass

    for dimensao in participantes_ordenados:
        print('DIMENSAO: ' + dimensao)
        indice = 1
        for pontuacao in sorted(participantes_ordenados[dimensao], reverse=True):
            for participante in participantes_ordenados[dimensao][pontuacao]:
                print('%d  -  %s\t%.2f' % (indice, participante, pontuacao))
                indice += 1

        print('\n')

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
        if 'Wordnet' in metodo or 'Oxford':
#        if 'Wordnet' in  metodo:
#        if 'Wordnet' in metodo:
#        if True:
            todas_submissoes_geradas = aplicar_se2007_sob_metodo(configs, metodo, True)
            for metrica in todas_metricas_se2007:
                submissao_gerada = todas_submissoes_geradas[metrica]

                nome_minha_abordagem = configs['semeval2007']['nome_minha_abordagem'] + '-' + metodo + '.' + metrica
                nome_minha_abordagem = validador_se2007.formatar_submissao(nome_minha_abordagem, submissao_gerada)

                resultados_minha_abordagem = validador_se2007.calcular_score(configs['dir_saidas_rankeador'], nome_minha_abordagem)
                resultados[metrica].append(resultados_minha_abordagem)

    return resultados
 
# Realizar o SemEval2007 exclusivamente para os métodos que desenvolvi
def realizar_se2007_metodos_desenvolvidos(configs):
    system('clear ' + configs['dir_saidas_rankeador'])

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

# Carregar gold file
def obter_gabarito_rankings(configs):
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
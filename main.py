#! coding: utf-8
from ModuloUtilitarios.Utilitarios import Utilitarios
from SemEval2007 import *
from sys import argv
import traceback
import re

# Experimentacao
from ModuloDesambiguacao.DesambiguadorOxford import DesambiguadorOxford
from ModuloDesambiguacao.DesambiguadorUnificado import DesambiguadorUnificado
from ModuloDesambiguacao.DesambiguadorWordnet import DesambiguadorWordnet
from ModuloOxfordAPI.ModuloClienteOxfordAPI import BaseUnificadaObjetosOxford
from CasadorDefinicoes.RepositorioCentralConceitos import CasadorConceitos
from nltk.corpus import wordnet as wn
# Fim pacotes da Experimentacao


def TesteDesambiguadores(configs):
    base_unificada_oxford = BaseUnificadaObjetosOxford(configs)

    desambiguador_oxford = DesambiguadorOxford(configs, base_unificada_oxford)
    desambiguador_unificado = DesambiguadorUnificado(configs, base_unificada_oxford)
    desambiguador_wordnet = DesambiguadorWordnet(configs)

    #repositorio_definicoes = CasadorConceitos(configs, base_unificada_oxford)

    lema = 'side'

    frase = "On Sunday at Craven Cottage, Jose Mourinho and his all stars exhibited all "
    frase += "of the above symptoms and they were made to pay the price by a Fulham side that had "
    frase += "in previous weeks woken up after matches with their heads kicked in .".lower()

    pos = 'n'

    if False:
        casador = CasadorConceitos(configs, base_unificada_oxford)
        casador.iniciar_casamento(raw_input('Lema: '), raw_input('POS: '))


    # ---------------------------------------------------------------------------

    if True:
        print('\n\nDESAMBIGUADOR OXFORD')
        resultado = desambiguador_oxford.adapted_cosine_lesk(frase, lema, pos, usar_ontologia=True, usar_exemplos=False)
        resultado = [(elemento[0][0:2], elemento[1]) for elemento in resultado]
      
        for elemento in resultado:
            nome_definicao, definicao, pontuacao = elemento[0][0], elemento[0][1], elemento[1]

            # consulta repositorio pra obter dados
            obj_retorno = base_unificada_oxford.iniciar_consulta(lema)
            # busca sinonimos por definicao
            sinonimos = base_unificada_oxford.obter_sinonimos(pos, definicao, obj_retorno)

            print((nome_definicao, definicao, pontuacao, sinonimos))
            print('\n')
            
        print('\n\n\n')
        raw_input('\n<ENTER>')
        Utilitarios.limpar_console()

    # ---------------------------------------------------------------------------

    if True:
        resultado = desambiguador_unificado.adapted_cosine_lesk(frase, lema, pos, usar_ontologia=True, usar_exemplos=False)
        resultado = [(elemento[0][0:2], elemento[1]) for elemento in resultado]

        print('\n\nDESAMBIGADOR UNIFICADO (USANDO EXEMPLOS)\n')
        for elemento in resultado:
            print(elemento)

        print('\n\n\n')
        raw_input('\n<enter>')
        Utilitarios.limpar_console()

    # ---------------------------------------------------------------------------

    if True:
        resultado = desambiguador_unificado.adapted_cosine_lesk(frase, lema, pos, usar_exemplos=False)
        resultado = [(elemento[0][0:2], elemento[1]) for elemento in resultado]

        print('\n\nDESAMBIGADOR UNIFICADO (SEM UTILIZAR EXEMPLOS)\n')
        for elemento in resultado:
            print(elemento)

        print('\n\n\n')
        raw_input('\n<enter>')
        Utilitarios.limpar_console()

    # ---------------------------------------------------------------------------

    if True:
        print('DESAMBIGADOR WORDNET')
        resultado = desambiguador_wordnet.adapted_cosine_lesk(frase, lema, pos=pos)

        for elemento in resultado:
            print(elemento)

        print('\n\n\n')
        raw_input('\n<enter>')
        Utilitarios.limpar_console()

    exit(0)

    # ---------------------------------------------------------------------------


if __name__ == '__main__':
    if len(argv) < 2:
        print('\nParametrizacao errada!')
        print('Tente py ./main <dir_config_file>\n\n')
        exit(0)

    Utilitarios.limpar_console()
    configs = Utilitarios.carregar_configuracoes(argv[1])

    TesteDesambiguadores(configs)
    exit(0)

    validador_se2007 = ValidadorRankingSemEval2007(configs)
    validador_gap = GeneralizedAveragePrecisionMelamud(configs)

    realizar_se2007(configs, validador_se2007)


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
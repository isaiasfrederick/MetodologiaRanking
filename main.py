#! coding: utf-8
from ModuloUtilitarios.Utilitarios import Utilitarios
from SemEval2007 import *
from sys import argv
import traceback
import re

def teste_desambiguador(configs):
    from ModuloDesambiguacao.DesambiguadorOxford import DesambiguadorOxford
    from ModuloDesambiguacao.DesambiguadorUnificado import DesambiguadorUnificado
    from ModuloOxfordAPI.ModuloClienteOxfordAPI import BaseUnificadaObjetosOxford
    from CasadorDefinicoes.RepositorioCentralConceitos import CasadorConceitos
    from nltk.corpus import wordnet as wn

    base_unificada_oxford = BaseUnificadaObjetosOxford(configs)
    desambiguador_oxford = DesambiguadorOxford(configs, base_unificada_oxford)
    desambiguador_unificado = DesambiguadorUnificado(configs, base_unificada_oxford)
    repositorio_definicoes = CasadorConceitos(configs, base_unificada_oxford)

    #repositorio_definicoes.iniciar_casamento(raw_input("Digite a palavra do ingles: "), "Noun")
    #exit(0)

    # ---------------------------------------------------------------------------
    f = "If Australia was not at or about to be at war, the tactical voter's decision would be easy this weekend.".lower()
    f = "i was at fight using my box.".lower()
    r = desambiguador_oxford.adapted_cosine_lesk(f, 'fight', 'n', usar_ontologia=True)
    r = [(e[0][0:2], e[1]) for e in r]

    for e in r:
        print(e)


    print('\n\n\n')
    raw_input('\n<enter>')
    Utilitarios.limpar_console()

    r = desambiguador_unificado.adapted_cosine_lesk(f, raw_input('Lema: '), 'n', usar_ontologia=True)
    
    for e in r:
        print(e)

    exit(0)
    Utilitarios.limpar_console()

    # ---------------------------------------------------------------------------


if __name__ == '__main__':
    system('rm /media/isaias/ParticaoAlternat/Bases/Cache/CasadorDefinicoes/*')

    if len(argv) < 2:
        print('\nParametrizacao errada!')
        print('Tente py ./main <dir_config_file>\n\n')
        exit(0)

    Utilitarios.limpar_console()
    configs = Utilitarios.carregar_configuracoes(argv[1])

    teste_desambiguador(configs)
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
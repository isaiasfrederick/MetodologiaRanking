#! coding: utf-8
from ModuloUtilitarios.Utilitarios import Utilitarios
from SemEval2007 import *
from sys import argv
import statistics
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

def testar_casamento(configs):
    base_unificada = BaseUnificadaObjetosOxford(configs)
    casador = CasadorConceitos(configs, base_unificada)

    palavra = raw_input('Palavra: ')
    pos = raw_input('POS: ')

    r = casador.iniciar_casamento(palavra, pos)
    print('\n')

    for e in r:
        print(e)
        print(r[e])
        print('\n\n\n')

    print('\n\nCheguei aqui...')

if __name__ == '__main__':
    if len(argv) < 2:
        print('\nParametrizacao errada!')
        print('Tente py ./main <dir_config_file>\n\n')
        exit(0)

    Utilitarios.limpar_console()
    configs = Utilitarios.carregar_configuracoes(argv[1])

#    testar_casamento(configs)
#    exit(0)

    # Criando validadores par as métricas avaliadas
    validador_se2007 = ValidadorRankingSemEval2007(configs)

    # Realiza o SemEval2007 para as minhas abordagens implementadas (baselines)
    print('\nIniciando o Semantic Evaluation 2007!')
    realizar_se2007_metodos_desenvolvidos(configs)
    print('\n\nSemEval2007 realizado!\n\n')

    aplicar_metrica_gap = True

    if aplicar_metrica_gap:
        validador_gap = GeneralizedAveragePrecisionMelamud(configs)
        # Obtem os gabaritos informados por ambos
        # anotadores no formato <palavra.pos.id -> gabarito>
        gold_rankings_se2007 = obter_gabarito_rankings(configs)

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
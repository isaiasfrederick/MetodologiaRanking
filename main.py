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


def testar_desambiguadores(configs):
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

    frase = 'General Update #3 Wednesday , 24th September , 2003 : : 03:56 EDT - Sidenotes - perplexed A little more of the general boring scrap , nothing to get too excited about .'
    frase = frase.lower()

    lema = 'scrap'

    if False:
        casador = CasadorConceitos(configs, base_unificada_oxford)
        casador.iniciar_casamento(raw_input('Lema: '), raw_input('POS: '))


    # ---------------------------------------------------------------------------

    if False:
        print('\n\nDESAMBIGUADOR OXFORD')
        resultado = desambiguador_oxford.adapted_cosine_lesk(frase, lema, pos, usar_ontologia=True, usar_exemplos=True)
        resultado = [(elemento[0][0:2], elemento[1]) for elemento in resultado]
      
        for elemento in resultado:
            nome_definicao, definicao, pontuacao = elemento[0][0], elemento[0][1], elemento[1]

            # consulta repositorio pra obter dados
            obj_retorno = base_unificada_oxford.iniciar_consulta(lema)
            # busca sinonimos por definicao
            sinonimos = base_unificada_oxford.obter_sinonimos_fonte_obj_unificado(pos, definicao, obj_retorno)

            print((nome_definicao, definicao, pontuacao, sinonimos))
            print('\n')
            
        print('\n\n\n')
        #raw_input('\n<ENTER>')
        #Utilitarios.limpar_console()

    # ---------------------------------------------------------------------------

    if True:
        resultado = desambiguador_unificado.adapted_cosine_lesk(frase, lema, pos, usar_ontologia=True, usar_exemplos=True)
        resultado = [(elemento[0][0:2], elemento[1]) for elemento in resultado]

        print('\n\nDESAMBIGADOR UNIFICADO (USANDO EXEMPLOS)\n')
        for elemento in resultado:
            print(elemento)

        print('\n\n\n')
        raw_input('\n<enter>')
        #Utilitarios.limpar_console()

    # ---------------------------------------------------------------------------

    if False:
        resultado = desambiguador_unificado.adapted_cosine_lesk(frase, lema, pos, usar_exemplos=False, usar_ontologia=True)
        resultado = [(elemento[0][0:2], elemento[1]) for elemento in resultado]

        print('\n\nDESAMBIGADOR UNIFICADO (SEM UTILIZAR EXEMPLOS)\n')
        for elemento in resultado:
            print(elemento)

        print('\n\n\n')
        raw_input('\n<enter>')
        #Utilitarios.limpar_console()

    # ---------------------------------------------------------------------------

    if False:
        print('DESAMBIGADOR WORDNET')
        resultado = desambiguador_wordnet.adapted_cosine_lesk(frase, lema, pos=pos)

        for elemento in resultado:
            synset, pontuacao = elemento
            print((synset.name(), synset.definition(), pontuacao))

        print('\n\n\n')
        #raw_input('\n<enter>')
        #Utilitarios.limpar_console()

    exit(0)

    # ---------------------------------------------------------------------------


if __name__ == '__main__':
    if len(argv) < 2:
        print('\nParametrizacao errada!')
        print('Tente py ./main <dir_config_file>\n\n')
        exit(0)

    Utilitarios.limpar_console()
    configs = Utilitarios.carregar_configuracoes(argv[1])

    if False:
        from Abordagens.BaselineOrdenadorFrequencia import BaselineOrdenadorFrequencia
        bof = BaselineOrdenadorFrequencia()
        bof.iniciar(configs, None)
        exit(0)

    if False:
    #    def obter_obj_cli_api(self, palavra):
    #    def obter_obj_col_web(self, palavra):
    #    def obter_obj_unificado(self, palavra)

        base_unificada = BaseUnificadaObjetosOxford(configs)
        obj = base_unificada.iniciar_consulta('informal')

        definicao = 'Bits of uneaten food left after a meal.'

        sinonimos = base_unificada.obter_sinonimos_fonte_obj_unificado('n', definicao, obj)
        #sinonimos = base_unificada.obter_sinonimos_fonte_obj_api('n', definicao, obj)

        testar_desambiguadores(configs)

        exit(0)

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
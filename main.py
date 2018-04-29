#! coding: utf-8
from ModuloUtilitarios.Utilitarios import Utilitarios
from SemEval2007 import *
from sys import argv
import traceback
import re

def teste_desambiguador(configs):
    from ModuloDesambiguacao.DesambiguadorOxford import DesambiguadorOxford
    from ModuloOxfordAPI.ModuloClienteOxfordAPI import BaseUnificadaObjetosOxford
    from CasadorDefinicoes.RepositorioCentralConceitos import CasadorConceitos
    from nltk.corpus import wordnet as wn

    base_unificada_oxford = BaseUnificadaObjetosOxford(configs)
    desambiguador_oxford = DesambiguadorOxford(configs, base_unificada_oxford)
    repositorio_definicoes = CasadorConceitos(configs, base_unificada_oxford)

    repositorio_definicoes.iniciar_casamento(raw_input("Digite a palavra do ingles: "), "Noun")
    exit(0)

    # ---------------------------------------------------------------------------
    f = "If Australia was not at or about to be at war, the tactical voter's decision would be easy this weekend.".lower()
    desambiguador_oxford.adapted_cosine_lesk(f, 'war', 'n', usar_ontologia=True)
    exit(0)

    # ---------------------------------------------------------------------------
    dfs = ["A state of armed conflict between different countries or different groups within a country."]
    dfs.append("A state of competition or hostility between different people or groups.")
    dfs.append("A sustained campaign against an undesirable situation or activity.")

    synsets = wn.synsets('war', 'n')

    repositorio_definicoes.busca_todos_hiperonimos('car', synsets, dfs)

    raw_input('\n\n\n<enter>\n')
    f2 = 'A sustained campaign against an undesirable situation or activity.'
#    f2 = 'A state of competition or hostility between different people or groups.'

    for s in repositorio_definicoes.buscador_conceitos_centrais('campaign', 'n', f2):
        print(s[0].definition() + ' - ' + str(s[1]))

    print('\n\n\n\n')
    # ---------------------------------------------------------------------------


    f = "A system for transmitting voices over a distance using wire or radio, by converting acoustic vibrations to electrical signals."
    f.lower()

    stem = True
    rel = True

    tds_synsets = wn.synsets('telephone', 'n')

    for s in tds_synsets:
        assinatura = repositorio_definicoes.assinatura_synset(s, stem=stem, usar_relacoes=rel)
        f = repositorio_definicoes.stemizar_frase(f) if stem else f
        r = Utilitarios.cosseno(assinatura, f)
        print('OXFORD: Frase: ' + f)
        print('\tAssinatura: ' + f)
        print('WORDNET: Synset: ' + s.name() + ' - ' + s.definition())
        print('\tAssinatura: ' + assinatura)
        print('Cosseno: ' + str(r))
        r = Utilitarios.jaccard(assinatura, f)
        print('Jaccard: ' + str(r))
        print('\n\n')

if __name__ == '__main__':
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
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

# Testar Abordagem Alvaro
from Abordagens.AbordagemAlvaro import AbordagemAlvaro
from CasadorManual import CasadorManual

wn = wordnet

def executar_abordagem_alvaro(configs, usar_desambiguador=False, usar_ctx=False):
    contadores = Utilitarios.carregar_json("/media/isaias/ParticaoAlternat/Bases/contadores_leipzig_corpus.json")
    
    f = [raw_input("Digite a fonte desejada ('oxford' ou 'wordnet'): ")]

    usar_desambiguador = False

    flag_base = 'trial'

    if flag_base == 'test':
        # 301, 321, 331, 1091
        casos_testes = Utilitarios.carregar_json('/home/isaias/casos_testes-test.json')
        gabarito = Utilitarios.carregar_json('/home/isaias/gabarito-test.json')

    else:
        casos_testes = Utilitarios.carregar_json('/home/isaias/casos_testes-trial.json')
        # 298, 281, 181, 255, 201, 11
        gabarito = Utilitarios.carregar_json('/home/isaias/gabarito-trial.json')

    indice = int(raw_input('\nDigite o indice (Maximo: %d): ' % (len(gabarito)-1)))

    casador_manual = CasadorManual(configs)
    base_unificada = BaseUnificadaObjetosOxford(configs)
    abordagem_alvaro = AbordagemAlvaro(configs, base_unificada, casador_manual)
    
    usar_gabarito = raw_input('Utilizar candidatos do gabarito? s/N: ').lower()

    if usar_gabarito == 's':
        candidatos = [e[0] for e in gabarito[indice]]
    else:
        candidatos = None

    contexto, palavra, pos = casos_testes[indice]

    candidatos_selecionados_tmp = abordagem_alvaro.selecionar_candidatos(palavra, pos, fontes=f)
    gabarito_tmp = candidatos = [e[0] for e in gabarito[indice]]

    print("\nGabarito:\n%s" % str(gabarito_tmp))
    print("\nCandidatos temporarios:\n%s" % str(candidatos_selecionados_tmp))
    intersecao_tmp = list(set(gabarito_tmp) & set(candidatos_selecionados_tmp))
    print("\nIntersecao: %s" % str(intersecao_tmp))
    raw_input("\nTotal de preditos corretamente: %d" % (len(intersecao_tmp)))

    resultado = abordagem_alvaro.iniciar_processo(palavra, pos, contexto, fontes=f, anotar_exemplos=True, usar_fontes_secundarias=True, usar_ctx=usar_ctx, candidatos=candidatos)

    agregacao = dict()
    frases = set()

    for reg in resultado:
        if f == ['wordnet']:
            label_sinonimo, significado, exemplo, pontuacao = reg
        elif f == ['oxford']:
            label_sinonimo = reg[0]
            significado, exemplo, pontuacao = reg[1], reg[2], reg[3]

        if not exemplo in frases:
            frases.add(exemplo)
            # (film.Noun.6;Cinema considered as an art or industry.#Cinema considered as an art or industry)
            label = label_sinonimo + '#' + significado

            if not label in agregacao:
                agregacao[label] = []

            agregacao[label].append(pontuacao)

    resultado_ordenado = []

    for chave in agregacao:
        media = sum(agregacao[chave]) / len(agregacao[chave])
        resultado_ordenado.append((chave, media))

    resultado_ordenado.sort(key=lambda x: x[1], reverse=True)
    resultado = []

    if usar_desambiguador == True:
        if f == ['wordnet']:
            resultado_desambiguacao = cosine_lesk(contexto, palavra, pos=pos, nbest=True)
            resultado_desambiguacao = [r[0].name() for r in resultado_desambiguacao]

        elif f == ['oxford']:
            desambiguador_oxford = DesambiguadorOxford(configs, base_unificada)            
            resultado_desambiguacao = desambiguador_oxford.adapted_cosine_lesk(contexto, palavra, pos=pos, nbest=True)

            resultado_desambiguacao = ["%s#%s" % (r[0][0], r[0][1]) for r in resultado_desambiguacao]

        definicoes_processadas = set()

        for reg in resultado_ordenado:
            for reg_desambiguacao in resultado_desambiguacao:
                if len(resultado) < 10:
                    if f == ['wordnet']:
                        s1, s2 = reg[0].split('#')
                    elif f == ['oxford']:
                        s1 = reg[0].split('#')[0]
                        s2 = reg[0].split('#')[1].split(";")[0]

                    if f == ['oxford']:
                        flag = not s1 in definicoes_processadas and s2 == reg_desambiguacao.split("#")[1]
                    elif f == ['wordnet']:                    
                        flag = not s1 in definicoes_processadas and s2 == reg_desambiguacao

                    if flag == True:
                        definicoes_processadas.add(s1)

                        if f == ['wordnet']:
                            todos_lemas = wn.synset(s1).lemma_names()
                        elif f == ['oxford']:
                            #(u'def_1.;lema_1#def_2.;lema_2', 0.0)
                            def_s1, lema_s1 = s1.split(";")
                            todos_lemas = base_unificada.obter_sinonimos(lema_s1, def_s1)

        resultado = resultado[:10]

    else:
        for reg in resultado_ordenado:
            todos_lemas = []
            if f == ['wordnet']:
                s1, s2 = reg[0].split('#')
                s1, s2 = wn.synset(s1), wn.synset(s2)

                todos_lemas = list(set(s1.lemma_names() + s2.lemma_names()))
            elif f == ['oxford']:
                s1, s2 = reg[0].split('#')

                def_s1, lema_s1 = s1.split(";")
                def_s2, lema_s2 = re.split("[;.]+", s2)[:2]

                todos_lemas = base_unificada.obter_sinonimos(lema_s1, def_s1)

    for lema in todos_lemas:
        if not lema in resultado:
            if Utilitarios.representa_multipalavra(lema) == False:
                if not lema in resultado:
                    resultado.append(lema)

        resultado = resultado[:10]

    raw_input("\n\nRESULTADO: " + str(resultado))
    if palavra in resultado:
        resultado.remove(palavra)

    resultado = [(p, contadores[p]) for p in resultado]

    print('\n\nRESULTADO +: ')
    resultado.sort(key=lambda x: x[1], reverse=True)

    print(resultado)
    print('\n')

    print('\nGABARITO:\n')
    print(gabarito[indice])
    print('\n')

    print('\nINTERSECAO:\n')
    intersecao = set([e[0] for e in gabarito[indice]]) & set([e[0] for e in resultado])
    print(list(intersecao))

    return

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

    if True:
        executar_abordagem_alvaro(configs, usar_desambiguador=True)
        #raw_input('\n\n<ENTER>\n')
        #testar_abordagem_alvaro(configs, usar_desambiguador=False)
        #raw_input('\n\nUSANDO CONTEXTO:\n<ENTER>\n')
        #testar_abordagem_alvaro(configs, usar_desambiguador=True, usar_ctx=True)
        #raw_input('\n\n<ENTER>\n')
        #testar_abordagem_alvaro(configs, usar_desambiguador=False, usar_ctx=True)

        print('\n\n\n')
        exit(0)

    if True:
        from Abordagens.RepresentacaoVetorial import RepresentacaoVetorial
        rep_vetorial = RepresentacaoVetorial(configs)
        rep_vetorial.carregar_modelo('/home/isaias/Desktop/glove.6B.300d.txt', binario=False)

        while False:
            res = rep_vetorial.palavra_diferente(raw_input("Digite as palavras separadas por espaços: "))
            print(">>> " + res)

        if True:
            palavra = ""        
            while palavra != "sair":
                palavra = raw_input("DIGITAR PALAVRA: ")
                if not palavra in ["sair", ""]:
                    positivos = palavra + " " + raw_input("COLAR DEFINICAO DA PALAVRA: ")
                    positivos = positivos.split(" ")
                    
                    for e in rep_vetorial.obter_palavras_relacionadas(positivos=positivos, topn=40):
                        print(e)
                    print('\n\n')
        exit(0)

#    testar_casamento_manual(configs)
#    exit(0)
    #testar_wander(configs)

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
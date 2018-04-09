from ModuloBabelNetAPI.ModuloClienteBabelNetAPI import ClienteBabelAPI
from ModuloOxfordAPI.ModuloClienteOxfordAPI import ClienteOxfordAPI
from ModuloExtrator.ExtratorSinonimos import ExtratorSinonimos
from ValidadorRanking.Validadores import ValidadorRankingSemEval2007, ValidadorGeneralizedAveragePrecision
from pywsd.lesk import cosine_lesk as cosine_lesk
from nltk.corpus import wordnet as wordnet
from Utilitarios import Utilitarios
from sys import argv
import traceback
import re

def aplicar_semeval2007(configs, metodo_extracao, ordenar):
    respostas_semeval = dict()

    configs_semeval2007 = configs['semeval2007']
    todas_metricas = configs_semeval2007['metricas']['limites'].keys()

    dir_contadores = configs['leipzig']['dir_contadores']

    cli_babelnet = ClienteBabelAPI(configs)
    cli_oxford = ClienteOxfordAPI(configs)

    extrator_sinonimos = ExtratorSinonimos(configs, cli_oxford, cli_babelnet, dir_contadores)
    validador_semeval2007 = ValidadorRankingSemEval2007(configs)

    dir_arquivo_teste = configs_semeval2007["dir_arquivo_teste"]
    casos_entrada = validador_semeval2007.ler_entrada_teste(dir_arquivo_teste)

    for metrica in todas_metricas:
        respostas_semeval[metrica] = dict()

    for lemma in casos_entrada:
        respostas_semeval[metrica][lemma] = dict()

        for id_entrada in casos_entrada[lemma]:
            palavra, pos = lemma.split('.')

            frase = id_entrada['frase']
            codigo = id_entrada['codigo']

            sinonimos = extrator_sinonimos.busca_sinonimos(palavra, pos, metodo_extracao, contexto=frase)

            if ordenar:
                sinonimos = extrator_sinonimos.ordenar_por_frequencia(sinonimos)

            try: sinonimos.remove(palavra)
            except: pass

            for metrica in todas_metricas:
                if not lemma in respostas_semeval[metrica]:
                    respostas_semeval[metrica][lemma] = dict()

                limite_superior = int(configs_semeval2007['metricas']['limites'][metrica])
                respostas_semeval[metrica][lemma][codigo] = [e.replace('_', ' ') for e in sinonimos[:limite_superior]]
        
    return respostas_semeval


def exibir_todos_resultados(todos_participantes, validador_semeval2007):
    lista_todos_participantes = todos_participantes.values()
    todas_dimensoes = todos_participantes[todos_participantes.keys()[0]].keys()
    
    for dimensao in todas_dimensoes:
        print('DIMENSAO: ' + dimensao)
        validador_semeval2007.ordenar_scores(lista_todos_participantes, dimensao)

        indice = 1
        for participante in lista_todos_participantes:
            print(str(indice) + ' - ' + participante['nome'] + '  -  ' + str(participante[dimensao]))

            indice += 1

        print('\n')

# obter frases do caso de entrada
def obter_frases_da_base(validador_semeval2007, configs):
    entrada = validador_semeval2007.ler_entrada_teste(configs['semeval2007']['dir_arquivo_teste'])

    for lemma in entrada:
        for id_entrada in entrada[lemma]:
            pos = lemma.split('.')[1]
            frase = id_entrada['frase']
            palavra = id_entrada['palavra']

            resultados_desambiguador = [r for r in cosine_lesk(frase, palavra, nbest=True, pos=pos) if r[0]]

# gerar todos os metodos de extracao direcionados ao semeval2007
def gerar_submissoes_para_semeval2007(configs, validador_semeval2007):
    metodos_extracao = configs['aplicacao']['metodos_extracao']
    todas_metricas = configs['semeval2007']['metricas']['separadores'].keys()

    resultados = dict()

    for metrica in todas_metricas:
        resultados[metrica] = [ ]

    for metodo in metodos_extracao:
        todas_submissoes_geradas = aplicar_semeval2007(configs, metodo, True)
        for metrica in todas_metricas:
            print('Calculando metrica "%s" para o metodo "%s"' % (metrica, metodo))
            submissao_gerada = todas_submissoes_geradas[metrica]

            nome_minha_abordagem = configs['semeval2007']['nome_minha_abordagem'] + '-' + metodo + '.' + metrica
            nome_minha_abordagem = validador_semeval2007.formatar_submissao(nome_minha_abordagem, submissao_gerada)

            resultados_minha_abordagem = validador_semeval2007.calcular_score(configs['dir_saidas_rankeador'], nome_minha_abordagem)
            resultados[metrica].append(resultados_minha_abordagem)

    return resultados

def realizar_semeval2007(configs, validador_semeval2007):
    minhas_submissoes_geradas = gerar_submissoes_para_semeval2007(configs, validador_semeval2007)

    for metrica in minhas_submissoes_geradas.keys():
        submissao_gerada = minhas_submissoes_geradas[metrica]

        resultados_participantes = validador_semeval2007.obter_score_participantes_originais(metrica)

        for minha_abordagem in submissao_gerada:
            resultados_participantes[minha_abordagem['nome']] = minha_abordagem

        exibir_todos_resultados(resultados_participantes, validador_semeval2007)
        print('\n\n')

def obter_gold_rankings(configs):
    saida = dict()
    dir_gold_file = configs['semeval2007']['trial']['gold_file']

    arquivo_gold = open(dir_gold_file, 'r')
    linhas = arquivo_gold.readlines()
    arquivo_gold.close()


    for l in linhas:
        resposta_linha = dict()
        print(l)
        try:
            ltmp = str(l)
            ltmp = ltmp.replace('\n', '')
            chave, sugestoes = ltmp.split(" :: ")
            for sinonimo in str(sugestoes).split(';'):
                if sinonimo != "":
                    sinonimo_lista = str(sinonimo).split(' ')
                    votos = int(sinonimo_lista.pop())
                    sinonimo_final = ' '.join(sinonimo_lista)

                    print((sinonimo_final, votos))
            
                    resposta_linha[sinonimo_final] = votos

            saida[chave] = resposta_linha
        except:
            traceback.print_exc()
    
    return saida

if __name__ == '__main__':
    # arg[1] = diretorio das configuracoes.json
    configs = Utilitarios.carregar_configuracoes(argv[1])

    validador_semeval2007 = ValidadorRankingSemEval2007(configs)
    validador_gap = ValidadorGeneralizedAveragePrecision()

#    realizar_semeval2007(configs, validador_semeval2007)
    for v in obter_gold_rankings(configs).values():
        score = validador_gap.average_precision(v, v)
        print(v)
        print(score)


    print('Fim do __main__')
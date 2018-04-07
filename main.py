from ModuloBabelNetAPI.ModuloClienteBabelNetAPI import ClienteBabelAPI
from ModuloOxfordAPI.ModuloClienteOxfordAPI import ClienteOxfordAPI
from ModuloExtrator.ExtratorSinonimos import ExtratorSinonimos
from ValidadorRanking.Validador import ValidadorRankingSemEval2007
from pywsd.lesk import cosine_lesk as cosine_lesk
from nltk.corpus import wordnet as wordnet
from Utilitarios import Utilitarios
from sys import argv

def testar_minha_abordagem(configs, metrica):
    configs_semeval2007 = configs['semeval2007']
    todas_metricas = configs_semeval2007['metricas']['separadores'].keys()

    respostas_geradas = dict()

    cli_babelnet = ClienteBabelAPI(configs)
    cli_oxford = ClienteOxfordAPI(configs)

    extrator_sinonimos = ExtratorSinonimos(configs, cli_oxford, cli_babelnet)
    validador_semeval2007 = ValidadorRankingSemEval2007(configs)

    dir_arquivo_teste = configs_semeval2007["dir_arquivo_teste"]
    casos_entrada = validador_semeval2007.ler_entrada_teste(dir_arquivo_teste)

    for lemma in casos_entrada:
        respostas_geradas[lemma] = dict()

        for id_entrada in casos_entrada[lemma]:
            palavra, pos = lemma.split('.')
            frase = id_entrada['frase']

            codigo = id_entrada['codigo']

            sinonimos = extrator_sinonimos.busca_sinonimos(palavra, pos, 'baseline', contexto=frase)
            sinonimos = extrator_sinonimos.ordenar_por_frequencia(sinonimos)

            try:
                sinonimos.remove(palavra)
            except: pass

            limite_superior = int(configs_semeval2007['metricas']['limites'][metrica])
            respostas_geradas[lemma][codigo] = [e.replace('_', ' ') for e in sinonimos[:limite_superior]]

    return respostas_geradas


def exibir_todos_resultados(todos_participantes, validador_semeval2007, nome_minha_abordagem):
    lista_todos_participantes = todos_participantes.values()
    todas_dimensoes = todos_participantes[todos_participantes.keys()[0]].keys()
    
    for dimensao in todas_dimensoes:
        print('DIMENSAO: ' + dimensao)
        validador_semeval2007.ordenar_scores(lista_todos_participantes, dimensao)

        indice = 1
        for participante in lista_todos_participantes:
            marcador = "" if participante['nome'] != nome_minha_abordagem else " <<<<"
            print(str(indice) + ' - ' + participante['nome'] + '  -  ' + str(participante[dimensao]) + marcador)

            indice += 1

        raw_input('\nPressione <enter> para proxima medida')

# obter frases do caso de entrada
def obter_frases_da_base(validador_semeval2007, configs):
    entrada = validador_semeval2007.ler_entrada_teste(configs['semeval2007']['dir_arquivo_teste'])

    for lemma in entrada:
        for id_entrada in entrada[lemma]:
            pos = lemma.split('.')[1]
            frase = id_entrada['frase']
            palavra = id_entrada['palavra']

            resultados_desambiguador = [r for r in cosine_lesk(frase, palavra, nbest=True, pos=pos) if r[0]]


if __name__ == '__main__':
    configs = Utilitarios.carregar_configuracoes('configuracoes.json')   
    validador_semeval2007 = ValidadorRankingSemEval2007(configs)

    todas_metricas = configs['semeval2007']['metricas']['limites']    

    for metrica in todas_metricas:        
        submissao_gerada = testar_minha_abordagem(configs, metrica)
        nome_minha_abordagem = configs['semeval2007']['nome_minha_abordagem'] + '.' + metrica

        todos_participantes = validador_semeval2007.obter_score_participantes(metrica)
        nome_minha_abordagem = validador_semeval2007.formatar_submissao(nome_minha_abordagem, submissao_gerada)

        resultados_minha_abordagem = validador_semeval2007.calcular_score_abordagem(configs['dir_saidas_rankeador'], nome_minha_abordagem)
        todos_participantes[nome_minha_abordagem] = resultados_minha_abordagem
        exibir_todos_resultados(todos_participantes, validador_semeval2007, nome_minha_abordagem)


        print('\n\n')

    print('\n\nFim algoritmo')
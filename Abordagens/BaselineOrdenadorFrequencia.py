from SemEval2007 import obter_gabarito_rankings_semeval
from Utilitarios import Utils
from ValidadorRanking.Validadores import GeneralizedAveragePrecisionMelamud

class BaselineOrdenadorFrequencia(object):
    def __init__(self):
        pass

    def iniciar(self, configs, dir_arquivo_saida):
        validador_gap = GeneralizedAveragePrecisionMelamud(Utils.configs)
        resultado = {}
        gabarito = obter_gabarito_rankings_semeval(configs)

        gap_acc = 0
        cont = 0

        resultado_correto = []

        candidatos = dict()

        for entrada in gabarito:
            chave = str(entrada).split(' ')[0]
            if not chave in candidatos:
                candidatos[chave] = set()

            candidatos[chave].update([p for p in gabarito[entrada].keys()])

        for entrada in gabarito:
            palavras = list(candidatos[str(entrada).split(' ')[0]])

            res_ordenados = Utils.ordenar_palavras(palavras)
            #res_ordenados = [p for p in gabarito[entrada].keys() if len(p.split(' ')) > 1] + res_ordenados

            vetor = []
            for i in range(1, len(res_ordenados) + 1):
                v = [res_ordenados[i-1], i]
                vetor.append(v)

            for elemento in vetor:
                if len(elemento[0].split(' ')) > 1: elemento[1] = 1

            gabarito_anotado = []

            for sinonimo in gabarito[entrada]:
                gabarito_anotado.append([sinonimo, gabarito[entrada][sinonimo]])

            print('\n')
            print('1. Gabarito: ' + str(gabarito[entrada]))
            print('2. Gabarito: ' + str(gabarito_anotado))
            print('Minha sugestao: ' + str(vetor))
            print('\n')

            gap = validador_gap.calcular(gabarito_anotado, vetor)
            print('-> GAP: ' + str(gap))
            print('\n\n')

            if gap == 1.0:
                resultado_correto.append(gabarito_anotado)

            gap_acc += gap
            cont += 1

        gap_medio = float(gap_acc) / float(cont)
        print('\n\n\n GAP MEDIO: ' + str(gap_medio))
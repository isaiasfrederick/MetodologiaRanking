from SemEval2007 import obter_gold_rankings

class BaselineOrdenadorFrequencia(object):
    def __init__(self):
        pass

    def iniciar(self, configs, dir_arquivo_saida):
        gabarito = obter_gold_rankings(configs)

        for e in gabarito:
            print('-> ' + str(e) + ' - ' + str(gabarito[e]))
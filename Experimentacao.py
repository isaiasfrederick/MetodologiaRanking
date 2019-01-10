from nltk.corpus import wordnet as wn
from ModuloClienteOxAPI import BaseOx


class ValidadorInventarioWordnet(object):
    @staticmethod
    def caso_entrada(palavra, gabarito, top10):
        total_corretos = list(set(gabarito.keys()) & set(top10))
        best_gabarito = gabarito[sorted(gabarito.keys(), reverse=True)[0]]

        intersecao_palavras_wornet = [ ]
        diferenca_palavras_wordnet = [ ]

        for s in wn.synsets(palavra):
            intersecao = list(set(s.lemma_names()) & set(gabarito.keys()))
            intersecao_palavras_wornet += intersecao

        diferenca_palavras_wordnet = list(set(gabarito.keys()) - set(intersecao_palavras_wornet))
        intersecao_palavras_wornet = list(set(intersecao_palavras_wornet))
      
        max_value = max(gabarito.values())
        best_palavras = [p for p in gabarito.keys() if gabarito[p] == max_value]

        if list(set(best_palavras) & set(top10)):
            best_preditas = list(set(best_palavras) & set(top10))
        else:
            best_preditas = [ ]

        try:
            if best_gabarito == top10[0]: best_correto = True
            else: best_correto = False
        except: best_correto = False

        print('PALAVRA: ' + palavra)
        print('GABARITO: ' + str(gabarito))
        print('PREDITO: ' + str(top10))
        print('TOTAL CORRETOS: ' + str(len(total_corretos)))
        print('CORRETOS: ' + str(total_corretos))        
        print('BEST CORRETAS: ' + str(best_palavras))

        if best_preditas:
            print('BEST PREDITAS: ' + str(best_preditas))

        if intersecao_palavras_wornet:
            print('Intersecao: ' + str(intersecao_palavras_wornet))
            print('Total palavras fora da Wordnet: ' + str(len(diferenca_palavras_wordnet)))

            if not diferenca_palavras_wordnet:
                print('Diferenca: ' + str(diferenca_palavras_wordnet))

        print('\n')

class ValidadorInventarioOxford(object):
    @staticmethod
    def caso_entrada(palavra, gabarito, top10):
        pass
        
    @staticmethod
    def caso_entrada_(palavra, gabarito, top10):
        base_ox = BaseOx(None)

        total_corretos = list(set(gabarito.keys()) & set(top10))
        best_gabarito = gabarito[sorted(gabarito.keys(), reverse=True)[0]]

        intersecao_palavras_oxford = [ ]
        diferenca_palavras_oxford = [ ]

        obj_unificado_oxford = BaseOx.construir_objeto_unificado(palavra)
        todas_definicoes = BaseOx.obter_definicoes(palavra)

        for definicao in todas_definicoes:
            pass
            #sinonimos = BaseOx.

        intersecao = list(set(s.lemma_names()) & set(gabarito.keys()))
        intersecao_palavras_wornet += intersecao

        for s in wn.synsets(palavra):
            intersecao = list(set(s.lemma_names()) & set(gabarito.keys()))
            intersecao_palavras_oxford += intersecao

        diferenca_palavras_oxford = list(set(gabarito.keys()) - set(intersecao_palavras_oxford))
        intersecao_palavras_oxford = list(set(intersecao_palavras_oxford))
      
        max_value = max(gabarito.values())
        best_palavras = [p for p in gabarito.keys() if gabarito[p] == max_value]

        if list(set(best_palavras) & set(top10)):
            best_preditas = list(set(best_palavras) & set(top10))
        else:
            best_preditas = [ ]

        try:
            if best_gabarito == top10[0]: best_correto = True
            else: best_correto = False
        except: best_correto = False

        print('PALAVRA: ' + palavra)
        print('GABARITO: ' + str(gabarito))
        print('PREDITO: ' + str(top10))
        print('TOTAL CORRETOS: ' + str(len(total_corretos)))
        print('CORRETOS: ' + str(total_corretos))        
        print('BEST CORRETAS: ' + str(best_palavras))

        if best_preditas:
            print('BEST PREDITAS: ' + str(best_preditas))

        if intersecao_palavras_oxford:
            print('Intersecao: ' + str(intersecao_palavras_oxford))
            print('Total palavras fora da Wordnet: ' + str(len(diferenca_palavras_oxford)))

            if not diferenca_palavras_oxford:
                print('Diferenca: ' + str(diferenca_palavras_oxford))

        print('\n')
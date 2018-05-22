class ValidadorInventarioWordnet(object):
    @staticmethod
    def caso_entrada(palavra, gabarito, top10):
        total_corretos = list(set(gabarito.keys()) & set(top10))
        best_gabarito = gabarito[sorted(gabarito.keys(), reverse=True)[0]]

        max_value = max(gabarito.values())
        best_palavras = [p for p in gabarito.keys() if gabarito[p] == max_value]

        if list(set(best_palavras) & set(top10)):
            best_preditas = list(set(best_palavras) & set(top10))
        else:
            best_preditas = []

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

        print('\n')
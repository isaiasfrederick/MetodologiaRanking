from pywsd.lesk import cosine_lesk

class Desambiguador(object):
    def __init__(self):
        pass

    def desambiguar(self, frase, palavra, pos=None):
        return cosine_lesk(frase, palavra, pos=pos, nbest=True)
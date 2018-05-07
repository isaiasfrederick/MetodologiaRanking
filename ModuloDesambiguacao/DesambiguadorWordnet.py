from pywsd.lesk_isaias import cosine_lesk

class DesambiguadorWordnet(object):
    def __init__(self, configs):
        pass

    def adapted_cosine_lesk(self, frase, palavra, pos=None):
        return cosine_lesk(frase, palavra, pos=pos, nbest=True)
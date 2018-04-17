from nltk.corpus import wordnet as wn

# esta classe funcionara como um "casador" de definicoes de diferentes fontes da abordagem
class RepositorioCentralConceitos:
    def __init__(self, configs, ):
        self.configs = configs

    def mesclar_wordnet_oxford(self, lemma, obj_oxford):
        todos_synsets = wn.synsets(lemma, pos)
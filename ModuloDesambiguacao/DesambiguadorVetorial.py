from Abordagens.RepresentacaoVetorial import RepVetorial
from nltk.corpus import wordnet as wn


""" Desambigua uma palavra usando a Wordnet de """
class DesambiguadoVetorial(object):
    def __init__(self, configs, representacao_vetorial):
        self.representacao_vetorial = representacao_vetorial
        self.configs = configs

    def desambiguar(self, palavra, pos, contexto):
        synsets = wn.synsets(palavra, pos)
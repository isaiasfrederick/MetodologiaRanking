from RepositorioCentralConceitos import CasadorConceitos
from pywsd.utils import lemmatize, porter, lemmatize_sentence
from Utilitarios import Util
import traceback
from textblob import TextBlob
from pywsd.cosine import cosine_similarity as cos_sim
#from pywsd.lesk_isaias import cosine_lesk
from nltk.corpus import stopwords, wordnet
from nltk import pos_tag, word_tokenize
from ModuloExtrator.ExtratorWikipedia import ExtratorWikipedia
import itertools
import inspect
import re
import os

class DesWikipedia(object):
    def __init__(self, cfgs):
        self.cfgs = cfgs
        self.usar_cache = True
        self.ext_wikipedia = ExtratorWikipedia(self.cfgs)

    def extrair_entidades(self, ctx):
        return [ ]

    # Dado o nome de uma determinada entidade, ja desambiguada,
    # consulta pela mesma a partir de uma URL base para consulta de verbetes
    def consultar_entidade(self, nome):
        nome = nome.replace(" ", "_")

        url = self.cfgs['wikipedia']['url_base_verbete']+'/'+nome

        try:
            texto = self.ext_wikipedia.obter_texto(url)
            return texto
        except Exception, e:            
            print("Excecao na obtencao da pagina '%s'"%url)
            print("Tipo Excecao: "+str(e)+"\n")
            traceback.print_stack()
            print("\n")

        return None

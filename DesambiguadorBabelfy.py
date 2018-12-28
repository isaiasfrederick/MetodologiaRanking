from RepositorioCentralConceitos import CasadorConceitos
from pywsd.utils import lemmatize, porter, lemmatize_sentence
from Utilitarios import Util
from textblob import TextBlob
from pywsd.cosine import cosine_similarity as cos_sim
#from pywsd.lesk_isaias import cosine_lesk
import json
from nltk.corpus import stopwords, wordnet
from nltk import pos_tag
import itertools
import inspect
import requests
import re
import os

# Cheque a API em http://babelfy.org/guide#Disambiguateatext
class DesBabelfy(object):
    def __init__(self, cfgs):
        self.cfgs = cfgs

        self.usar_cache = True
        self.dir_cache = cfgs['oxford']['cache']['desambiguador']

    def desambiguar(self, ctx, ambigua, nbest=True):
        app_key = self.cfgs['babelnet']['app_key']
        url = self.cfgs['babelnet']['url_desambiguador']%(ctx, ambigua, app_key)

        print("\n\n@@@ URL: %s\n\n"%url)

        try:
            obj_json = requests.get(url).json()
            return obj_json
        except:
            return None

    def testar(self):
        frase = raw_input("FRASE: ")
        ambigua = raw_input("AMBIGUA: ")

        saida = self.desambiguar(frase, ambigua, nbest=True)

        print("\n")
        print(json.dumps(saida, indent=4))
        print("\n")
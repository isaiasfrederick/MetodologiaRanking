from RepositorioCentralConceitos import CasadorConceitos
from pywsd.utils import lemmatize, porter, lemmatize_sentence
from Utilitarios import Util
from textblob import TextBlob
from pywsd.cosine import cosine_similarity as cos_sim
#from pywsd.lesk_isaias import cosine_lesk
from nltk.corpus import stopwords, wordnet
from nltk import pos_tag, word_tokenize
import itertools
import inspect
import requests
import re
import os

# Cheque a API em http://babelfy.org/guide#Disambiguateatext
class DesBabelfy(object):
    def __init__(self, cfgs, base_ox):
        self.cfgs = cfgs
        self.base_ox = base_ox
        self.rep_conceitos = CasadorConceitos(self.cfgs, self.base_ox)

        self.usar_cache = True
        self.dir_cache = cfgs['oxford']['cache']['desambiguador']

    def desambiguar(self, ctx, ambigua, nbest=True):
        app_key = self.cfgs['babelnet']['app_key']
        url = self.cfgs['babelnet']['url_desambiguador']%(ctx, ambigua, app_key)

        raw_input("\n\n@@@ URL: %s\n\n"%url)

        try:
            return requests.get(url).json()
        except:
            return None
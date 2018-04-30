from CasadorDefinicoes.RepositorioCentralConceitos import CasadorConceitos
from pywsd.utils import lemmatize, porter, lemmatize_sentence
from ModuloUtilitarios.Utilitarios import Utilitarios
from pywsd.cosine import cosine_similarity as cos_sim
from pywsd.lesk_isaias import cosine_lesk
from ModuloOxfordAPI.ModuloClienteOxfordAPI import *
from nltk.corpus import stopwords, wordnet
from nltk import pos_tag, word_tokenize
from nltk.corpus import wordnet
from itertools import chain
import re


class DesambiguadorOxford(object):
    def __init__(self, configs, base_unificada_oxford):
        self.configs = configs
        self.base_unificada_oxford = base_unificada_oxford
        self.rep_conceitos = CasadorConceitos(self.configs, self.base_unificada_oxford)

    # Retira relacoes semanticas a partir da Wordnet
    def extrair_relacao_semantica(self, lemma, palavras_arg):
        palavras = list(palavras_arg)
        casamentos = dict()

        for p in palavras:
            casamentos[p] = dict()

        for synset in wordnet.synsets(lemma):
            pass

        return []

    """ Gera a assinatura a partir de um significado Oxford a partir dos parametros """
    def assinatura_significado_aux(self, lema, pos, definicao, exemplos, extrair_relacao_semantica):
        retornar_valida = Utilitarios.retornar_valida_pra_indexar

        assinatura = []
        assinatura += retornar_valida(definicao.replace('.', ''))

        if exemplos:
            assinatura += list(chain(*[retornar_valida(ex).split() for ex in exemplos]))

        if extrair_relacao_semantica:
            nova_definicao = definicao.replace(lema, '')
            substantivos = self.rep_conceitos.extrair_substantivos(nova_definicao)

            hiperonimos_extraidos = self.rep_conceitos.extrair_hiperonimos_detectados(lema, pos, definicao)
            for h in hiperonimos_extraidos:
                dist_cosseno = Utilitarios.cosseno(definicao, wordnet.synset(h).definition())
                print('\t- ' + str(h) + '  -  ' + str(dist_cosseno) + ' - ' + str(hiperonimos_extraidos[h]))
                for h2 in wordnet.synsets(h.split('.')[0]):
                    if h2.name() != h:
                        dist_cosseno = Utilitarios.cosseno(definicao, h2.definition())
                        print('\t\t- ' + h2.name() + '  -  ' + str(dist_cosseno))

        assinatura += lema
        assinatura = [p for p in assinatura if len(p) > 1]

        return assinatura

    """Metodo treinado por exemplos"""
    def desambiguar_por_exemplos(self, frase, palavra_ambigua, pos, nbest=True, lemma=True, stem=True, stop=True):
        pass

    """Treinador desambiguador por exemplos"""
    def treinar_desambiguador_exemplos(self, sentidos):
        pass

    """Metodo Cosseno feito para o dicionario de Oxford"""
    def adapted_cosine_lesk(self, frase, ambigua, pos, nbest=True, lematizar=True, stem=True, stop=True, usar_ontologia=False, usar_exemplos=False):
        self.rep_conceitos = CasadorConceitos(self.configs, self.base_unificada_oxford)

        # (self, lemma, lematizar=True, stem=False, stop=True, extrair_relacao_semantica=False):
        assinaturas = self.assinatura_significado(ambigua)
        assinaturas = [a for a in assinaturas if pos in a[0]]

        frase = " ".join(lemmatize_sentence(frase))
        pontuacao = []

        if usar_exemplos:
            pass

        for a in assinaturas:
            ass_tmp = a[3]

            if stop:
                ass_tmp = [i for i in ass_tmp if i not in stopwords.words('english')]
            if lematizar:
                ass_tmp = [lemmatize(i) for i in ass_tmp]
            if stem:
                ass_tmp = [porter.stem(i) for i in ass_tmp]

            pontuacao.append((cos_sim(frase, " ".join(ass_tmp)), a[0:3]))

        resultado = [(s, p) for p, s in sorted(pontuacao, reverse=True)]

        return resultado if nbest else [resultado[0]]

    """Gera uma assinatura de um significado Oxford para aplicar Cosseno"""
    def assinatura_significado(self, lema, lematizar=True, stem=False, stop=True, extrair_relacao_semantica=False):
        resultado = self.base_unificada_oxford.iniciar_consulta(lema)
        lema = lemmatize(lema)

        assinaturas_significados = []  #(nome, definicao, exemplos)

        for pos in resultado.keys():
            significados = resultado[pos].keys()

            indice = 1
            for s in significados:
                nome_sig = "%s.%s.%d" % (lema, pos, indice)
                indice += 1
                exemplos = resultado[pos][s]['exemplos']

                # nome, definicao, exemplos, assinatura
                synset_corrente = [nome_sig, s, exemplos, []]
                assinaturas_significados.append(synset_corrente)

                # Colocando exemplos na assinatura
                synset_corrente[3] += self.assinatura_significado_aux(lema, pos, s, exemplos, extrair_relacao_semantica)

                sig_secundarios = resultado[pos][s]['def_secs']

                for ss in sig_secundarios:
                    nome_sig_sec = "%s.%s.%d" % (lema, pos, indice)
                    exemplos_secundarios = resultado[pos][s]['def_secs'][ss]['exemplos']
                    synset_corrente_sec = [nome_sig_sec, ss, exemplos_secundarios, []]
                    assinaturas_significados.append(synset_corrente_sec)

                    synset_corrente_sec[3] += self.assinatura_significado_aux(lema, pos, ss, exemplos_secundarios, extrair_relacao_semantica)

                    indice += 1

        for s in assinaturas_significados:
            if stop == True:
                s[3] = [i for i in s[3] if i not in stopwords.words('english')]
            if lematizar == True:
                s[3] = [lemmatize(i) for i in s[3]]
            if stem == True:
                s[3] = [porter.stem(i) for i in s[3]]

        return [tuple(a) for a in assinaturas_significados]

    def retornar_valida(self, frase):
        return Utilitarios.retornar_valida(frase)
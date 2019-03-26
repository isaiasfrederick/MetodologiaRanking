#! coding: utf-8
from Utilitarios import Util

import os
import re
import string
import itertools # Para gerar as combinacoes de desambiguacao ""all-words"

import gc

from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
from nltk import word_tokenize, pos_tag

from pywsd.cosine import cosine_similarity as cos_sim
from pywsd.utils import lemmatize, porter, lemmatize_sentence, synset_properties

import pywsd.lesk
from textblob import TextBlob

EN_STOPWORDS = stopwords.words('english')

import traceback

class DesWordnet(object):    
	cache_assinaturas = dict()

	def __init__(self, configs):
		self.usar_cache = False
		self.dir_cache = configs['wordnet']['cache']['desambiguador']
		self.configs = configs

	# Converte o resultado da desambiguacao 
	# (Nome Synset, pontuacao) => (("Nome Synset;lema", Definicao, Frases]), Pontuacao)
	def convert_res(self, res_desambiguacao_wn, ambiguous_word):
		res_desambiguacao = [ ]

		for reg in res_desambiguacao_wn:
			rnome = reg[0].name()+";"+ambiguous_word
			rdefinicao = reg[0].definition()
			rfrases = reg[0].examples()
			pt = reg[1]

			res_desambiguacao.append([[rnome, rdefinicao, rfrases], pt])

		return res_desambiguacao

	# Esta funcao abstrai a funcao Cosine Lesk para a biblioteca WSD
	def cosine_lesk(self, context_sentence, ambiguous_word, \
					pos=None, lemma=True, stem=True, hyperhypo=True, \
					stop=True, context_is_lemmatized=False, \
					nbest=False, remove_ambiguous_word=True, convert=True):

		if remove_ambiguous_word:
			context_sentence = context_sentence.replace(ambiguous_word, "")

		if pos:
			pos = Util.cvsr_pos_semeval_wn(pos)

		res_des = pywsd.lesk.cosine_lesk(context_sentence, ambiguous_word, pos=pos, nbest=True)

		# Converte para o padrao:
		# [[u'clean.Verb.1', u'Make clean; remove dirt, marks, or stains from.', [ ]], 0.1]
		if convert: return self.convert_res(res_des, ambiguous_word)
		else: return res_des

	def adapted_cosine_lesk(self, contexto, palavra, pos=None, busca_ampla=False):
		return cosine_lesk_inventario_estendido(contexto, palavra, pos=pos, nbest=True, busca_ampla=busca_ampla)

	# Realiza o processo de desambiguacao gerando um Ranking que usa da medida de cosseno como critério de ordenação
	# A partir disto, realiza a coleta de palavras correlatas ao significado sugerido
	def extrair_sinonimos(self, ctx, palavra, pos=None, \
							usar_exemplos=False, busca_ampla=False, \
							repetir=True, coletar_todos=True):

		max_sinonimos = 10

		print('Executando desambiguador Wordnet...')
		resultado = self.adapted_cosine_lesk(ctx, palavra, pos, busca_ampla=busca_ampla)
		print('Desambiguador executado...\n')

		sinonimos = [ ]

		try:
			if resultado[0][1] == 0:
				resultado = [resultado[0]]				
				repetir = False

				if False:
					sinonimos = [ ]
					try:
						for synset in [s[0] for s in resultado]:
							for lema in synset.lemma_names():
								if not l in sinonimos:
									sinonimos.append(l)
					except: pass

					return sinonimos[:max_sinonimos]
			else:
				resultado = [item for item in resultado if item[1] > 0]
		except:
			resultado = [ ]

		continuar = bool(resultado)
		
		while len(sinonimos) < max_sinonimos and continuar:
			len_sinonimos = len(sinonimos)

			for item in resultado:
				synset, pontuacao = item

				if len(sinonimos) < max_sinonimos:
					try:
						sinonimos_tmp = [s for s in synset.lemma_names() if not Util.e_mpalavra(s)]
						sinonimos_tmp = list(set(sinonimos_tmp) - set(sinonimos))

						if coletar_todos: sinonimos += sinonimos_tmp
						elif sinonimos_tmp: sinonimos += [sinonimos_tmp[0]]

					except: pass
				else:
					continuar = False

			if repetir == False: continuar = False
			elif len_sinonimos == len(sinonimos): continuar = False

		return sinonimos[:max_sinonimos]

	def banerjee_lesk(self, ctx, ambigua, pos, nbest=True, \
						lematizar=True, stem=True, stop=True, \
						usr_ex=False, janela=3):

		# Casamentos cartesianos das diferentes definicoes
		solucoes_candidatas = [ ]

		# nltk.help.upenn_tagset() -> Nouns, Adverbs, Verbs e Adjectives
		tags_validas = self.configs['pos_tags_treebank']

		ctx_blob = TextBlob(ctx)

		cache_assinaturas_local={ }

		i_tokens_validos = [ ]
		i_amb = None # Indice palavra ambigua

		i_token = 0

		# [('The', 'DT'), ('titular', 'JJ'), ('threat', 'NN'), ('of', 'IN'), ...]
		tokens_validos_tmp = [(token_tmp, tag_tmp) for (token_tmp, tag_tmp) in ctx_blob.tags if tag_tmp in tags_validas]

		max_combinacoes = 1

		tv = [ ]

		for token_tmp, tag_tmp in tokens_validos_tmp:
			if token_tmp == ambigua:
				i_amb = i_token

				# Delimitadores de indices
				imin = max(i_token-janela, 0) # nao pode exister indice menor que ZERO
				imax = min(i_token+janela, len(tokens_validos_tmp)-1) #  e nem maior que LENGTH

				# Itera a janela do contexto a partir da identificacao da palavra-target
				for i in range(imin, imax+1):
					token, tag = tokens_validos_tmp[i]

					# Excepcionalmente, 'J' corresponde à classe de adverbios:
					# https://stackoverflow.com/questions/15388831/what-are-all-possible-pos-tags-of-nltk
					if tag[0].lower() == 'j': pos_wn = 'a'
					else: pos_wn = tag[0].lower()

					defs = wn.synsets(token, pos_wn)

					if defs:
						max_combinacoes *= len(defs) if len(defs) > 0 else 1
						solucoes_candidatas.append(defs)
						#cache_assinaturas_local[token] = pywsd.lesk.simple_signature(token, pos=pos_wn)
					elif i == i_amb: pass # Se nao ha candidato para palavra a ser desambiguada, abortar.

					tv.append(token)
					i_tokens_validos.append(i_token)

			i_token+=1

		print("\n")
		print(tv)
		raw_input("\n\nTotal de combinacoes: "+str(max_combinacoes)+"\n")

		return 0.00


def criar_inventario_des_wn(lema, pos=None, busca_ampla=False):
	inventario = set()
	inventario.update(wn.synsets(lema, pos))

	if busca_ampla == True:
		for synset in wn.synsets(lema, pos):
			for hiper in synset.hypernyms():
				for hipo in hiper.hyponyms():
					inventario.add(hipo)

	return list(inventario)

def compare_overlaps_greedy(context, synsets_signatures):
	"""
	Calculate overlaps between the context sentence and the synset_signature
	and returns the synset with the highest overlap.

	Note: Greedy algorithm only keeps the best sense,
	see https://en.wikipedia.org/wiki/Greedy_algorithm

	Only used by original_lesk(). Keeping greedy algorithm for documentary sake,
	because original_lesks is greedy.
	"""
	max_overlaps = 0; lesk_sense = None
	for ss in synsets_signatures:
		overlaps = set(synsets_signatures[ss]).intersection(context)
		if len(overlaps) > max_overlaps:
			lesk_sense = ss
			max_overlaps = len(overlaps)
	return lesk_sense

def compare_overlaps(context, synsets_signatures, \
					 nbest=False, keepscore=False, normalizescore=False):
	"""
	Calculates overlaps between the context sentence and the synset_signture
	and returns a ranked list of synsets from highest overlap to lowest.
	"""
	overlaplen_synsets = [ ] # a tuple of (len(overlap), synset).
	for ss in synsets_signatures:
		overlaps = set(synsets_signatures[ss]).intersection(context)
		overlaplen_synsets.append((len(overlaps), ss))

	# Rank synsets from highest to lowest overlap.
	ranked_synsets = sorted(overlaplen_synsets, reverse=True)

	# Normalize scores such that it's between 0 to 1.
	if normalizescore:
		total = float(sum(i[0] for i in ranked_synsets))
		ranked_synsets = [(i/total,j) for i,j in ranked_synsets]

	if not keepscore: # Returns a list of ranked synsets without scores
		ranked_synsets = [i[1] for i in sorted(overlaplen_synsets, \
											   reverse=True)]
	if nbest: # Returns a ranked list of synsets.
		return ranked_synsets
	else: # Returns only the best sense.
		return ranked_synsets[0]

def original_lesk(context_sentence, ambiguous_word, dictionary=None):
	"""
	This function is the implementation of the original Lesk algorithm (1986).
	It requires a dictionary which contains the definition of the different
	sense of each word. See http://dl.acm.org/citation.cfm?id=318728
	"""
	ambiguous_word = lemmatize(ambiguous_word)
	if not dictionary: # If dictionary is not provided, use the WN defintion.
		dictionary = { }
		for ss in wn.synsets(ambiguous_word):
			ss_definition = synset_properties(ss, 'definition')
			dictionary[ss] = ss_definition
	best_sense = compare_overlaps_greedy(context_sentence.split(), dictionary)
	return best_sense

def simple_signature(ambiguous_word, pos=None, lemma=True, stem=False, \
					 hyperhypo=True, stop=True, busca_ampla=False):
	"""
	Returns a synsets_signatures dictionary that includes signature words of a
	sense from its:
	(i)   definition
	(ii)  example sentences
	(iii) hypernyms and hyponyms
	"""
	synsets_signatures = { }
	#for ss in wn.synsets(ambiguous_word):
	for ss in criar_inventario_des_wn(ambiguous_word, pos=pos, busca_ampla=busca_ampla):
		try: # If POS is specified.
			if pos and str(ss.pos()) != pos:
				continue
		except:
			if pos and str(ss.pos) != pos:
				continue

		signature = [ ]
		# Includes definition.
		ss_definition = synset_properties(ss, 'definition')

		ss_definition = re.sub('[-_]', ' ', ss_definition)
		ss_definition = re.sub('[,.;]', ' ', ss_definition)

		signature += ss_definition.split(' ')

		# Includes examples
		ss_examples = synset_properties(ss, 'examples')
		signature+=list(itertools.chain(*[i.split() for i in ss_examples]))
		
		# Includes lemma_names.
		ss_lemma_names = synset_properties(ss, 'lemma_names')

		try:
			# Includes lemma_names.
			for h in ss.hypernyms():
				ss_lemma_names = synset_properties(h, 'lemma_names')
		except: pass

		signature+= ss_lemma_names

		# Optional: includes lemma_names of hypernyms and hyponyms.
		if hyperhypo:
			ss_hyponyms = synset_properties(ss, 'hyponyms')
			ss_hypernyms = synset_properties(ss, 'hypernyms')
			ss_hypohypernyms = ss_hypernyms+ss_hyponyms
			ss_hypohypernyms = ss_hypernyms
			signature+= list(itertools.chain(*[i.lemma_names() for i in ss_hypohypernyms]))

		# Optional: removes stopwords.
		if stop == True:
			signature = [i for i in signature if i not in EN_STOPWORDS]
		# Lemmatized context is preferred over stemmed context.
		if lemma == True:
			signature = [lemmatize(i) for i in signature]
		# Matching exact words may cause sparsity, so optional matching for stems.
		if stem == True:
			signature = [porter.stem(i) for i in signature]

		synsets_signatures[ss] = signature

	return synsets_signatures

def simple_lesk(context_sentence, ambiguous_word, \
				pos=None, lemma=True, stem=False, hyperhypo=True, \
				stop=True, context_is_lemmatized=False, \
				nbest=False, keepscore=False, normalizescore=False):
	"""
	Simple Lesk is somewhere in between using more than the
	original Lesk algorithm (1986) and using less signature
	words than adapted Lesk (Banerjee and Pederson, 2002)
	"""
	# Ensure that ambiguous word is a lemma.
	ambiguous_word = lemmatize(ambiguous_word)
	# If ambiguous word not in WordNet return None
	if not wn.synsets(ambiguous_word):
		return None
	# Get the signatures for each synset.
	ss_sign = simple_signature(ambiguous_word, pos, lemma, stem, hyperhypo)
	# Disambiguate the sense in context.
	if context_is_lemmatized:
		context_sentence = context_sentence.split()
	else:
		context_sentence = lemmatize_sentence(context_sentence)
	best_sense = compare_overlaps(context_sentence, ss_sign, \
									nbest=nbest, keepscore=keepscore, \
									normalizescore=normalizescore)
	return best_sense

def adapted_lesk(context_sentence, ambiguous_word, \
				pos=None, lemma=True, stem=True, hyperhypo=True, \
				stop=True, context_is_lemmatized=False, \
				nbest=True, keepscore=True, normalizescore=False):
	"""
	This function is the implementation of the Adapted Lesk algorithm,
	described in Banerjee and Pederson (2002). It makes use of the lexical
	items from semantically related senses within the wordnet
	hierarchies and to generate more lexical items for each sense.
	see www.d.umn.edu/~tpederse/Pubs/cicling2002-b.pdf‎
	"""
	# Ensure that ambiguous word is a lemma.
	ambiguous_word = lemmatize(ambiguous_word)
	# If ambiguous word not in WordNet return None
	if not wn.synsets(ambiguous_word):
		return None
	# Get the signatures for each synset.
	ss_sign = simple_signature(ambiguous_word, pos, lemma, stem, hyperhypo)
	for ss in ss_sign:
		# Includes holonyms.
		ss_mem_holonyms = synset_properties(ss, 'member_holonyms')
		ss_part_holonyms = synset_properties(ss, 'part_holonyms')
		ss_sub_holonyms = synset_properties(ss, 'substance_holonyms')
		# Includes meronyms.
		ss_mem_meronyms = synset_properties(ss, 'member_meronyms')
		ss_part_meronyms = synset_properties(ss, 'part_meronyms')
		ss_sub_meronyms = synset_properties(ss, 'substance_meronyms')
		# Includes similar_tos
		ss_simto = synset_properties(ss, 'similar_tos')

		related_senses = list(set(ss_mem_holonyms+ss_part_holonyms+
								  ss_sub_holonyms+ss_mem_meronyms+
								  ss_part_meronyms+ss_sub_meronyms+ ss_simto))

		signature = list([j for j in itertools.chain(*[synset_properties(i, 'lemma_names')
											 for i in related_senses])
						  if j not in EN_STOPWORDS])

	# Lemmatized context is preferred over stemmed context
	if lemma == True:
		signature = [lemmatize(i) for i in signature]
	# Matching exact words causes sparsity, so optional matching for stems.
	if stem == True:
		signature = [porter.stem(i) for i in signature]
	# Adds the extended signature to the simple signatures.
	ss_sign[ss]+=signature

	# Disambiguate the sense in context.
	if context_is_lemmatized:
		context_sentence = context_sentence.split()
	else:
		context_sentence = lemmatize_sentence(context_sentence)
	best_sense = compare_overlaps(context_sentence, ss_sign, \
									nbest=nbest, keepscore=keepscore, \
									normalizescore=normalizescore)
	return best_sense

def cosine_lesk_inventario_estendido(context_sentence, ambiguous_word, \
				pos=None, lemma=True, stem=True, hyperhypo=True, \
				stop=True, context_is_lemmatized=False, \
				nbest=False, synsets_signatures=None, busca_ampla=False):
	"""
	In line with vector space models, we can use cosine to calculate overlaps
	instead of using raw overlap counts. Essentially, the idea of using
	signatures (aka 'sense paraphrases') is lesk-like.
	"""
	
	# Ensure that ambiguous word is a lemma.
	if lemma:
		ambiguous_word = lemmatize(ambiguous_word)

	# If ambiguous word not in WordNet return None
	#if not wn.synsets(ambiguous_word):
	if not criar_inventario_des_wn(ambiguous_word, busca_ampla=busca_ampla):
		return None

	if context_is_lemmatized:
		context_sentence = " ".join(context_sentence.split())
	else:
		context_sentence = " ".join(lemmatize_sentence(context_sentence))

	scores = [ ]

	chave_assinatura = "%s.%s.%s.%s.%s.%s" % (ambiguous_word, pos, lemma, stem, hyperhypo, busca_ampla)

	if not chave_assinatura in DesWordnet.cache_assinaturas:
		synsets_signatures = simple_signature(ambiguous_word, pos, lemma, stem, hyperhypo, busca_ampla=busca_ampla)

		DesWordnet.cache_assinaturas[chave_assinatura] = [ ]

		for ss, signature in synsets_signatures.items():
			# Lowercase and replace "_" with spaces.
			signature = " ".join(map(str, signature)).lower().replace("_", " ")
			# Removes punctuation.
			signature = [i for i in Util.word_tokenize(signature) \
						if i not in string.punctuation]

			signature = Util.normalizar_ctx(signature, stop=stop, lematizar=lemma, stem=stem)

			scores.append((cos_sim(context_sentence, " ".join(signature)), ss))

			DesWordnet.cache_assinaturas[chave_assinatura].append((ss, signature))

	else:
		synsets_signatures = DesWordnet.cache_assinaturas[chave_assinatura]

		for ss, signature in synsets_signatures:
			scores.append((cos_sim(context_sentence, " ".join(signature)), ss))

	if not nbest:
		return sorted(scores, reverse=True)[0][1]
	else:
		return [(j,i) for i,j in sorted(scores, reverse=True)]
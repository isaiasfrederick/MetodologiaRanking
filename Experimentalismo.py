import pywsd
import re
from SemEval2007 import ValidadorSemEval

def ler_entrada(configs, fonte="wordnet"):
    total_entradas_validas = 0
    total_entradas_invalidas = 0

    validador = ValidadorSemEval(configs)

    tipo = raw_input("Test ou trial? ").lower()
    dir_casos_entrada, dir_gabarito = configs['semeval2007'][tipo].values()

    casos_testes_tmp = validador.carregar_caso_entrada(dir_casos_entrada)
    gabarito = validador.carregar_gabarito(dir_gabarito)

    caso_entrada_tmp = validador.carregar_caso_entrada(dir_casos_entrada)
    gabarito = validador.carregar_gabarito(dir_gabarito)

    caso_entrada = dict()

    for lema in caso_entrada_tmp:
        for reg in caso_entrada_tmp[lema]:
            id_lema = reg['codigo']
            caso_entrada[lema + " " + str(id_lema)] = reg

    for lexelt in set(caso_entrada.keys()) & set(gabarito.keys()):
        frase = caso_entrada[lexelt]["frase"]

        palavra, pos = lexelt.replace(".", " ").split(" ")[:2] # mad.a 1446

        print("\n")
        print("TIPO BASE: " + tipo.upper())
        print("LEXELT: " + lexelt)
        #print("FRASE: " + frase)
        print("PALAVRA: " + palavra)
        print("PART-OF-SPEECH: " + pos)
        print("GABARITO: " + str(gabarito[lexelt]))
        print("\n\n")

        try:
            if fonte == 'wordnet':
                res_desambiguacao = pywsd.lesk.cosine_lesk(frase, palavra, pos=pos, nbest=True)
            elif fonte == 'oxford':
                pass

            try:
                if res_desambiguacao[0][1] > 0.0:
                    total_entradas_validas += 1
                else:
                    total_entradas_invalidas += 1
            except:
                total_entradas_invalidas += 1

            for reg in res_desambiguacao:
                definicao, pontuacao = reg
                print("\t%s - %s\t%f" % (definicao.name(), definicao.definition(), pontuacao))
                #print("\t%s" % str(definicao.lemma_names()))
                #print("\n")

        except Exception, e:
            pass

        print("\n\n")

    print("VALIDAS: " + str(total_entradas_validas))
    print("INVALIDAS: " + str(total_entradas_invalidas))
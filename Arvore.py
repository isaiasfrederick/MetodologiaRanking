class No(object):
    def __init__(self, pai, dado):
        self.pai = pai
        self.filhos = [ ]
        self.dado = dado

    def add_filho(self, no):
        self.filhos.append(no)

    def __str__(self):
        return "No: " + str(self.dado)

class Arvore(object):    
    def __init__(self, no):
        self.raiz = no
        self.resultado = [ ]

    def percorrer(self):
        self.perc_aux(self.raiz, self.raiz.dado)
        retorno = list(self.resultado)
        self.resultado = [ ]
        
        return retorno

    def perc_aux(self, no, caminho):
        for f in no.filhos:
            self.perc_aux(f, caminho+'/'+f.dado)
        self.resultado.append(caminho)

    def __str__(self):
        return "Arvore: "+str(self.raiz)

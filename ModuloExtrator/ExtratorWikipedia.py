class ColetorWikipedia(object):
    def __init__(self, configs):
        self.configs = configs
        self.prefixo_url = ""

    def obter_pagina(self, url):
        page = requests.get(url)
        tree = html.fromstring(page.content)
        return tree

    def buscar_tabela(self):
        url = ""
        tree = self.obter_pagina(url)
        xpath_lista_topo = '//*[@id="mw-content-text"]/div/dl[2]/dd/dl/dd/table'

        try:
            requests.session().cookies.clear()
        except: pass

        return tree.xpath(xpath_lista_topo)

    def retornar_lista(self, tabela):
        return [self.prefixo_url + t.get('href') for t in tabela.findall("tr/td[2]/a")]

    def salvar_textos(self, lista_urls):
        diretorio = ""
        caminho_xpath_conteudo_principal = '//*[@id="mw-content-text"]/div/p'

        lista_urls = [url for url in lista_urls[2:] if not 'List' in url]

        for url in lista_urls:
            tree = self.obter_pagina(url)
            elemento = tree.xpath(caminho_xpath_conteudo_principal)

            texto = [e.text_content() for e in elemento]

            texto = re.sub("(\[[a-zA-Z0-9]+\])", "", "".join(texto)).encode('utf-8')
            texto = re.sub("(\s[A-Z]\.\s)", " ", texto)
            texto = re.sub("(\[[a-z\s]+\])", "", texto)
            texto = re.sub("(\s[A-Z]\.)", "", texto)
            texto = re.sub("(\s[Ss][t]\.)", "Saint", texto)

            regex = "(?=([\d]*))(\.)(?=([\d]+\s*))"
            texto = re.sub(regex, ",", texto)

            print('Documento %s coletado!' % url)

            nome_arquivo = url.split('/').pop()
            caminho_arquivo = diretorio + nome_arquivo + '.txt'

            arq = open(caminho_arquivo, 'w')
            arq.write(texto)
            arq.close()
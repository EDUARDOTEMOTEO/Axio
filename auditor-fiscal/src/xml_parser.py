import xml.etree.ElementTree as ET

def extrair_dados_xml(caminho_arquivo):
    """
    Extrai dados detalhados de notas fiscais de mercadorias (NF-e - XML)
    incluindo NCM, CST, CFOP, valores e ICMS-ST.
    """
    produtos = []
    try:
        tree = ET.parse(caminho_arquivo)
        root = tree.getroot()
        
        # Namespace padrão da NF-e
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        
        # Dados do emitente e da nota
        emit = root.find('.//nfe:emit', ns)
        nome_emitente = emit.find('nfe:xNome', ns).text if emit is not None and emit.find('nfe:xNome', ns) is not None else "Desconhecido"
        cnpj_emitente = emit.find('nfe:CNPJ', ns).text if emit is not None and emit.find('nfe:CNPJ', ns) is not None else ""
        
        ide = root.find('.//nfe:ide', ns)
        numero_nota = ide.find('nfe:nNF', ns).text if ide is not None and ide.find('nfe:nNF', ns) is not None else ""
        
        # Chave de acesso
        inf_nfe = root.find('.//nfe:infNFe', ns)
        chave_acesso = inf_nfe.attrib.get('Id', '').replace('NFe', '') if inf_nfe is not None else ""

        # Varredura dos itens (produtos)
        det_list = root.findall('.//nfe:det', ns)
        for det in det_list:
            prod = det.find('nfe:prod', ns)
            imposto = det.find('nfe:imposto', ns)
            
            if prod is not None:
                x_prod = prod.find('nfe:xProd', ns).text if prod.find('nfe:xProd', ns) is not None else ""
                ncm = prod.find('nfe:NCM', ns).text if prod.find('nfe:NCM', ns) is not None else ""
                cfop = prod.find('nfe:CFOP', ns).text if prod.find('nfe:CFOP', ns) is not None else ""
                v_prod = float(prod.find('nfe:vProd', ns).text) if prod.find('nfe:vProd', ns) is not None else 0.0
                
                cst_pis = ""
                cst_icms = ""
                v_icms_st = 0.0
                
                if imposto is not None:
                    # PIS
                    pis_node = imposto.find('nfe:PIS', ns)
                    if pis_node is not None:
                        for child in pis_node:
                            cst_elem = child.find('nfe:CST', ns)
                            if cst_elem is not None and cst_elem.text:
                                cst_pis = cst_elem.text.strip()
                    
                    # ICMS (CST / CSOSN / vICMSSTRet)
                    icms_node = imposto.find('nfe:ICMS', ns)
                    if icms_node is not None:
                        for child in icms_node:
                            cst_element = child.find('nfe:CST', ns)
                            if cst_element is not None and cst_element.text:
                                cst_icms = cst_element.text.strip()
                                
                            csosn_element = child.find('nfe:CSOSN', ns)
                            if csosn_element is not None and csosn_element.text:
                                cst_icms = csosn_element.text.strip()
                                
                            v_st_element = child.find('nfe:vICMSSTRet', ns)
                            if v_st_element is not None and v_st_element.text:
                                try:
                                    v_icms_st = float(v_st_element.text)
                                except:
                                    pass

                produtos.append({
                    'chave_acesso': chave_acesso,
                    'nome_emitente': nome_emitente,
                    'cnpj_emitente': cnpj_emitente,
                    'numero_nota': numero_nota,
                    'x_prod': x_prod,
                    'ncm': ncm,
                    'cfop': cfop,
                    'v_prod': v_prod,
                    'cst_pis': cst_pis,
                    'cst_icms': cst_icms,
                    'v_icms_st': v_icms_st
                })
        return produtos
    except Exception as e:
        print(f"Erro ao ler XML: {e}")
        return []
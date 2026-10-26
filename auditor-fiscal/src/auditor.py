import os
from src.xml_parser import extrair_dados_xml
from src.tax_rules import auditar_produto  # Import com o nome correto da função

def executar_auditoria(pasta_entrada):
    """
    Executa o processo de leitura e auditoria em lote na pasta de XMLs.
    """
    print(f"Lendo notas fiscais na pasta: {pasta_entrada}...")
    
    produtos = []
    # Percorre os arquivos .xml presentes na pasta de entrada
    if os.path.exists(pasta_entrada):
        for arquivo in os.listdir(pasta_entrada):
            if arquivo.endswith(".xml"):
                caminho_arquivo = os.path.join(pasta_entrada, arquivo)
                prods = extrair_dados_xml(caminho_arquivo)
                if prods:
                    produtos.extend(prods)
    
    print(f"Total de produtos encontrados nas notas: {len(produtos)}")
    print("Iniciando auditoria de regras fiscais...\n")

    resultados_auditoria = []

    for produto in produtos:
        alertas = auditar_produto(produto)  # Chamada com o nome correto
        if alertas:
            resultados_auditoria.append({
                'produto': produto,
                'alertas': alertas
            })

    return resultados_auditoria
import os
import xml.etree.ElementTree as ET

# Tabela simplificada de NCMs com tributação monofásica de PIS/COFINS
NCMS_MONOFASICOS = [
    "3003", "3004",        # Medicamentos
    "3303", "3304", "3305", "3307",  # Perfumaria / Higiene
    "8708", "4011",        # Autopeças / Pneus
    "2710",                # Combustíveis e Lubrificantes
    "2201", "2202", "2203" # Bebidas Frias (Refrigerantes, Cervejas, Águas)
]

def validar_regras_fiscais_por_regime(prod, regime_tributario="Lucro Presumido"):
    """
    Aplica validações específicas de PIS, COFINS e ICMS-ST 
    com base no Regime Tributário da empresa.
    """
    alertas = []
    ncm = str(prod.get("ncm", "")).replace(".", "").strip()
    cst_pis = str(prod.get("cst_pis", "")).strip()
    cfop = str(prod.get("cfop", "")).strip()
    
    eh_monofasico = any(ncm.startswith(prefixo) for prefixo in NCMS_MONOFASICOS)

    # 1. Regras para o SIMPLES NACIONAL
    if regime_tributario == "Simples Nacional":
        if eh_monofasico:
            alertas.append({
                "tipo": "Oportunidade - Simples Nacional",
                "mensagem": f"Produto NCM {ncm} é Monofásico (PIS/COFINS recolhido na fábrica). Segregue esta receita no PGDAS-D para não pagar imposto em duplicidade."
            })

    # 2. Regras para o LUCRO PRESUMIDO
    elif regime_tributario == "Lucro Presumido":
        if cst_pis in ["50", "51", "52"]:
            alertas.append({
                "tipo": "Alerta - Lucro Presumido",
                "mensagem": f"No regime cumulativo (Lucro Presumido), a entrada (CFOP {cfop}) não gera direito a crédito direto de PIS/COFINS."
            })

    # 3. Regras para o LUCRO REAL
    elif regime_tributario == "Lucro Real":
        if (cfop.startswith("1") or cfop.startswith("2")) and cst_pis not in ["50", "01"]:
            if not eh_monofasico:
                alertas.append({
                    "tipo": "Oportunidade - Lucro Real",
                    "mensagem": f"Entrada de insumo/revenda (CFOP {cfop}) sem aproveitamento de crédito de PIS/COFINS (1,65% / 7,60%). Avalie a tomada de crédito no Sped."
                })

    return alertas


def processar_xml_nfe(caminho_xml, regime_tributario="Lucro Presumido"):
    """Lê o arquivo XML da NF-e e executa o motor de regras."""
    try:
        tree = ET.parse(caminho_xml)
        root = tree.getroot()
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        
        relatorio_xml = []
        
        det_elements = root.findall('.//nfe:det', ns)
        if not det_elements:
            det_elements = root.findall('.//det')
            
        for det in det_elements:
            prod_node = det.find('nfe:prod', ns) if det.find('nfe:prod', ns) is not None else det.find('prod')
            imposto_node = det.find('nfe:imposto', ns) if det.find('nfe:imposto', ns) is not None else det.find('imposto')
            
            if prod_node is not None:
                x_prod = prod_node.findtext('nfe:xProd', default='', namespaces=ns) or prod_node.findtext('xProd', default='')
                ncm = prod_node.findtext('nfe:NCM', default='', namespaces=ns) or prod_node.findtext('NCM', default='')
                cfop = prod_node.findtext('nfe:CFOP', default='', namespaces=ns) or prod_node.findtext('CFOP', default='')
                
                # Extrai CST PIS
                cst_pis = ""
                if imposto_node is not None:
                    pis_node = imposto_node.find('.//nfe:PIS', ns) or imposto_node.find('.//PIS')
                    if pis_node is not None:
                        for child in pis_node:
                            cst_pis = child.findtext('nfe:CST', default='', namespaces=ns) or child.findtext('CST', default='')
                            if cst_pis:
                                break

                dados_produto = {
                    "x_prod": x_prod,
                    "ncm": ncm,
                    "cfop": cfop,
                    "cst_pis": cst_pis
                }

                alertas = validar_regras_fiscais_por_regime(dados_produto, regime_tributario)
                
                if alertas:
                    relatorio_xml.append({
                        "produto": dados_produto,
                        "alertas": alertas
                    })
                    
        return relatorio_xml
    except Exception as e:
        print(f"Erro ao processar XML {caminho_xml}: {e}")
        return []


def executar_auditoria(pasta_xmls, regime_tributario="Lucro Presumido"):
    """Varre a pasta de XMLs de entrada e aplica a auditoria no regime selecionado."""
    relatorio_geral = []
    
    if not os.path.exists(pasta_xmls):
        return relatorio_geral
        
    for arquivo in os.listdir(pasta_xmls):
        if arquivo.endswith(".xml"):
            caminho_completo = os.path.join(pasta_xmls, arquivo)
            resultado = processar_xml_nfe(caminho_completo, regime_tributario)
            relatorio_geral.extend(resultado)
            
    return relatorio_geral
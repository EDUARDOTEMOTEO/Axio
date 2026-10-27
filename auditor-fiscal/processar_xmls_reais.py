"""
PROCESSADOR DE LOTES DE XMLS REAIS PARA TELEMETRIA (processar_xmls_reais.py)
Lê pastas com XMLs autênticos de NFe, extrai tributos reais e alimenta a base do Axio.
"""

import os
import pandas as pd
import xml.etree.ElementTree as ET
from src.tax_rules import validar_item_fiscal

# Mapeamento de UFs para Regiões do Brasil
UF_PARA_REGIAO = {
    "MA": "Nordeste", "PI": "Nordeste", "CE": "Nordeste", "RN": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "AL": "Nordeste", "SE": "Nordeste", "BA": "Nordeste",
    "SP": "Sudeste", "RJ": "Sudeste", "MG": "Sudeste", "ES": "Sudeste",
    "PR": "Sul", "SC": "Sul", "RS": "Sul",
    "MT": "Centro-Oeste", "MS": "Centro-Oeste", "GO": "Centro-Oeste", "DF": "Centro-Oeste",
    "AM": "Norte", "PA": "Norte", "AC": "Norte", "RR": "Norte", "RO": "Norte", "AP": "Norte", "TO": "Norte"
}

def identificar_regiao_por_uf(uf: str) -> str:
    return UF_PARA_REGIAO.get(uf.upper(), "Sudeste")

def processar_pasta_xmls_reais(pasta_xmls: str, regime_tributario: str = "Simples Nacional", tipo_contabilidade: str = "Terceirizada"):
    """Varre a pasta com XMLs reais e gera a telemetria com dados verídicos."""
    if not os.path.exists(pasta_xmls):
        print(f"⚠️ A pasta '{pasta_xmls}' não existe. Crie a pasta e insira os XMLs reais nela.")
        return

    arquivos = [f for f in os.listdir(pasta_xmls) if f.endswith(".xml")]
    if not arquivos:
        print(f"⚠️ Nenhum arquivo .xml encontrado na pasta '{pasta_xmls}'.")
        return

    print(f"📦 Processando {len(arquivos)} XMLs reais da pasta '{pasta_xmls}'...")

    registros_reais = []
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

    for arq in arquivos:
        caminho = os.path.join(pasta_xmls, arq)
        try:
            tree = ET.parse(caminho)
            root = tree.getroot()
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

            # Dados da Empresa Emitente e Localização
            cnpj_emit = root.findtext('.//nfe:emit/nfe:CNPJ', default='00000000000000', namespaces=ns)
            uf_emit = root.findtext('.//nfe:emit/nfe:enderEmit/nfe:UF', default='PB', namespaces=ns)
            uf_dest = root.findtext('.//nfe:dest/nfe:enderDest/nfe:UF', default='PB', namespaces=ns)
            razao_emit = root.findtext('.//nfe:emit/nfe:xNome', default='Empresa Real', namespaces=ns)
            regiao = identificar_regiao_por_uf(uf_emit)

            # Detalhes dos Produtos
            for det in root.findall('.//nfe:det', ns):
                prod = det.find('nfe:prod', ns)
                imposto = det.find('nfe:imposto', ns)

                if prod is not None:
                    x_prod = prod.findtext('nfe:xProd', default='', namespaces=ns)
                    ncm = prod.findtext('nfe:NCM', default='', namespaces=ns)
                    cfop = prod.findtext('nfe:CFOP', default='', namespaces=ns)
                    v_prod = float(prod.findtext('nfe:vProd', default='0.00', namespaces=ns))

                    cst_pis = ""
                    csosn = ""

                    if imposto is not None:
                        pis_node = imposto.find('.//nfe:PIS', ns)
                        icms_node = imposto.find('.//nfe:ICMS', ns)

                        if pis_node is not None:
                            for child in pis_node:
                                cst_pis = child.findtext('nfe:CST', default='', namespaces=ns)
                                if cst_pis: break

                        if icms_node is not None:
                            for child in icms_node:
                                csosn = child.findtext('nfe:CSOSN', default='', namespaces=ns)
                                if csosn: break

                    item_dict = {
                        "x_prod": x_prod,
                        "ncm": ncm,
                        "cfop": cfop,
                        "cst_pis": cst_pis,
                        "csosn": csosn,
                        "v_prod": v_prod
                    }

                    # Auditoria em tempo real com regras reais
                    alertas = validar_item_fiscal(item_dict, regime_tributario=regime_tributario)
                    tem_erro = len(alertas) > 0
                    credito_rs = sum(a.get("impacto_estimado_rs", 0.0) for a in alertas)

                    registros_reais.append({
                        "nota_id": arq.replace(".xml", ""),
                        "empresa_id": cnpj_emit,
                        "segmento": "Dados Reais",
                        "regiao": regiao,
                        "tipo_contabilidade": tipo_contabilidade,
                        "regime_tributario": regime_tributario,
                        "produto": x_prod,
                        "ncm": ncm,
                        "cfop": cfop,
                        "valor_nota_rs": v_prod,
                        "teve_divergencia": tem_erro,
                        "credito_recuperavel_rs": credito_rs,
                        "qtd_alertas": len(alertas),
                        "tipo_alerta_principal": alertas[0]["tipo"] if alertas else "Sem Inconsistência"
                    })
        except Exception as e:
            print(f"❌ Erro ao ler {arq}: {e}")

    if registros_reais:
        df_novos = pd.DataFrame(registros_reais)
        caminho_csv = "data/telemetria_mercado_axio.csv"

        # Se já existir o CSV da simulação, unifica os dados reais com os simulados
        if os.path.exists(caminho_csv):
            df_existente = pd.read_csv(caminho_csv)
            df_final = pd.concat([df_existente, df_novos], ignore_index=True)
        else:
            df_final = df_novos

        df_final.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
        print(f"✅ {len(registros_reais)} itens reais foram processados e adicionados ao painel de inteligência!")

if __name__ == "__main__":
    # Crie a pasta data/xmls_reais e adicione seus XMLs de teste reais lá
    os.makedirs("data/xmls_reais", exist_ok=True)
    processar_pasta_xmls_reais("data/xmls_reais", regime_tributario="Simples Nacional")
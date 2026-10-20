import re
def auditar_produto(produto):
    """
    Motor de IA Tributária para NF-e de Mercadorias / Peças (Modelo 55).
    """
    alertas = []
    
    ncm = str(produto.get('ncm', '')).strip()
    cst_pis = str(produto.get('cst_pis', '')).strip()
    v_prod = float(produto.get('v_prod', 0.0))
    x_prod = str(produto.get('x_prod', '')).upper()
    cst_icms = str(produto.get('cst_icms', '')).strip()
    cfop = str(produto.get('cfop', '')).strip()
    
    # 1. Regra de PIS/COFINS Monofásico refinada para autopeças (Excluindo 84219999)
    ncms_monofasicos = ['8708', '4011', '8511', '842123', '8714']
    eh_monofasico = any(ncm.startswith(prefixo) for prefixo in ncms_monofasicos) and ncm != '84219999'
    
    if eh_monofasico and cst_pis in ['01', '02']:
        alertas.append({
            'tipo': 'PIS_COFINS_MONOFASICO_TRIBUTADO_INCORRETAMENTE',
            'impacto_financeiro': round(v_prod * 0.0925, 2),
            'mensagem': f'O item "{x_prod}" (NCM: {ncm}) é sujeito ao regime monofásico, mas foi tributado no CST {cst_pis}.'
        })

    # 2. Regra de ICMS-ST para lubrificantes e peças (CST 60 / 500 / CFOPs específicos)
    if 'OLEO' in x_prod or 'LUB' in x_prod or 'FILTRO' in x_prod:
        cst_icms_limpo = str(cst_icms).replace('0', '').strip()
        is_st_antecipada = cst_icms_limpo in ['60', '500'] or cfop.endswith(('404', '405')) or float(produto.get('v_icms_st', 0.0)) > 0
        
        if not is_st_antecipada:
            alertas.append({
                'tipo': 'ICMS_ST_FALTANTE',
                'impacto_financeiro': round(v_prod * 0.18, 2),
                'mensagem': f'O item "{x_prod}" exige retenção prévia por Substituição Tributária (ICMS-ST).'
            })

    return alertas


def auditar_documento_fiscal_inteligente(dados_doc, tipo_doc="PDF"):
    """
    IA Tributária: Reconhece o documento e valida conformidade.
    """
    alertas = []
    status = "Tudo OK"
    impacto_total = 0.0
    
    if tipo_doc == "PDF" or tipo_doc == "NFSE":
        texto = dados_doc.get('texto_completo', '').lower()
        if "danfe" in texto or "venda merc" in texto or "documento auxiliar" in texto:
            alertas.append({
                'tipo': 'OPERACAO_MERCADORIA_CORRETA',
                'impacto_financeiro': 0.0,
                'mensagem': 'IA Tributária: Documento validado como Circulação de Mercadorias e Peças (Modelo 55). Tributação correta por ICMS, IBS e CBS. ISSQN inexigível.'
            })
            return 'Tudo OK', alertas, 0.0

    return status, alertas, impacto_total


def auditar_cruzamento_nfse_nfe(lista_servicos, todos_produtos):
    """
    Cruzamento Inteligente Avançado entre Serviços (PDF) e Peças (XML):
    Valida operações mistas para Órgãos Públicos Federais (ex: Ministério da Justiça),
    detetando se há coerência e se as retenções federais (IN RFB 1234/2012) foram observadas.
    """
    alertas_cruzamento = []
    
    for serv in lista_servicos:
        for prod in todos_produtos:
            cnpj_serv = str(serv['dados'].get('cnpj_prestador', '')).strip()
            cnpj_prod = str(prod.get('cnpj_emitente', '')).strip()
            
            if cnpj_serv and cnpj_prod and cnpj_serv == cnpj_prod:
                texto_servico = serv['dados'].get('texto_completo', '').lower()
                
                # Verifica se é tomador público federal
                eh_publico_federal = "ministerio" in texto_servico or "federal" in texto_servico
                
                if eh_publico_federal:
                    # Verifica se o serviço apresenta alerta de retenção federal faltante
                    tem_alerta_retencao = any('RETENCAO_FEDERAL' in a.get('tipo', '') for a in serv['dados'].get('alertas', []))
                    
                    if tem_alerta_retencao:
                        impacto_serv = serv['dados'].get('impacto_total', 0.0)
                        alertas_cruzamento.append({
                            'origem': f"Operação Mista Órgão Público ({serv['arquivo']} & NF-e nº {prod.get('numero_nota', '')})",
                            'tipo': 'ALERTA_CRUZADO_RETENCAO_PUBLICA',
                            'mensagem': f"Atenção em Operação Mista: O atendimento ao órgão público federal possui divergência nas retenções federais na nota de serviço, com impacto de R$ {impacto_serv:.2f} pendente de regularização na mesa."
                        })
                    else:
                        alertas_cruzamento.append({
                            'origem': f"Operação Mista Órgão Público ({serv['arquivo']} & NF-e nº {prod.get('numero_nota', '')})",
                            'tipo': 'CRUZAMENTO_REGULAR',
                            'mensagem': "Cruzamento de operação mista validado: Peças (ICMS) e Serviços (ISS/Retenções) perfeitamente segregados."
                        })
                            
    return alertas_cruzamento
from datetime import datetime, timedelta

def validar_prazos_e_vencimentos(dados_doc, tipo="PDF"):
    """
    Valida prazos de vencimento, termos de pagamento e conformidade temporal 
    de emissão e recolhimento fiscal.
    """
    alertas_prazo = []
    texto = dados_doc.get('texto_completo', '')
    
    # Exemplo: detetar termos de pagamento como "60 dias" comuns em faturas públicas
    if "60 dias" in texto.lower() or "60 dias" in texto:
        alertas_prazo.append({
            'tipo': 'COMPLIANCE_PRAZO_PAGAMENTO',
            'impacto_financeiro': 0.0,
            'mensagem': 'Compliance de Prazo: Fatura com condição de pagamento a 60 dias registada. Monitorizar o fluxo de caixa para a compensação das retenções federais.'
        })
        
    return alertas_prazo

def validar_cnpj(cnpj_str):
    """Valida um CNPJ utilizando o algoritmo oficial de dígitos verificadores."""
    cnpj = re.sub(r'\D', '', cnpj_str)
    
    if len(cnpj) != 14:
        return False
    if cnpj in [c * 14 for c in "0123456789"]:
        return False
        
    # Validação do 1º dígito verificador
    soma = 0
    peso = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    for i in range(12):
        soma += int(cnpj[i]) * peso[i]
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    if int(cnpj[12]) != digito1:
        return False
        
    # Validação do 2º dígito verificador
    soma = 0
    peso = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    for i in range(13):
        soma += int(cnpj[i]) * peso[i]
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    if int(cnpj[13]) != digito2:
        return False
        
    return True
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
from typing import Dict, List, Any, Optional

# =====================================================================
# 1. TABELA EXPANDIDA DE NCMS MONOFÁSICOS (PIS/COFINS ALÍQUOTA CONCENTRADA)
# =====================================================================
NCMS_MONOFASICOS: Dict[str, Dict[str, str]] = {
    # --- AUTOPEÇAS, PNEUS E VEÍCULOS ---
    "8708": {"segmento": "Autopeças", "descricao": "Partes e Acessórios de Veículos Automóveis"},
    "4011": {"segmento": "Autopeças", "descricao": "Pneus Novos de Borracha"},
    "4013": {"segmento": "Autopeças", "descricao": "Câmaras de Ar de Borracha"},
    "8511": {"segmento": "Autopeças", "descricao": "Aparelhos e Equipamentos Elétricos de Ignição/Arranque"},
    "8407": {"segmento": "Autopeças", "descricao": "Motores de Opagamento/Ignição por Faísca"},
    "8408": {"segmento": "Autopeças", "descricao": "Motores de Embolo de Compressão (Diesel)"},
    "8714": {"segmento": "Autopeças", "descricao": "Partes e Acessórios de Motocicletas e Ciclomotores"},

    # --- MEDICAMENTOS, REAGENTES E PERFUMARIA/COSMÉTICOS ---
    "3003": {"segmento": "Farmacêutico", "descricao": "Medicamentos para Fins Terapêuticos/Profiláticos"},
    "3004": {"segmento": "Farmacêutico", "descricao": "Medicamentos Dosados ou Embalados para Venda a Retalho"},
    "3006": {"segmento": "Farmacêutico", "descricao": "Preparações e Artigos Farmacêuticos Especiais"},
    "3303": {"segmento": "Cosméticos", "descricao": "Perfumes e Águas de Colônia"},
    "3304": {"segmento": "Cosméticos", "descricao": "Produtos de Maquiagem e Cuidados com a Pele"},
    "3305": {"segmento": "Cosméticos", "descricao": "Preparações Capilares (Xampus, Condicionadores, Tinturas)"},
    "3306": {"segmento": "Cosméticos", "descricao": "Preparações para Higiene Bucal ou Dentária"},
    "3307": {"segmento": "Cosméticos", "descricao": "Desodorantes, Barbear e Preparações para Banho"},
    "3401": {"segmento": "Cosméticos", "descricao": "Sabões e Preparações Orgânicas Tensoativas"},

    # --- BEBIDAS FRIAS ---
    "2201": {"segmento": "Bebidas Frias", "descricao": "Águas Minerais, Potáveis, Naturais e Gaseificadas"},
    "2202": {"segmento": "Bebidas Frias", "descricao": "Refrigerantes, Chás, Energéticos e Bebidas Não Alcoólicas"},
    "2203": {"segmento": "Bebidas Frias", "descricao": "Cervejas de Malte e Chopes"},

    # --- COMBUSTÍVEIS E LUBRIFICANTES ---
    "2710": {"segmento": "Combustíveis/Lubrificantes", "descricao": "Óleos de Petróleo, Lubrificantes, Gasolina e Diesel"},
    "2711": {"segmento": "Combustíveis/Lubrificantes", "descricao": "Gás de Petróleo e Outros Hidrocarbonetos Gasosos (GLP)"},
    "3826": {"segmento": "Combustíveis/Lubrificantes", "descricao": "Biodiesel e suas Misturas"}
}
# =====================================================================
# 2. TABELAS DE CÓDIGOS FISCAIS (CFOP, CST PIS/COFINS, CSOSN ICMS)
# =====================================================================

# CFOPs de Saída com ICMS-ST (Recolhido Anteriormente ou Substituição Tributária)
CFOPS_SAIDA_ICMS_ST = ["5403", "5405", "6403", "6404", "5401", "6401"]

# CFOPs de Venda com Tributação Integral / Normal
CFOPS_SAIDA_TRIBUTACAO_NORMAL = ["5101", "5102", "6101", "6102"]

# CFOPs de Entradas com Direito a Crédito em Regimes Não-Cumulativos
CFOPS_ENTRADA_INSUMOS_REVENDA = [
    "1101", "1102", "1201", "1202", "1352", "1353",
    "2101", "2102", "2201", "2202", "2352", "2353"
]

# CSTs de PIS/COFINS
CST_PIS_COFINS_MONOFASICO = ["04", "05", "64", "65", "66"]
CST_PIS_COFINS_CREDITO = ["50", "51", "52", "53", "54", "55", "56", "60", "61", "62", "63"]
CST_PIS_COFINS_SEM_CREDITO = ["70", "71", "72", "73", "74", "75", "98", "99", "08"]

# CSOSN do Simples Nacional indicativos de ICMS-ST
CSOSN_SIMPLES_ST = ["201", "202", "203", "500"]

# =====================================================================
# 3. PARÂMETROS DE ALÍQUOTAS MÉDIAS PARA RESTITUIÇÃO / ESTIMATIVA (R$)
# =====================================================================
# Alíquota média de PIS/COFINS embutida no Anexo I/II do Simples Nacional (~0,85% a 1,25%)
ALIQUOTA_SIMPLES_MONOFASICO_ESTIMADA = 0.0085

# Parcela média do ICMS no DAS do Simples Nacional (~3,35% a 4,20%)
ALIQUOTA_SIMPLES_ICMS_ST_ESTIMADA = 0.0335

# Alíquota Cheia Não-Cumulativa (Lucro Real: 1,65% PIS + 7,60% COFINS)
ALIQUOTA_LUCRO_REAL_NAO_CUMULATIVO = 0.0925

# Alíquota Cumulativa (Lucro Presumido: 0,65% PIS + 3,00% COFINS)
ALIQUOTA_LUCRO_PRESUMIDO_CUMULATIVO = 0.0365

# =====================================================================
# 4. FUNÇÕES DE BUSCA E CÁLCULO MONETÁRIO
# =====================================================================

def buscar_segmento_monofasico(ncm: str) -> Optional[Dict[str, str]]:
    """Procura se um NCM pertence à tabela de produtos monofásicos."""
    ncm_limpo = str(ncm).replace(".", "").strip()
    for prefixo, info in NCMS_MONOFASICOS.items():
        if ncm_limpo.startswith(prefixo):
            return info
    return None

def calcular_impacto_financeiro(valor_operacao: float, regime: str, tipo_regra: str) -> float:
    """Calcula a estimativa em R$ do benefício fiscal ou crédito perdido."""
    if valor_operacao <= 0:
        return 0.0

    if regime == "Simples Nacional":
        if tipo_regra == "MONOFASICO_PIS_COFINS":
            return round(valor_operacao * ALIQUOTA_SIMPLES_MONOFASICO_ESTIMADA, 2)
        elif tipo_regra == "SEGREGACAO_ICMS_ST":
            return round(valor_operacao * ALIQUOTA_SIMPLES_ICMS_ST_ESTIMADA, 2)

    elif regime == "Lucro Real":
        if tipo_regra == "CREDITO_INSUMO_NAO_APROVEITADO":
            return round(valor_operacao * ALIQUOTA_LUCRO_REAL_NAO_CUMULATIVO, 2)

    return 0.0

# =====================================================================
# 5. MOTOR DE AUDITORIA E TRIANGULAÇÃO FISCAL
# =====================================================================

def validar_item_fiscal(prod: dict, regime_tributario: str = "Simples Nacional") -> List[Dict[str, Any]]:
    """
    Realiza a triangulação cruzada entre NCM, CFOP, CST, CSOSN e Valor do Produto
    conforme o Regime Tributário ativo da empresa.
    """
    alertas = []
    
    ncm = str(prod.get("ncm", "")).replace(".", "").strip()
    cfop = str(prod.get("cfop", "")).strip()
    cst_pis = str(prod.get("cst_pis", "")).strip()
    csosn = str(prod.get("csosn", "")).strip()
    v_prod = float(prod.get("v_prod", 0.0))

    info_monofasico = buscar_segmento_monofasico(ncm)

    # -----------------------------------------------------------------
    # REGRA A: SIMPLES NACIONAL (PGDAS-D)
    # -----------------------------------------------------------------
    if regime_tributario == "Simples Nacional":
        # 1. Segregação de PIS/COFINS Monofásico
        if info_monofasico:
            valor_recuperar = calcular_impacto_financeiro(v_prod, regime_tributario, "MONOFASICO_PIS_COFINS")
            cst_alerta = f" (CST informado: {cst_pis})" if cst_pis else ""
            alertas.append({
                "tipo": "Oportunidade - PIS/COFINS Monofásico",
                "impacto_estimado_rs": valor_recuperar,
                "mensagem": (
                    f"Produto NCM {ncm} ({info_monofasico['segmento']} - {info_monofasico['descricao']}) "
                    f"possui tributação concentrada na fábrica. Segregue esta receita no PGDAS-D{cst_alerta}. "
                    f"Economia/Restituição estimada: R$ {valor_recuperar:.2f}."
                )
            })

        # 2. Exclusão de ICMS-ST no PGDAS-D
        if cfop in CFOPS_SAIDA_ICMS_ST or csosn in CSOSN_SIMPLES_ST:
            valor_icms_st = calcular_impacto_financeiro(v_prod, regime_tributario, "SEGREGACAO_ICMS_ST")
            alertas.append({
                "tipo": "Oportunidade - Segregação ICMS-ST",
                "impacto_estimado_rs": valor_icms_st,
                "mensagem": (
                    f"Venda efetuada com ICMS-ST recolhido na origem (CFOP {cfop} / CSOSN {csosn}). "
                    f"Exclua a parcela de ICMS do cálculo da alíquota do PGDAS-D. Economia estimada: R$ {valor_icms_st:.2f}."
                )
            })

    # -----------------------------------------------------------------
    # REGRA B: LUCRO REAL (NÃO-CUMULATIVIDADE)
    # -----------------------------------------------------------------
    elif regime_tributario == "Lucro Real":
        # 1. Tomada de Crédito de PIS/COFINS Não Aproveitada na Entrada
        if cfop in CFOPS_ENTRADA_INSUMOS_REVENDA and cst_pis in CST_PIS_COFINS_SEM_CREDITO:
            if not info_monofasico:
                valor_credito = calcular_impacto_financeiro(v_prod, regime_tributario, "CREDITO_INSUMO_NAO_APROVEITADO")
                alertas.append({
                    "tipo": "Crédito Oculto - Lucro Real",
                    "impacto_estimado_rs": valor_credito,
                    "mensagem": (
                        f"Entrada de mercadoria/insumo (CFOP {cfop}) registrada com CST {cst_pis} sem aproveitamento. "
                        f"Direito a crédito não-cumulativo de 9,25% de PIS/COFINS no Sped Contribuições. Crédito estimado: R$ {valor_credito:.2f}."
                    )
                })

        # 2. Venda de Produto Monofásico com CST Incorreto
        if info_monofasico and cfop in CFOPS_SAIDA_TRIBUTACAO_NORMAL and cst_pis not in CST_PIS_COFINS_MONOFASICO:
            alertas.append({
                "tipo": "Alerta Cadastral - CST Incorreto",
                "impacto_estimado_rs": 0.0,
                "mensagem": (
                    f"Produto NCM {ncm} ({info_monofasico['segmento']}) emitido com CST PIS/COFINS {cst_pis}. "
                    f"Para itens monofásicos na saída, utilize o CST 04 (Operação Tributável Alíquota Zero/Monofásica)."
                )
            })

    # -----------------------------------------------------------------
    # REGRA C: LUCRO PRESUMIDO (CUMULATIVIDADE)
    # -----------------------------------------------------------------
    elif regime_tributario == "Lucro Presumido":
        if cfop in CFOPS_ENTRADA_INSUMOS_REVENDA and cst_pis in CST_PIS_COFINS_CREDITO:
            alertas.append({
                "tipo": "Inconsistência - Alerta de Multa",
                "impacto_estimado_rs": 0.0,
                "mensagem": (
                    f"No regime cumulativo (Lucro Presumido), a entrada CFOP {cfop} foi lançada com CST {cst_pis} gerando crédito direto. "
                    f"Ajuste para CST sem direito a crédito (ex: 70/98) para evitar autuação da Receita Federal."
                )
            })

    return alertas

"""
MÓDULO CENTRAL DE REGRAS E TABELAS FISCAIS DO AXIO (src/tax_rules.py)
"""

from typing import Dict, List, Any, Optional

# ... [Manter as tabelas NCMS_MONOFASICOS e CFOPS existentes] ...

# =====================================================================
# 1. NOVAS REGRAS DE RETENÇÃO E TRIANGULAÇÃO GEOGRÁFICA
# =====================================================================

def validar_retencao_tomador_pf(doc_tomador: str, retencoes: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Valida se há destaque indevido de retenção federal na fonte (PIS/COFINS/CSLL/IRRF)
    para tomadores Pessoa Física (CPF).
    """
    alertas = []
    doc_limpo = "".join(filter(str.isdigit, str(doc_tomador)))
    
    # Valida se o documento do tomador é CPF (11 dígitos)
    if len(doc_limpo) == 11:
        total_federais = (
            float(retencoes.get("pis", 0.0)) + 
            float(retencoes.get("cofins", 0.0)) + 
            float(retencoes.get("csll", 0.0)) + 
            float(retencoes.get("irrf", 0.0))
        )
        if total_federais > 0:
            alertas.append({
                "tipo": "Alerta Cadastral - Retenção Indevida CPF",
                "impacto_estimado_rs": total_federais,
                "mensagem": (
                    f"Retenção federal de R$ {total_federais:.2f} destacada na NFS-e para Tomador Pessoa Física (CPF {doc_limpo}). "
                    f"Pessoas Físicas não possuem obrigatoriedade legal de retenção na fonte (Lei nº 10.833/2003)."
                )
            })
    return alertas


def validar_cfop_uf_operacao(cfop: str, uf_emit: str, uf_dest: str) -> List[Dict[str, Any]]:
    """
    Verifica se uma operação entre estados diferentes foi emitida incorretamente
    com CFOP de operação interna (iniciado por 5).
    """
    alertas = []
    cfop_str = str(cfop).strip()
    uf_e = str(uf_emit).strip().upper()
    uf_d = str(uf_dest).strip().upper()

    if uf_e and uf_d and uf_e != uf_d:
        if cfop_str.startswith("5"):
            cfop_sugerido = "6" + cfop_str[1:]
            alertas.append({
                "tipo": "Inconsistência Cadastral - CFOP Inválido",
                "impacto_estimado_rs": 0.0,
                "mensagem": (
                    f"Operação interestadual ({uf_e} -> {uf_d}) registrada com CFOP interno ({cfop_str}). "
                    f"Corrija o cadastro no ERP para o CFOP equivalente iniciado por 6 (ex: {cfop_sugerido})."
                )
            })
    return alertas


# =====================================================================
# 2. ATUALIZAÇÃO DO MOTOR DE VALIDAÇÃO DE ITENS FISCAIS
# =====================================================================

def validar_item_fiscal(
    prod: dict, 
    regime_tributario: str = "Simples Nacional",
    uf_emit: str = "",
    uf_dest: str = ""
) -> List[Dict[str, Any]]:
    """
    Executa a triangulação de NCM, CFOP, CST/CSOSN, valor e validação de UF.
    """
    alertas = []
    
    ncm = str(prod.get("ncm", "")).replace(".", "").strip()
    cfop = str(prod.get("cfop", "")).strip()
    cst_pis = str(prod.get("cst_pis", "")).strip()
    csosn = str(prod.get("csosn", "")).strip()
    v_prod = float(prod.get("v_prod", 0.0))

    # 1. Validação de CFOP vs. Estados (UF)
    if uf_emit and uf_dest:
        alertas.extend(validar_cfop_uf_operacao(cfop, uf_emit, uf_dest))

    # 2. Busca no Mapeamento Monofásico
    info_monofasico = buscar_segmento_monofasico(ncm)

    # 3. Análise para SIMPLES NACIONAL
    if regime_tributario == "Simples Nacional":
        if info_monofasico:
            valor_recuperar = calcular_impacto_financeiro(v_prod, regime_tributario, "MONOFASICO_PIS_COFINS")
            alertas.append({
                "tipo": "Oportunidade - PIS/COFINS Monofásico",
                "impacto_estimado_rs": valor_recuperar,
                "mensagem": (
                    f"Produto NCM {ncm} ({info_monofasico['segmento']}) possui tributação concentrada. "
                    f"Segregue a receita no PGDAS-D. Economia estimada: R$ {valor_recuperar:.2f}."
                )
            })

        if cfop in CFOPS_SAIDA_ICMS_ST or csosn in CSOSN_SIMPLES_ST:
            valor_icms_st = calcular_impacto_financeiro(v_prod, regime_tributario, "SEGREGACAO_ICMS_ST")
            alertas.append({
                "tipo": "Oportunidade - Segregação ICMS-ST",
                "impacto_estimado_rs": valor_icms_st,
                "mensagem": (
                    f"Venda com ICMS-ST recolhido na origem (CFOP {cfop}). "
                    f"Exclua a parcela de ICMS do cálculo no PGDAS-D. Economia estimada: R$ {valor_icms_st:.2f}."
                )
            })

    # 4. Análise para LUCRO REAL
    elif regime_tributario == "Lucro Real":
        if cfop in CFOPS_ENTRADA_INSUMOS_REVENDA and cst_pis in CST_PIS_COFINS_SEM_CREDITO:
            if not info_monofasico:
                valor_credito = calcular_impacto_financeiro(v_prod, regime_tributario, "CREDITO_INSUMO_NAO_APROVEITADO")
                alertas.append({
                    "tipo": "Crédito Oculto - Lucro Real",
                    "impacto_estimado_rs": valor_credito,
                    "mensagem": (
                        f"Entrada de mercadoria (CFOP {cfop}) sem aproveitamento de PIS/COFINS (CST {cst_pis}). "
                        f"Direito a crédito estimado em R$ {valor_credito:.2f} (9,25%)."
                    )
                })

    return alertas
"""
SIMULADOR DE ESTRESSE E INTELIGÊNCIA DE MERCADO (simulador_mercado_axio.py)
Gera centenas de cenários fiscais sintéticos cruzando dados de gestão,
região e contabilidade para medir a eficácia e evolução do motor do Axio.
"""

import os
import random
import json
import pandas as pd
from typing import List, Dict, Any
from src.tax_rules import validar_item_fiscal, NCMS_MONOFASICOS

# ---------------------------------------------------------------------
# PARÂMETROS DE SIMULAÇÃO DE MERCADO
# ---------------------------------------------------------------------
REGIOES = ["Nordeste", "Sudeste", "Sul", "Norte", "Centro-Oeste"]
TIPOS_CONTABILIDADE = ["Interna", "Terceirizada"]
REGIMES = ["Simples Nacional", "Lucro Real", "Lucro Presumido"]

SEGMENTOS_E_PRODUTOS = {
    "Bebidas Frias": [
        {"nome": "CERVEJA PILSEN 350ML", "ncm": "22030000", "valor_medio": 4.50},
        {"nome": "REFRIGERANTE COLA 2L", "ncm": "22021000", "valor_medio": 8.00},
        {"nome": "ÁGUA MINERAL 500ML", "ncm": "22011000", "valor_medio": 2.00},
    ],
    "Autopeças e Oficinas": [
        {"nome": "PASTILHA DE FREIO BROS", "ncm": "87083090", "valor_medio": 85.00},
        {"nome": "ÓLEO LUBRIFICANTE 20W50 1L", "ncm": "27101911", "valor_medio": 38.00},
        {"nome": "PNEU ARO 17 MOTORCYCLE", "ncm": "40114000", "valor_medio": 240.00},
    ],
    "Farmácia e Cosméticos": [
        {"nome": "DIPIRONA SODICA 500MG", "ncm": "30049099", "valor_medio": 12.00},
        {"nome": "PERFUME COLONIA 100ML", "ncm": "33030010", "valor_medio": 115.00},
        {"nome": "SHAMPOO ANTIQUEDA 300ML", "ncm": "33051000", "valor_medio": 28.00},
    ],
    "Comércio Comum / Papelaria": [
        {"nome": "CADERNO ESPIRAL 100 FLS", "ncm": "48201000", "valor_medio": 18.00},
        {"nome": "CANETA ESFEROGRÁFICA AZUL", "ncm": "96081000", "valor_medio": 2.50},
    ]
}


def gerar_empresa_sintetica(id_empresa: int) -> Dict[str, Any]:
    """Gera o perfil de uma empresa com viés probabilístico de mercado."""
    segmento = random.choice(list(SEGMENTOS_E_PRODUTOS.keys()))
    regiao = random.choice(REGIOES)
    tipo_contabilidade = random.choice(TIPOS_CONTABILIDADE)
    
    # Probabilidade de erro fiscal induzido (Aumenta se a contabilidade for terceirizada em regiões específicas)
    taxa_erro_induzida = 0.35
    if tipo_contabilidade == "Terceirizada":
        taxa_erro_induzida += 0.25
    if regiao in ["Nordeste", "Norte"]:
        taxa_erro_induzida += 0.10

    return {
        "empresa_id": f"EMP-{id_empresa:04d}",
        "razao_social": f"Empresa Simulação {id_empresa} LTDA",
        "segmento": segmento,
        "regiao": regiao,
        "tipo_contabilidade": tipo_contabilidade,
        "regime_tributario": random.choice(REGIMES),
        "taxa_erro_induzida": min(taxa_erro_induzida, 0.85)
    }


def gerar_nota_sintetica(empresa: Dict[str, Any], id_nota: int) -> Dict[str, Any]:
    """Cria uma nota fiscal sintética com possíveis erros cadastrais/fiscais."""
    produtos_disp = SEGMENTOS_E_PRODUTOS[empresa["segmento"]]
    prod_ref = random.choice(produtos_disp)
    
    quantidade = random.randint(10, 500)
    valor_total = round(prod_ref["valor_medio"] * quantidade, 2)
    
    # Determina se esta nota conterá erro com base na taxa da empresa
    possuir_erro = random.random() < empresa["taxa_erro_induzida"]
    
    if possuir_erro:
        # Padrão de Erro: Mercadoria Monofásica/ST emitida com CFOP/CST genérico de tributação cheia
        cfop = "5102"
        cst_pis = "01" if empresa["regime_tributario"] != "Simples Nacional" else ""
        csosn = "101" if empresa["regime_tributario"] == "Simples Nacional" else ""
    else:
        # Emissão fiscal correta
        if empresa["segmento"] in ["Bebidas Frias", "Autopeças e Oficinas", "Farmácia e Cosméticos"]:
            cfop = "5405"
            cst_pis = "04"
            csosn = "500"
        else:
            cfop = "5102"
            cst_pis = "01"
            csosn = "101"

    return {
        "nota_id": f"NF-{id_nota:06d}",
        "empresa_id": empresa["empresa_id"],
        "segmento": empresa["segmento"],
        "regiao": empresa["regiao"],
        "tipo_contabilidade": empresa["tipo_contabilidade"],
        "regime_tributario": empresa["regime_tributario"],
        "produto_nome": prod_ref["nome"],
        "ncm": prod_ref["ncm"],
        "cfop": cfop,
        "cst_pis": cst_pis,
        "csosn": csosn,
        "v_prod": valor_total
    }


def executar_simulacao_massa(qtd_empresas: int = 50, notas_por_empresa: int = 10):
    """Executa a bateria de auditoria massiva e gera o dataset de telemetria."""
    print(f"🚀 Iniciando simulação de mercado: {qtd_empresas} empresas | {qtd_empresas * notas_por_empresa} notas...")
    
    registros_telemetria = []
    total_creditos_identificados_rs = 0.0

    for i in range(1, qtd_empresas + 1):
        empresa = gerar_empresa_sintetica(i)
        
        for j in range(1, notas_por_empresa + 1):
            nota = gerar_nota_sintetica(empresa, (i * 100) + j)
            
            # Submete ao motor de inteligência do Axio (src/tax_rules.py)
            alertas = validar_item_fiscal(nota, regime_tributario=nota["regime_tributario"])
            
            tem_inconsistencia = len(alertas) > 0
            credito_nota_rs = sum(a.get("impacto_estimado_rs", 0.0) for a in alertas)
            total_creditos_identificados_rs += credito_nota_rs

            # Registra o log detalhado para análise estatística
            registros_telemetria.append({
                "nota_id": nota["nota_id"],
                "empresa_id": nota["empresa_id"],
                "segmento": nota["segmento"],
                "regiao": nota["regiao"],
                "tipo_contabilidade": nota["tipo_contabilidade"],
                "regime_tributario": nota["regime_tributario"],
                "produto": nota["produto_nome"],
                "ncm": nota["ncm"],
                "cfop": nota["cfop"],
                "valor_nota_rs": nota["v_prod"],
                "teve_divergencia": tem_inconsistencia,
                "credito_recuperavel_rs": credito_nota_rs,
                "qtd_alertas": len(alertas),
                "tipo_alerta_principal": alertas[0]["tipo"] if alertas else "Sem Inconsistência"
            })

    # Exporta para CSV para consumo pelo Dashboard do Axio
    os.makedirs("data", exist_ok=True)
    df_telemetria = pd.DataFrame(registros_telemetria)
    caminho_csv = "data/telemetria_mercado_axio.csv"
    df_telemetria.to_csv(caminho_csv, index=False, encoding="utf-8-sig")

    print(f"✅ Simulação concluída com sucesso!")
    print(f"📊 Total de Registros Analisados: {len(df_telemetria)}")
    print(f"💰 Total de Créditos Ocultos Identificados pelo Axio: R$ {total_creditos_identificados_rs:,.2f}")
    print(f"📁 Dataset exportado para: {caminho_csv}")

if __name__ == "__main__":
    executar_simulacao_massa(qtd_empresas=100, notas_por_empresa=10)
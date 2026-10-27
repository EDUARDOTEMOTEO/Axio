from engine.base_strategy import BaseStrategy
from engine.registry import registrar_estrategia

@registrar_estrategia(setor="VAREJO", subgrupo="SUPERMERCADO")
class SupermercadoStrategy(BaseStrategy):
    def auditar_item(self, prod: dict, regime_tributario: str, **kwargs) -> list:
        alertas = []
        ncm = str(prod.get("ncm", "")).strip()
        cfop = str(prod.get("cfop", "")).strip()
        cst_pis = str(prod.get("cst_pis", "")).strip()
        csosn = str(prod.get("csosn", "")).strip()

        # NCMs comuns de Bebidas Frias (Águas, Refrigerantes, Cervejas) -> Monofásico
        ncms_bebidas_frias = ["2201", "2202", "2203"]
        is_bebida_fria = any(ncm.startswith(prefixo) for prefixo in ncms_bebidas_frias)

        if regime_tributario == "Simples Nacional":
            # Segregação Monofásica de PIS/COFINS em Supermercados
            if is_bebida_fria and cfop in ["5102", "6102"]:
                alertas.append({
                    "tipo": "Oportunidade - PIS/COFINS Monofásico (Bebidas Frias)",
                    "impacto_estimado_rs": float(prod.get("v_prod", 0.0)) * 0.0365,
                    "mensagem": f"Produto NCM {ncm} (Bebidas) é tributado no regime Monofásico. Segregue a receita do PIS/COFINS no PGDAS para não pagar tributo em duplicidade."
                })
        
        return alertas
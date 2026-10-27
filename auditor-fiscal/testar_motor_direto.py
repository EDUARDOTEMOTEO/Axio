"""
TESTE RÁPIDO DO MOTOR DE REGRAS (testar_motor_direto.py)
"""
from src.tax_rules import validar_item_fiscal

def executar_bateria_de_testes():
    print("=" * 60)
    print("⚡ BATERIA DE TESTES DE VERACIDADE - MOTOR FISCAL AXIO")
    print("=" * 60)

    cenarios_teste = [
        {
            "cenario": "1. Venda de Pastilha de Freio (Autopeça Monofásica) no Simples Nacional",
            "regime": "Simples Nacional",
            "item": {"x_prod": "PASTILHA DE FREIO BROS", "ncm": "87083090", "cfop": "5102", "cst_pis": "01", "v_prod": 1200.00}
        },
        {
            "cenario": "2. Venda de Medicamento (Monofásico) no Simples Nacional",
            "regime": "Simples Nacional",
            "item": {"x_prod": "DIPIRONA 500MG 20ML", "ncm": "30049099", "cfop": "5102", "cst_pis": "01", "v_prod": 5000.00}
        },
        {
            "cenario": "3. Entrada de Insumo no Lucro Real Sem Aproveitamento de Crédito",
            "regime": "Lucro Real",
            "item": {"x_prod": "CHAPA DE AÇO INDUSTRIAL", "ncm": "72081000", "cfop": "1101", "cst_pis": "70", "v_prod": 10000.00}
        },
        {
            "cenario": "4. Venda de Produto Comum Sem Monofasia (Deveria vir Sem Alerta)",
            "regime": "Simples Nacional",
            "item": {"x_prod": "CADERNO ESPIRAL 100 FLS", "ncm": "48201000", "cfop": "5102", "cst_pis": "01", "v_prod": 150.00}
        }
    ]

    for teste in cenarios_teste:
        print(f"\n📌 {teste['cenario']}")
        print(f"   Regime: {teste['regime']} | Produto: {teste['item']['x_prod']} | NCM: {teste['item']['ncm']} | Valor: R$ {teste['item']['v_prod']:.2f}")
        
        alertas = validar_item_fiscal(teste['item'], regime_tributario=teste['regime'])
        
        if alertas:
            for a in alertas:
                print(f"   🚨 [DIAGNOÓSTICO DETECTADO] Tipo: {a['tipo']}")
                print(f"      Mensagem: {a['mensagem']}")
                print(f"      Valor Estimado: R$ {a['impacto_estimado_rs']:.2f}")
        else:
            print("   ✅ [OK] Nenhuma inconsistência fiscal identificada (Conforme o esperado).")

if __name__ == "__main__":
    executar_bateria_de_testes()
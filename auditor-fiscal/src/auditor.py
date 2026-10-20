from src.xml_parser import ler_pasta_xmls
from src.tax_rules import auditar_produto

def executar_auditoria(pasta_entrada):
    """
    Executa o processo de leitura e auditoria em lote na pasta de XMLs de entrada.
    """
    print(f"Lendo notas fiscais na pasta: {pasta_entrada}...")
    produtos = ler_pasta_xmls(pasta_entrada)
    
    print(f"Total de produtos encontrados nas notas: {len(produtos)}")
    print("Iniciando auditoria de regras fiscais...\n")
    
    resultados_auditoria = []
    
    for produto in produtos:
        alertas = auditar_produto(produto)
        if alertas:
            resultados_auditoria.append({
                'produto': produto,
                'alertas': alertas
            })
            
    return resultados_auditoria
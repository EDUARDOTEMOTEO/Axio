REGISTRO_SETORES = {}

def registrar_estrategia(setor: str, subgrupo: str = "GERAL"):
    """Decorator para registar automaticamente uma estratégia de auditoria."""
    def decorator(cls):
        chave = (setor.upper(), subgrupo.upper())
        REGISTRO_SETORES[chave] = cls()
        return cls
    return decorator

def obter_estrategia(setor: str, subgrupo: str = "GERAL"):
    """Retorna a instância da estratégia do subgrupo ou o fallback GERAL."""
    chave = (setor.upper(), subgrupo.upper())
    if chave in REGISTRO_SETORES:
        return REGISTRO_SETORES[chave]
    
    return REGISTRO_SETORES.get((setor.upper(), "GERAL"), None)
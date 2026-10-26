import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.database import engine, Base, obter_db
import src.models as models

from src.auditor import executar_auditoria
from src.reporter import gerar_relatorio_excel
from src.auth import criar_token_acesso, obter_empresa_atual, verificar_senha, gerar_hash_senha

app = FastAPI(title="Axio - API de Auditoria Fiscal")

# Garante que todas as tabelas (incluindo as novas) sejam criadas
Base.metadata.create_all(bind=engine)

class CadastroEmpresaUsuario(BaseModel):
    cnpj: str
    razao_social: str
    regime_tributario: str = "Lucro Presumido"
    email: str
    senha: str

@app.on_event("startup")
def inicializar_dados_teste():
    db = next(obter_db())
    empresa_existente = db.query(models.Empresa).first()
    
    if not empresa_existente:
        nova_empresa = models.Empresa(
            cnpj="12345678000199",
            razao_social="Empresa Demonstracao LTDA",
            regime_tributario="Lucro Presumido"
        )
        db.add(nova_empresa)
        db.commit()
        db.refresh(nova_empresa)

        novo_usuario = models.Usuario(
            empresa_id=nova_empresa.id,
            email="admin@empresa.com",
            senha_hash=gerar_hash_senha("123456"),
            papel="admin"
        )
        db.add(novo_usuario)
        db.commit()
    db.close()

@app.get("/")
def pagina_inicial():
    return {"status": "Online", "sistema": "Axio API", "documentacao": "/docs"}

@app.post("/cadastrar")
def cadastrar_empresa_usuario(dados: CadastroEmpresaUsuario, db: Session = Depends(obter_db)):
    usuario_existente = db.query(models.Usuario).filter(models.Usuario.email == dados.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")
    
    empresa = db.query(models.Empresa).filter(models.Empresa.cnpj == dados.cnpj).first()
    if not empresa:
        empresa = models.Empresa(
            cnpj=dados.cnpj,
            razao_social=dados.razao_social,
            regime_tributario=dados.regime_tributario
        )
        db.add(empresa)
        db.commit()
        db.refresh(empresa)
    
    novo_usuario = models.Usuario(
        empresa_id=empresa.id,
        email=dados.email,
        senha_hash=gerar_hash_senha(dados.senha),
        papel="admin"
    )
    db.add(novo_usuario)
    db.commit()
    
    return {"mensagem": "Usuário e empresa cadastrados com sucesso!", "empresa_id": empresa.id}

@app.post("/login")
def realizar_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(obter_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    
    if not usuario or not verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    
    dados_usuario = {
        "sub": usuario.id,
        "empresa_id": usuario.empresa_id,
        "papel": usuario.papel
    }
    
    token = criar_token_acesso(dados_usuario)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/auditoria/executar")
def rodar_auditoria(
    empresa_id: str = Depends(obter_empresa_atual), 
    db: Session = Depends(obter_db)
):
    """Executa a auditoria considerando o regime tributário da empresa ativa."""
    # Busca os dados da empresa ativa no banco de dados
    empresa = db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()
    regime = empresa.regime_tributario if empresa and empresa.regime_tributario else "Lucro Presumido"

    pasta_xmls_entrada = os.path.join("data", "xmls_entrada")
    
    # Executa a auditoria passando o regime tributario dinâmico
    relatorio = executar_auditoria(pasta_xmls_entrada, regime_tributario=regime)
    
    if relatorio:
        gerar_relatorio_excel(relatorio)
        
        for item in relatorio:
            prod = item.get("produto", {})
            for alerta in item.get("alertas", []):
                nova_divergencia = models.DivergenciaFiscal(
                    empresa_id=empresa_id,
                    produto_nome=prod.get("x_prod", "Produto Indefinido"),
                    ncm=prod.get("ncm", ""),
                    cfop=prod.get("cfop", ""),
                    tipo_alerta=alerta.get("tipo", "Aviso"),
                    mensagem=alerta.get("mensagem", "")
                )
                db.add(nova_divergencia)
        db.commit()

    novo_log = models.LogAuditoria(
        empresa_id=empresa_id,
        acao=f"Auditoria executada ({regime}). Divergências gravadas: {len(relatorio) if relatorio else 0}"
    )
    db.add(novo_log)
    db.commit()
    
    return {
        "empresa_id": empresa_id,
        "regime_aplicado": regime,
        "total_ocorrencias": len(relatorio) if relatorio else 0,
        "relatorio": relatorio
    }

@app.get("/auditoria/historico")
def consultar_historico_divergencias(
    empresa_id: str = Depends(obter_empresa_atual),
    db: Session = Depends(obter_db)
):
    """Consulta todas as divergências já registradas no banco para a empresa autenticada."""
    divergencias = db.query(models.DivergenciaFiscal).filter(
        models.DivergenciaFiscal.empresa_id == empresa_id
    ).all()
    
    return {
        "empresa_id": empresa_id,
        "total_registros_salvos": len(divergencias),
        "historico": divergencias
    }
# Esquema Pydantic para atualização da empresa
class AtualizarEmpresaSchema(BaseModel):
    cnpj: str
    razao_social: str
    regime_tributario: str

@app.get("/empresa/obter/{cnpj}")
def obter_empresa_por_cnpj(cnpj: str, db: Session = Depends(obter_db)):
    """Busca as informações completas da empresa pelo CNPJ."""
    empresa = db.query(models.Empresa).filter(models.Empresa.cnpj == cnpj).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    return empresa

@app.put("/empresa/atualizar")
def atualizar_empresa(dados: AtualizarEmpresaSchema, db: Session = Depends(obter_db)):
    """Atualiza a Razão Social e o Regime Tributário da empresa."""
    empresa = db.query(models.Empresa).filter(models.Empresa.cnpj == dados.cnpj).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não cadastrada no banco.")

    empresa.razao_social = dados.razao_social
    empresa.regime_tributario = dados.regime_tributario
    db.commit()
    db.refresh(empresa)

    return {"mensagem": "Dados da empresa atualizados com sucesso!", "empresa": {
        "cnpj": empresa.cnpj,
        "razao_social": empresa.razao_social,
        "regime_tributario": empresa.regime_tributario
    }}
@app.get("/empresas/listar")
def listar_empresas(db: Session = Depends(obter_db)):
    """Retorna todas as empresas cadastradas no banco de dados relacional."""
    empresas = db.query(models.Empresa).all()
    return empresas
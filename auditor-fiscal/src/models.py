import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from datetime import datetime
from src.database import Base

class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cnpj = Column(String, unique=True, index=True, nullable=False)
    razao_social = Column(String, nullable=False)
    regime_tributario = Column(String, nullable=True)

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = Column(String, ForeignKey("empresas.id"), nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    papel = Column(String, default="admin")

class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = Column(String, ForeignKey("empresas.id"), nullable=False)
    usuario_id = Column(String, nullable=True)
    acao = Column(String, nullable=False)
    data_hora = Column(DateTime, default=datetime.utcnow)

class NotaFiscal(Base):
    __tablename__ = "notas_fiscais"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = Column(String, ForeignKey("empresas.id"), nullable=False)
    chave_acesso = Column(String, index=True, nullable=True)
    numero_nota = Column(String, nullable=True)
    cnpj_emitente = Column(String, nullable=True)
    nome_emitente = Column(String, nullable=True)
    data_processamento = Column(DateTime, default=datetime.utcnow)

class DivergenciaFiscal(Base):
    __tablename__ = "divergencias_fiscais"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = Column(String, ForeignKey("empresas.id"), nullable=False)
    nota_fiscal_id = Column(String, ForeignKey("notas_fiscais.id"), nullable=True)
    produto_nome = Column(String, nullable=False)
    ncm = Column(String, nullable=True)
    cfop = Column(String, nullable=True)
    tipo_alerta = Column(String, nullable=False)
    mensagem = Column(String, nullable=False)
    data_auditoria = Column(DateTime, default=datetime.utcnow)
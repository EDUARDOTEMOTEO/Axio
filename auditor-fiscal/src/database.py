import sqlite3
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Inicialmente configurado para SQLite local; pronto para migrar para PostgreSQL futuramente
SQLALCHEMY_DATABASE_URL = "sqlite:///./axio_saas.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def obter_db():
    """Cria uma sessão de base de dados para cada pedido e fecha-a automaticamente no final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Inicializa a base de dados SQLite local com tabelas de empresas e histórico."""
    conn = sqlite3.connect('auditorias_axio.db')
    cursor = conn.cursor()
    
    # Tabela de Empresas Cadastradas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empresas (
            cnpj TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            data_cadastro TEXT
        )
    ''')
    
    # Tabela de Histórico de Auditorias vinculada às empresas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_auditorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT,
            cnpj_empresa TEXT,
            tipo_documento TEXT,
            nome_arquivo TEXT,
            status_auditoria TEXT,
            impacto_financeiro REAL,
            UNIQUE(cnpj_empresa, nome_arquivo),
            FOREIGN KEY(cnpj_empresa) REFERENCES empresas(cnpj)
        )
    ''')
    
    conn.commit()
    conn.close()

def cadastrar_empresa(cnpj, razao_social, regime_tributario, setor_atv="VAREJO", cnae_principal=""):
    """Regista uma nova empresa na base de dados."""
    init_db()
    conn = sqlite3.connect('auditorias_axio.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO empresas (cnpj, razao_social, regime_tributario, setor_atv, cnae_principal)
            VALUES (?, ?, ?, ?, ?)
        """, (cnpj, razao_social, regime_tributario, setor_atv, cnae_principal))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao cadastrar empresa: {e}")
        return False
    finally:
        conn.close()

def obter_empresas_cadastradas():
    """Retorna todas as empresas cadastradas em formato DataFrame."""
    init_db()
    conn = sqlite3.connect('auditorias_axio.db')
    df = pd.read_sql('SELECT * FROM empresas ORDER BY razao_social', conn)
    conn.close()
    return df

def salvar_registro_auditoria(cnpj_empresa, tipo_doc, nome_arquivo, status, impacto):
    """Regista ou atualiza uma auditoria associada a um CNPJ específico."""
    init_db()
    conn = sqlite3.connect('auditorias_axio.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO historico_auditorias (data_hora, cnpj_empresa, tipo_documento, nome_arquivo, status_auditoria, impacto_financeiro)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(cnpj_empresa, nome_arquivo) DO UPDATE SET
            data_hora = excluded.data_hora,
            tipo_documento = excluded.tipo_documento,
            status_auditoria = excluded.status_auditoria,
            impacto_financeiro = excluded.impacto_financeiro
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cnpj_empresa, tipo_doc, nome_arquivo, status, impacto))
    conn.commit()
    conn.close()
    

def obter_historico_db(cnpj_empresa=None):
    """Retorna o histórico de auditorias filtrado pelo CNPJ"""
    init_db()
    conn = sqlite3.connect('auditorias_axio.db')
    df = pd.DataFrame()
    try:
        if cnpj_empresa:
            df = pd.read_sql('SELECT * FROM historico_auditoria WHERE cnpj = ?', conn, params=(cnpj_empresa,))
        else:
            df = pd.read_sql('SELECT * FROM historico_auditoria ORDER BY data_hora DESC', conn)
    except Exception as e:
        print(f"Erro ao ler histórico: {e}")
    finally:
        conn.close()
    return df
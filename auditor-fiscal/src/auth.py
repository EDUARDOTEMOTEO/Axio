import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

SECRET_KEY = "axio_chave_segura_para_autenticacao"
ALGORITHM = "HS256"

# Configuração para criptografia de senhas (bcrypt)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def gerar_hash_senha(senha: str) -> str:
    """Transforma a senha em texto puro em um hash criptografado."""
    return pwd_context.hash(senha)

def verificar_senha(senha_pura: str, senha_hash: str) -> bool:
    """Compara a senha digitada com o hash salvo no banco."""
    return pwd_context.verify(senha_pura, senha_hash)

def criar_token_acesso(dados: dict):
    """Gera o token JWT com o empresa_id embutido."""
    a_codificar = dados.copy()
    expiracao = datetime.utcnow() + timedelta(hours=2)
    a_codificar.update({"exp": expiracao})
    
    return jwt.encode(a_codificar, SECRET_KEY, algorithm=ALGORITHM)

def obter_empresa_atual(token: str = Depends(oauth2_scheme)):
    """Lê o token recebido e extrai o ID da empresa atual."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        empresa_id: str = payload.get("empresa_id")
        
        if empresa_id is None:
            raise HTTPException(status_code=401, detail="Token inválido: falta o ID da empresa.")
            
        return empresa_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token expirado ou inválido.")
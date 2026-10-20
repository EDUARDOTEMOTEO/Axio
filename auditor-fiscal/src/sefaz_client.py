import os
import tempfile
import requests
import xml.etree.ElementTree as ET
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from cryptography.x509.oid import NameOID

def validar_certificado_a1(caminho_pfx, senha):
    try:
        with open(caminho_pfx, "rb") as f:
            pfx_data = f.read()
            
        private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
            pfx_data, senha.encode('utf-8')
        )
        
        titular = "Desconhecido"
        cnpj = ""
        if certificate:
            for attribute in certificate.subject:
                if attribute.oid == NameOID.COMMON_NAME:
                    titular = attribute.value
                    if ":" in titular:
                        parts = titular.split(":")
                        titular = parts[0].strip()
                        if len(parts) > 1:
                            cnpj = parts[1].strip()
                    break
            
            valido_ate = str(certificate.not_valid_after_utc)[:10] if hasattr(certificate, 'not_valid_after_utc') else str(certificate.not_valid_after)[:10]
        else:
            valido_ate = "Desconhecida"
            
        info_certificado = {
            'titular': titular,
            'cnpj': cnpj,
            'valido_ate': valido_ate,
            'status': 'Válido'
        }
        return True, info_certificado
        
    except Exception as e:
        return False, f"Senha incorreta ou ficheiro inválido. ({str(e)})"

def consultar_notas_sefaz_producao(caminho_pfx, senha, cnpj_empresa, nsu_desejado="1"):
    valido, info = validar_certificado_a1(caminho_pfx, senha)
    if not valido:
        raise Exception(f"Certificado inválido: {info}")
        
    cert_path = None
    key_path = None
    
    try:
        with open(caminho_pfx, "rb") as f:
            pfx_data = f.read()
            
        private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
            pfx_data, senha.encode('utf-8')
        )
        
        cert_pem = certificate.public_bytes(Encoding.PEM)
        key_pem = private_key.private_bytes(
            Encoding.PEM,
            PrivateFormat.TraditionalOpenSSL,
            NoEncryption()
        )
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pem') as cert_file:
            cert_file.write(cert_pem)
            cert_path = cert_file.name
            
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pem') as key_file:
            key_file.write(key_pem)
            key_path = key_file.name
            
    except Exception as e:
        return False, f"Erro ao preparar certificado para mTLS: {str(e)}"

    nsu_formatado = str(nsu_desejado).zfill(15)
    
    url_webservice = "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"

    soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDistDFeInteresse xmlns="http://www5.fazenda.sp.gov.br/NFeDistDFeInteresse/NFeDistDFeInteresse.asmx">
      <nfeDadosMsg>
        <distDFeInt versao="1.01" xmlns="http://www.portalfiscal.inf.br/nfe">
          <tpAmb>1</tpAmb>
          <cUFAutor>91</cUFAutor> <!-- 91 representa o Ambiente Nacional (AN) -->
          <CNPJ>{cnpj_empresa}</CNPJ>
          <distNSU>
            <ultNSU>{nsu_formatado}</ultNSU>
          </distNSU>
        </distDFeInt>
      </nfeDadosMsg>
    </nfeDistDFeInteresse>
  </soap12:Body>
</soap12:Envelope>"""

    headers = {
        "Content-Type": "application/soap+xml; charset=utf-8",
        "SOAPAction": "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistDFeInteresse"
    }

    try:
        response = requests.post(
            url_webservice,
            data=soap_envelope.encode('utf-8'),
            headers=headers,
            cert=(cert_path, key_path),
            timeout=30
        )
        
        if cert_path and os.path.exists(cert_path):
            os.remove(cert_path)
        if key_path and os.path.exists(key_path):
            os.remove(key_path)
            
        if response.status_code == 200:
            # Retorna o trecho da resposta para sabermos o que a Sefaz disse
            resposta_crua = response.text[:400].replace("<", "&lt;").replace(">", "&gt;")
            return True, f"Sefaz respondeu (HTTP 200). Retorno: {resposta_crua}"
        else:
            return False, f"Erro HTTP {response.status_code}: {response.text[:200]}"
            
    except Exception as e:
        if cert_path and os.path.exists(cert_path):
            os.remove(cert_path)
        if key_path and os.path.exists(key_path):
            os.remove(key_path)
        return False, f"Erro de rede: {str(e)}"
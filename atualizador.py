import os
import requests
from datetime import datetime
from supabase import create_client, Client

# Busca as chaves de forma segura
URL_SUPABASE = os.environ.get("SUPABASE_URL")
KEY_SUPABASE = os.environ.get("SUPABASE_KEY")

if not URL_SUPABASE or not KEY_SUPABASE:
    print("❌ ERRO: Chaves do Supabase não encontradas!")
    exit()

supabase: Client = create_client(URL_SUPABASE, KEY_SUPABASE)

def buscar_ultimo_sorteio():
    print("📡 Buscando dados na API OFICIAL da Caixa...")
    
    # URL Oficial da Caixa Econômica Federal
    url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"
    
    # "Disfarce" para a Caixa achar que é um humano acessando pelo Chrome
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    try:
        # verify=False é necessário porque a Caixa vira e mexe tem problemas com o próprio certificado SSL
        resposta = requests.get(url, headers=headers, verify=False)
        
        if resposta.status_code == 200:
            dados = resposta.json()
            
            # A Caixa manda a data como DD/MM/AAAA. Vamos formatar para o banco (AAAA-MM-DD)
            data_formatada = datetime.strptime(dados["dataApuracao"], '%d/%m/%Y').strftime('%Y-%m-%d')
            
            # Adaptando para a estrutura JSON da Caixa
            registro = {
                "id": dados["numero"], 
                "data_sorteio": data_formatada,
                "bola_1": int(dados["listaDezenas"][0]),
                "bola_2": int(dados["listaDezenas"][1]),
                "bola_3": int(dados["listaDezenas"][2]),
                "bola_4": int(dados["listaDezenas"][3]),
                "bola_5": int(dados["listaDezenas"][4]),
                "bola_6": int(dados["listaDezenas"][5])
            }
            return registro
        else:
            print(f"❌ Erro na API: Status {resposta.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

def salvar_no_banco(registro):
    if not registro:
        return
        
    try:
        supabase.table("megasena").upsert(registro).execute()
        print(f"✅ Sucesso! Concurso {registro['id']} salvo no Supabase.")
    except Exception as e:
        print(f"❌ Erro ao salvar no banco de dados: {e}")

if __name__ == "__main__":
    # Desativa os avisos de segurança de SSL na tela preta do GitHub
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    sorteio_atual = buscar_ultimo_sorteio()
    salvar_no_banco(sorteio_atual)

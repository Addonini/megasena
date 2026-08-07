import requests
from supabase import create_client, Client

# --- 1. CONFIGURAÇÕES DO SUPABASE ---
# Como este é um script à parte, você pode colar suas chaves direto aqui 
# (só não suba este arquivo para o GitHub público com as chaves abertas!)
URL_SUPABASE = "https://seu-projeto.supabase.co"
KEY_SUPABASE = "sua-chave-anon-publica"

supabase: Client = create_client(URL_SUPABASE, KEY_SUPABASE)

def buscar_ultimo_sorteio():
    print("📡 Buscando dados do último sorteio...")
    
    # API pública que consolida dados das Loterias
    url = "https://loteriascaixa-api.herokuapp.com/api/megasena/latest"
    
    try:
        # Fazendo a requisição na internet
        resposta = requests.get(url)
        
        if resposta.status_code == 200:
            dados = resposta.json() # Transforma o texto da web em um Dicionário Python
            
            # Padronizando os dados para a estrutura da nossa tabela no Supabase
            registro = {
                "id": dados["concurso"], 
                "data_sorteio": dados["data"],
                "bola_1": int(dados["dezenas"][0]),
                "bola_2": int(dados["dezenas"][1]),
                "bola_3": int(dados["dezenas"][2]),
                "bola_4": int(dados["dezenas"][3]),
                "bola_5": int(dados["dezenas"][4]),
                "bola_6": int(dados["dezenas"][5])
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
        # UPSERT: O pulo do gato! 
        # Ele insere um novo registro. Se o 'id' (número do concurso) já existir, ele apenas atualiza.
        # Isso impede que o banco fique com sorteios duplicados se você rodar o script duas vezes.
        resposta = supabase.table("megasena").upsert(registro).execute()
        print(f"✅ Sucesso! Concurso {registro['id']} salvo no Supabase.")
    except Exception as e:
        print(f"❌ Erro ao salvar no banco de dados: {e}")

# --- EXECUÇÃO DO SCRIPT ---
if __name__ == "__main__":
    sorteio_atual = buscar_ultimo_sorteio()
    salvar_no_banco(sorteio_atual)

import os
import re
import json
import time
import requests
import math
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------
# Configurações do Programa
# ---------------------------------------------------------
NUM_REVIEWS_PER_GAME = 500   # Buscamos as 500 mais votadas por jogo
GAMES_FILE = "games_to_analyze_10k.json"
OUTPUT_FILE = "steam_embedding_results.json"
CACHE_DIR = "steam_reviews_500_cache"

# Inicializa o modelo de embeddings (BAAI/bge-small-en-v1.5)
print("Inicializando o modelo de embeddings BAAI/bge-small-en-v1.5...")
model = SentenceTransformer('BAAI/bge-small-en-v1.5')
print("Modelo inicializado com sucesso!")

# ---------------------------------------------------------
# Funções de Busca e APIs
# ---------------------------------------------------------
def get_json(appid, params=None):
    """Realiza a requisição GET para a API de reviews da Steam."""
    url = f'https://store.steampowered.com/appreviews/{appid}'
    if params is None:
        params = {'json': 1}
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"  [API Steam] Erro ao buscar dados para AppID {appid}: {e}")
    return None

def fetch_reviews_for_game(appid, n=500):
    """Busca reviews ordenadas por 'helpfulness' (votos) utilizando paginação por cursor."""
    reviews = []
    cursor = '*'
    params = {
        'json': 1,
        'filter': 'all',          # Ordena por helpfulness
        'language': 'english',
        'day_range': 9223372036854775807,
        'review_type': 'all',
        'purchase_type': 'all',
        'num_per_page': 100
    }
    
    downloaded = 0
    while downloaded < n:
        params['cursor'] = cursor
        data = get_json(appid, params)
        if not data or 'reviews' not in data or not data['reviews']:
            break
            
        cursor = data.get('cursor', '*')
        batch = data['reviews']
        reviews.extend(batch)
        downloaded += len(batch)
        
        if len(batch) < 100:
            break
            
        # Atraso para evitar rate-limiting
        time.sleep(0.4)
        
    # Ordena estritamente por votos recebidos (votes_up) de forma decrescente para garantir as mais votadas
    reviews.sort(key=lambda r: r.get('votes_up', 0), reverse=True)
    return reviews[:n]

def fetch_steamspy_tags(appid):
    """Busca as tags de gênero e comunidade do jogo no SteamSpy."""
    url = f"https://steamspy.com/api.php?request=appdetails&appid={appid}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            tags = data.get("tags", {})
            sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)
            return [tag_name for tag_name, votes in sorted_tags]
    except Exception as e:
        print(f"  [SteamSpy] Erro ao buscar tags para AppID {appid}: {e}")
    return []

# ---------------------------------------------------------
# Funções Auxiliares de Álgebra e Salvamento
# ---------------------------------------------------------
def normalize_vector(v):
    """Normaliza um vetor para que tenha comprimento Euclidiano (L2) igual a 1."""
    norm = math.sqrt(sum(x*x for x in v))
    if norm == 0:
        return v
    return [x/norm for x in v]

def load_results():
    """Carrega o arquivo de progresso para retomar de onde parou."""
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Progresso] Erro ao ler {OUTPUT_FILE}: {e}. Iniciando do zero.")
    return {"games": {}}

def save_results(data):
    """Salva os resultados consolidados em disco."""
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[Erro] Falha ao salvar resultados em {OUTPUT_FILE}: {e}")

# ---------------------------------------------------------
# Execução Principal do Pipeline
# ---------------------------------------------------------
def run_pipeline():
    # 1. Carrega os 10.000 jogos
    if not os.path.exists(GAMES_FILE):
        print(f"[Erro] O arquivo {GAMES_FILE} não existe. Execute o script de coleta primeiro.")
        return
        
    with open(GAMES_FILE, "r", encoding="utf-8") as f:
        games_list = json.load(f)
        
    # 2. Carrega progresso anterior
    results_data = load_results()
    processed_count = len(results_data["games"])
    print(f"\nIniciando processamento. Já processados: {processed_count}/{len(games_list)} jogos.")
    
    # Cria diretório de cache se não existir
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    start_time = time.time()
    count = 0
    
    for game in games_list:
        appid = str(game["appid"])
        name = game["name"]
        
        # Pula se já processado
        if appid in results_data["games"]:
            continue
            
        print(f"\n[{count + processed_count + 1}/{len(games_list)}] Processando {name} (AppID: {appid})...")
        
        # 3. Lógica de Cache Local de Comentários
        cache_path = os.path.join(CACHE_DIR, f"{appid}.json")
        loaded_from_cache = False
        tags = []
        reviews_raw = []
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                tags = cache_data.get("tags", [])
                reviews_raw = cache_data.get("reviews", [])
                print(f"  [Cache] Carregados {len(reviews_raw)} comentários e {len(tags)} tags locais.")
                loaded_from_cache = True
            except Exception as e:
                print(f"  [Aviso] Falha ao ler cache para o jogo {name} ({appid}): {e}")
                
        if not loaded_from_cache:
            print("  Buscando tags (SteamSpy) e reviews (Steam API)...")
            # Busca tags
            tags = fetch_steamspy_tags(appid)[:10]
            # Busca as 500 mais votadas
            reviews_raw = fetch_reviews_for_game(appid, NUM_REVIEWS_PER_GAME)
            
            # Salva no cache mesmo se reviews_raw estiver vazio (evita requisições repetidas no futuro)
            try:
                cache_data = {
                    "appid": int(appid),
                    "name": name,
                    "tags": tags,
                    "reviews": reviews_raw
                }
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=4)
                print(f"  [Cache] Dados salvos em '{cache_path}'.")
            except Exception as e:
                print(f"  [Aviso] Erro ao salvar cache para {name}: {e}")
                
        # 4. Geração de Embeddings e Média Vetorial
        if not reviews_raw:
            print("  [Aviso] Nenhuma review encontrada. Pulando cálculo de embeddings.")
            # Salva dados básicos para constar
            results_data["games"][appid] = {
                "name": name,
                "tags": tags,
                "average_embedding": None,
                "stats": {
                    "total_reviews": 0,
                    "positive_reviews": 0,
                    "negative_reviews": 0
                }
            }
            count += 1
            if count % 10 == 0:
                save_results(results_data)
            continue
            
        # Limpa o texto das reviews (remove BBCodes do Steam para melhor foco semântico)
        reviews_texts = []
        for r in reviews_raw:
            text = r.get("review", "")
            if text:
                # Limpa tags BBCode como [b], [h1], etc.
                text_clean = re.sub(r'\[\/?\w+\]', '', text).strip()
                if text_clean:
                    reviews_texts.append(text_clean)
                    
        if not reviews_texts:
            print("  [Aviso] Reviews sem texto aproveitável.")
            results_data["games"][appid] = {
                "name": name,
                "tags": tags,
                "average_embedding": None,
                "stats": {
                    "total_reviews": len(reviews_raw),
                    "positive_reviews": sum(1 for r in reviews_raw if r.get("voted_up", False)),
                    "negative_reviews": sum(1 for r in reviews_raw if not r.get("voted_up", False))
                }
            }
            count += 1
            if count % 10 == 0:
                save_results(results_data)
            continue
            
        # Calcula os embeddings em lote (batching rápido)
        try:
            print(f"  Gerando embeddings para {len(reviews_texts)} reviews...")
            # BAAI/bge-small-en-v1.5 funciona melhor com embeddings normalizados
            embeddings = model.encode(reviews_texts, batch_size=128, show_progress_bar=False, normalize_embeddings=True)
            
            # Média aritmética simples de todos os vetores de reviews
            mean_vector = embeddings.mean(axis=0).tolist()
            
            # Normalização L2 final para garantir dot_product = cosine_similarity
            avg_embedding = normalize_vector(mean_vector)
            
            # Conta estatísticas de recomendação
            pos_count = sum(1 for r in reviews_raw if r.get("voted_up", False))
            neg_count = len(reviews_raw) - pos_count
            
            # Armazena o jogo na base de embeddings
            results_data["games"][appid] = {
                "name": name,
                "tags": tags,
                "average_embedding": avg_embedding,
                "stats": {
                    "total_reviews": len(reviews_raw),
                    "positive_reviews": pos_count,
                    "negative_reviews": neg_count
                }
            }
            print(f"  [Embeddings] Perfil semântico gerado com sucesso.")
            
        except Exception as e:
            print(f"  [Erro] Falha ao processar embeddings para {name}: {e}")
            
        count += 1
        # Salva o progresso a cada 10 jogos
        if count % 10 == 0:
            save_results(results_data)
            elapsed = time.time() - start_time
            avg_time = elapsed / count
            print(f"\n>>> [Progresso] Salvo! {count} jogos processados nesta sessão. Tempo médio por jogo: {avg_time:.2f}s.")
            
    # Salva final
    save_results(results_data)
    print(f"\n=== PIPELINE CONCLUÍDO! ===")
    print(f"Resultados consolidados salvos em: {OUTPUT_FILE}")

if __name__ == "__main__":
    run_pipeline()

import os
import re
import json
import math
import tkinter as tk
from tkinter import ttk, messagebox
from collections import Counter
from PIL import Image, ImageTk

# Tenta importar sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

# Tenta importar nltk
try:
    import nltk
    from nltk.corpus import stopwords
    HAS_NLTK = True
except ImportError:
    HAS_NLTK = False

# Tenta importar WordCloud
try:
    from wordcloud import WordCloud
    HAS_WORDCLOUD = True
except ImportError:
    HAS_WORDCLOUD = False

# ---------------------------------------------------------
# Dicionário de Tradução Português -> Inglês
# ---------------------------------------------------------
TRANSLATIONS = {
    "historia": "story",
    "enredo": "story",
    "campanha": "story",
    "narrativa": "story",
    "graficos": "graphics",
    "visual": "graphics",
    "visualidade": "graphics",
    "som": "soundtrack",
    "musica": "music",
    "trilha": "soundtrack",
    "audio": "soundtrack",
    "jogabilidade": "gameplay",
    "acao": "action",
    "aventura": "adventure",
    "terror": "horror",
    "medo": "horror",
    "susto": "horror",
    "plataforma": "platformer",
    "dificil": "difficult",
    "dificuldade": "difficulty",
    "desafio": "challenging",
    "cooperativo": "co-op",
    "coop": "co-op",
    "junto": "co-op",
    "parceiro": "co-op",
    "multijogador": "multiplayer",
    "multi": "multiplayer",
    "online": "online",
    "amigos": "friends",
    "mundo aberto": "open world",
    "sobrevivencia": "survival",
    "sobreviver": "survival",
    "combate": "combat",
    "batalha": "combat",
    "luta": "fighting",
    "tiro": "shooter",
    "arma": "shooter",
    "corrida": "racing",
    "carro": "racing",
    "carros": "racing",
    "simulador": "simulator",
    "simulacao": "simulation",
    "estrategia": "strategy",
    "tatico": "strategy",
    "graca": "free",
    "gratis": "free",
    "gratuito": "free",
    "barato": "price",
    "preco": "price",
    "custo": "price",
    "dinheiro": "money",
    "caro": "price",
    "divertido": "fun",
    "legal": "fun",
    "engraçado": "funny",
    "humor": "funny",
    "medieval": "medieval",
    "fantasia": "fantasy",
    "pixel": "pixel",
    "retro": "retro",
    "solitário": "singleplayer",
    "sozinho": "singleplayer",
    "espacial": "space",
    "espaço": "space",
    "ficção científica": "sci-fi",
    "robôs": "robots",
    "construção": "building",
    "construir": "building",
    "cartas": "card",
    "luta": "fighting"
}

GAME_STOPWORDS = {
    'game', 'games', 'play', 'played', 'playing', 'good', 'great', 'fun', 'like', 'best', 
    'really', 'get', 'one', 'would', 'dont', 'im', 'ive', 'even', 'time', 'much', 'also', 
    'still', 'recommend', 'go', 'got', 'think', 'feel', 'feels', 'make', 'makes', 'made', 
    'say', 'saying', 'said', 'people', 'dont', 'cant', 'youre', 'thats', 'experience', 
    'hours', 'nice', 'pretty', 'first', 'love', 'amazing', 'perfect', 'bad', 'buy', 
    'worth', 'awesome', 'everything', 'well', 'every', 'lot', 'way', 'since', 'want',
    'know', 'better', 'try', 'tryin', 'though', 'something', 'never', 'back', 'always',
    'many', '1010', 'years', 'little', 'need', 'day', 'days', 'thing', 'things', 'cool', 
    'pretty', 'super', 'highly', 'reviews', 'review', 'bit', 'lot', 'stuff', 'way', 'ways',
    'end', 'actually', 'point', 'everyone', 'anyone', 'someone', 'nothing', 'anything',
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '0'
}

def remove_accents(text):
    """Remove acentuações comuns da língua portuguesa."""
    mapping = {
        'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c',
        'Á': 'a', 'À': 'a', 'Â': 'a', 'Ã': 'a', 'Ä': 'a',
        'É': 'e', 'È': 'e', 'Ê': 'e', 'Ë': 'e',
        'Í': 'i', 'Ì': 'i', 'Î': 'i', 'Ï': 'i',
        'Ó': 'o', 'Ò': 'o', 'Ô': 'o', 'Õ': 'o', 'Ö': 'o',
        'Ú': 'u', 'Ù': 'u', 'Û': 'u', 'Ü': 'u',
        'Ç': 'c'
    }
    for char, replacement in mapping.items():
        text = text.replace(char, replacement)
    return text

def levenshtein_similarity(s1, s2):
    """Similaridade normalizada Levenshtein para fallback de tradução."""
    s1, s2 = s1.lower().strip(), s2.lower().strip()
    if s1 == s2:
        return 1.0
    m, n = len(s1), len(s2)
    if m == 0 or n == 0:
        return 0.0
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    distance = dp[m][n]
    return 1.0 - (distance / max(m, n))

# ---------------------------------------------------------
# Motor de Busca Vetorial / Semântica
# ---------------------------------------------------------
class SemanticRecommendationEngine:
    def __init__(self, results_json_path):
        self.results_json_path = results_json_path
        self.games_data = {}
        self.model = None
        self.load_database()
        
    def load_database(self):
        """Carrega os dados de embeddings consolidados a partir do JSON."""
        if not os.path.exists(self.results_json_path):
            return False
        try:
            with open(self.results_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.games_data = data.get("games", {})
            return True
        except Exception as e:
            print(f"[Erro] Falha ao carregar base de embeddings: {e}")
            return False
            
    def load_model(self, status_callback=None):
        """Inicializa o modelo SentenceTransformer."""
        if not HAS_TRANSFORMERS:
            return False
        try:
            if status_callback:
                status_callback("Carregando modelo semântico...")
            self.model = SentenceTransformer('BAAI/bge-small-en-v1.5')
            if status_callback:
                status_callback("Modelo Carregado! Pronto para buscar.")
            return True
        except Exception as e:
            print(f"[Erro] Falha ao carregar SentenceTransformer: {e}")
            if status_callback:
                status_callback("Falha ao carregar o modelo.")
            return False

    def clean_query(self, text):
        """Prepara o texto de busca."""
        words = re.findall(r'\b\w+\b', text.lower())
        return words

    def translate_terms(self, terms):
        """Traduz os termos para inglês."""
        translated = []
        for raw_t in terms:
            t = remove_accents(raw_t)
            if t in TRANSLATIONS:
                translated.append(TRANSLATIONS[t])
            else:
                best_match = None
                best_sim = 0.0
                for pt_word, en_word in TRANSLATIONS.items():
                    sim = levenshtein_similarity(t, pt_word)
                    if sim > 0.8 and sim > best_sim:
                        best_sim = sim
                        best_match = en_word
                if best_match:
                    translated.append(best_match)
                else:
                    translated.append(t)
        return list(set(translated))

    def recommend(self, query_text):
        """Calcula a recomendação Top 5 usando busca semântica por cosseno."""
        if not self.games_data or not self.model:
            return []
            
        # 1. Traduz e higieniza a busca
        raw_terms = self.clean_query(query_text)
        if not raw_terms:
            return []
        query_terms = self.translate_terms(raw_terms)
        query_english = " ".join(query_terms)
        print(f"[Busca Semântica] Inglês: '{query_english}'")
        
        # 2. Gera embedding do query
        query_vector = self.model.encode(query_english, normalize_embeddings=True).tolist()
        
        recommendations = []
        for appid, g in self.games_data.items():
            avg_embedding = g.get("average_embedding")
            if not avg_embedding:
                continue
                
            # Produto escalar de vetores L2-normalizados é exatamente a similaridade de cosseno
            cosine_similarity = sum(q * e for q, e in zip(query_vector, avg_embedding))
            
            recommendations.append({
                "appid": appid,
                "name": g["name"],
                "score": cosine_similarity,
                "tags": g.get("tags", []),
                "stats": g.get("stats", {})
            })
            
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:5]

# ---------------------------------------------------------
# Interface Gráfica Tkinter (Steam Dark Mode Theme)
# ---------------------------------------------------------
class AppGUI:
    def __init__(self, root, engine):
        self.root = root
        self.engine = engine
        self.selected_game = None
        self.current_category = 'total'
        
        self.setup_window()
        self.setup_styles()
        self.create_widgets()
        
        # Inicializa o modelo SentenceTransformer de forma assíncrona
        self.root.after(100, self.async_load_model)
        
    def setup_window(self):
        self.root.title("Steam Semantic Suggest - Busca por Embeddings")
        self.root.geometry("1100x680")
        self.root.configure(bg="#1b2838")
        
    def setup_styles(self):
        self.font_title = ("Segoe UI", 16, "bold")
        self.font_subtitle = ("Segoe UI", 12, "bold")
        self.font_body = ("Segoe UI", 10)
        self.font_body_bold = ("Segoe UI", 10, "bold")
        self.font_score = ("Segoe UI", 14, "bold")
        
    def async_load_model(self):
        """Inicializa o modelo SentenceTransformer na thread principal sem bloquear GUI imediatamente."""
        def callback(status_txt):
            self.status_lbl.config(text=status_txt)
            if "Pronto" in status_txt:
                self.status_lbl.config(fg="#a3cf06")
                self.search_btn.config(state="normal")
            elif "Falha" in status_txt:
                self.status_lbl.config(fg="#e05a47")
                
        self.search_btn.config(state="disabled")
        self.status_lbl.config(text="Inicializando modelo BAAI/bge-small-en-v1.5...", fg="#ffc107")
        self.root.update()
        self.engine.load_model(callback)
        
    def create_widgets(self):
        self.root.columnconfigure(0, weight=4)
        self.root.columnconfigure(1, weight=5)
        self.root.rowconfigure(0, weight=1)
        
        # Painel Esquerdo
        left_panel = tk.Frame(self.root, bg="#171a21", padx=20, pady=20)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_panel.rowconfigure(7, weight=1)
        left_panel.columnconfigure(0, weight=1)
        
        # Painel Direito
        right_panel = tk.Frame(self.root, bg="#1b2838", padx=20, pady=20)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(2, weight=1)
        
        # --- ELEMENTOS PAINEL ESQUERDO ---
        title_label = tk.Label(left_panel, text="Busca Semântica Steam (AI)", font=self.font_title, fg="#ffffff", bg="#171a21")
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        # Status do modelo
        self.status_lbl = tk.Label(left_panel, text="Carregando modelo...", font=("Segoe UI", 9, "italic"), fg="#ffc107", bg="#171a21")
        self.status_lbl.grid(row=1, column=0, sticky="w", pady=(0, 10))
        
        desc_label = tk.Label(left_panel, text="Digite uma frase descrevendo o jogo ideal que você busca:\n(Ex: 'a dark fantasy RPG with difficult boss battles')", 
                              font=self.font_body, fg="#c7d5e0", bg="#171a21", justify="left")
        desc_label.grid(row=2, column=0, sticky="w", pady=(0, 10))
        
        # Input e botão de busca
        search_frame = tk.Frame(left_panel, bg="#171a21")
        search_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        search_frame.columnconfigure(0, weight=1)
        
        self.search_entry = tk.Entry(search_frame, font=("Segoe UI", 12), bg="#101822", fg="#ffffff", 
                                     insertbackground="white", bd=1, relief="flat", highlightthickness=1)
        self.search_entry.config(highlightbackground="#2a475e", highlightcolor="#66c0f4")
        self.search_entry.grid(row=0, column=0, sticky="ew", ipady=6, padx=(0, 10))
        self.search_entry.bind("<Return>", lambda event: self.perform_search())
        
        self.search_btn = tk.Button(search_frame, text="Buscar", font=self.font_body_bold, bg="#106ea4", fg="#ffffff",
                               activebackground="#66c0f4", activeforeground="#ffffff", bd=0, padx=20, cursor="hand2",
                               command=self.perform_search)
        self.search_btn.grid(row=0, column=1, sticky="ns")
        self.search_btn.bind("<Enter>", lambda e: self.search_btn.config(bg="#66c0f4"))
        self.search_btn.bind("<Leave>", lambda e: self.search_btn.config(bg="#106ea4"))
        
        # Checkbox auto WordCloud
        self.auto_cloud_var = tk.BooleanVar(value=True)
        self.auto_cloud_cb = tk.Checkbutton(left_panel, text="Gerar/Visualizar WordCloud automaticamente do Top 5", 
                                            variable=self.auto_cloud_var, font=self.font_body, fg="#c7d5e0", bg="#171a21",
                                            activebackground="#171a21", activeforeground="#ffffff", selectcolor="#101822",
                                            cursor="hand2")
        self.auto_cloud_cb.grid(row=4, column=0, sticky="w", pady=(0, 15))
        
        separator = tk.Frame(left_panel, height=2, bg="#2a475e")
        separator.grid(row=5, column=0, sticky="ew", pady=(0, 15))
        
        # Lista resultados
        results_header = tk.Label(left_panel, text="Top 5 Recomendações Semânticas:", font=self.font_subtitle, fg="#66c0f4", bg="#171a21")
        results_header.grid(row=6, column=0, sticky="w", pady=(0, 10))
        
        self.cards_canvas = tk.Canvas(left_panel, bg="#171a21", bd=0, highlightthickness=0)
        self.cards_canvas.grid(row=7, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(left_panel, orient="vertical", command=self.cards_canvas.yview)
        scrollbar.grid(row=7, column=1, sticky="ns")
        self.cards_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.cards_frame = tk.Frame(self.cards_canvas, bg="#171a21")
        self.cards_canvas.create_window((0, 0), window=self.cards_frame, anchor="nw", width=420)
        self.cards_frame.columnconfigure(0, weight=1)
        
        self.no_results_lbl = tk.Label(self.cards_frame, text="Nenhum resultado ainda.\nDigite acima para buscar por inteligência semântica.",
                                       font=self.font_body, fg="#c7d5e0", bg="#171a21", pady=50)
        self.no_results_lbl.grid(row=0, column=0, sticky="ew")

        # --- ELEMENTOS PAINEL DIREITO ---
        self.right_title = tk.Label(right_panel, text="Nuvem de Palavras", font=self.font_title, fg="#ffffff", bg="#1b2838")
        self.right_title.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        self.right_desc = tk.Label(right_panel, text="Selecione um jogo da lista para visualizar a WordCloud gerada a partir das reviews.", 
                                   font=self.font_body, fg="#c7d5e0", bg="#1b2838", justify="left")
        self.right_desc.grid(row=1, column=0, sticky="w", pady=(0, 15))
        
        # Moldura imagem
        self.image_container = tk.Frame(right_panel, bg="#2a475e", bd=1, padx=2, pady=2)
        self.image_container.grid(row=2, column=0, sticky="nsew", pady=(0, 15))
        self.image_container.columnconfigure(0, weight=1)
        self.image_container.rowconfigure(0, weight=1)
        
        self.wc_label = tk.Label(self.image_container, bg="#101822", text="Sem imagem carregada.", 
                                 font=self.font_body, fg="#c7d5e0", width=65, height=13)
        self.wc_label.grid(row=0, column=0, sticky="nsew")
        
        # Categoria abas
        self.tab_frame = tk.Frame(right_panel, bg="#1b2838")
        self.tab_frame.grid(row=3, column=0, sticky="ew", pady=(0, 15))
        
        self.tab_buttons = {}
        categories = [('total', 'Geral'), ('positive', 'Positiva'), ('negative', 'Negativa')]
        for idx, (cat_id, cat_lbl) in enumerate(categories):
            btn = tk.Button(self.tab_frame, text=cat_lbl, font=self.font_body_bold, bg="#2a475e", fg="#c7d5e0",
                            bd=0, padx=15, pady=6, cursor="hand2", command=lambda c=cat_id: self.change_category(c))
            btn.grid(row=0, column=idx, padx=(0, 5))
            self.tab_buttons[cat_id] = btn
            
        # Botão gerar
        self.generate_btn = tk.Button(right_panel, text="Gerar Nuvem de Palavras Manualmente", font=self.font_body_bold,
                                      bg="#a3cf06", fg="#000000", activebackground="#b8e70a", activeforeground="#000000",
                                      bd=0, pady=10, cursor="hand2", command=self.generate_selected_wordcloud)
        self.generate_btn.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self.generate_btn.grid_remove()
        
        # Estatísticas
        self.stats_frame = tk.LabelFrame(right_panel, text=" Estatísticas da Base de Dados ", font=self.font_subtitle, 
                                         fg="#66c0f4", bg="#171a21", bd=1, relief="solid", padx=10, pady=10)
        self.stats_frame.grid(row=5, column=0, sticky="ew")
        self.stats_frame.columnconfigure(0, weight=1)
        self.stats_frame.columnconfigure(1, weight=1)
        self.stats_frame.columnconfigure(2, weight=1)
        
        self.pos_count_lbl = tk.Label(self.stats_frame, text="Positivas: -", font=self.font_body, fg="#a3cf06", bg="#171a21")
        self.pos_count_lbl.grid(row=0, column=0, sticky="w")
        self.neg_count_lbl = tk.Label(self.stats_frame, text="Negativas: -", font=self.font_body, fg="#e05a47", bg="#171a21")
        self.neg_count_lbl.grid(row=0, column=1, sticky="w")
        self.total_count_lbl = tk.Label(self.stats_frame, text="Total: -", font=self.font_body, fg="#ffffff", bg="#171a21")
        self.total_count_lbl.grid(row=0, column=2, sticky="w")

    def perform_search(self):
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("Campo Vazio", "Por favor, digite uma descrição para buscar.")
            return
            
        self.current_recommendations = self.engine.recommend(query)
        
        for widget in self.cards_frame.winfo_children():
            widget.destroy()
            
        if not self.current_recommendations:
            no_match = tk.Label(self.cards_frame, text="Nenhum jogo compatível encontrado.",
                                 font=self.font_body, fg="#e05a47", bg="#171a21", pady=50)
            no_match.grid(row=0, column=0, sticky="ew")
            self.selected_game = None
            self.update_right_panel()
            return
            
        for idx, rec in enumerate(self.current_recommendations):
            self.create_game_card(idx, rec)
            
        self.select_game(self.current_recommendations[0])
        self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox("all"))

    def create_game_card(self, index, data):
        name = data["name"]
        score_pct = data["score"] * 100
        tags = data["tags"]
        
        card_bg = "#233c51" if index == 0 else "#202a39"
        border_color = "#66c0f4" if index == 0 else "#2a475e"
        
        card = tk.Frame(self.cards_frame, bg=card_bg, bd=1, relief="solid", highlightthickness=0, padx=10, pady=10)
        card.grid(row=index, column=0, sticky="ew", pady=(0, 8))
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=0)
        
        text_frame = tk.Frame(card, bg=card_bg)
        text_frame.grid(row=0, column=0, sticky="nw")
        
        name_lbl = tk.Label(text_frame, text=f"{index+1}. {name}", font=self.font_subtitle, fg="#ffffff", bg=card_bg, anchor="w")
        name_lbl.grid(row=0, column=0, sticky="w")
        
        tags_str = ", ".join(tags[:4])
        tags_lbl = tk.Label(text_frame, text=tags_str, font=("Segoe UI", 9), fg="#67c1f5", bg=card_bg, anchor="w")
        tags_lbl.grid(row=1, column=0, sticky="w", pady=(2, 0))
        
        score_lbl = tk.Label(card, text=f"{score_pct:.1f}%", font=self.font_score, fg="#a3cf06", bg=card_bg)
        score_lbl.grid(row=0, column=1, sticky="ne", padx=(10, 0))
        
        bar_frame = tk.Frame(card, height=4, bg="#101822")
        bar_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        # Similaridade de cosseno do BGE varia bastante, normalizamos graficamente de 0 a 100
        bar_fill = tk.Frame(bar_frame, height=4, bg="#a3cf06", width=int(380 * max(0.0, min(1.0, data["score"]))))
        bar_fill.pack(side="left", fill="y")
        
        for w in (card, name_lbl, tags_lbl, score_lbl, text_frame, bar_frame, bar_fill):
            w.bind("<Button-1>", lambda event, r=data: self.select_game(r))
            w.config(cursor="hand2")
            
        def on_enter(e, c=card):
            c.config(highlightbackground="#66c0f4", highlightthickness=1)
        def on_leave(e, c=card):
            c.config(highlightthickness=0)
            
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

    def select_game(self, game_data):
        self.selected_game = game_data
        self.update_right_panel()

    def update_right_panel(self):
        if not self.selected_game:
            self.right_title.config(text="Nuvem de Palavras")
            self.right_desc.config(text="Selecione um jogo para visualizar a WordCloud.")
            self.wc_label.config(image="", text="Sem imagem carregada.")
            self.pos_count_lbl.config(text="Positivas: -")
            self.neg_count_lbl.config(text="Negativas: -")
            self.total_count_lbl.config(text="Total: -")
            self.generate_btn.grid_remove()
            return
            
        name = self.selected_game["name"]
        stats = self.selected_game["stats"]
        
        self.right_title.config(text=name)
        self.right_desc.config(text=f"Sentimento baseado em {stats.get('total_reviews', 0)} comentários.")
        self.pos_count_lbl.config(text=f"Positivas: {stats.get('positive_reviews', 0)}")
        self.neg_count_lbl.config(text=f"Negativas: {stats.get('negative_reviews', 0)}")
        self.total_count_lbl.config(text=f"Total: {stats.get('total_reviews', 0)}")
        
        self.update_tab_buttons_ui()
        self.load_wordcloud_image()

    def update_tab_buttons_ui(self):
        for cat_id, btn in self.tab_buttons.items():
            if cat_id == self.current_category:
                btn.config(bg="#66c0f4", fg="#171a21")
            else:
                btn.config(bg="#2a475e", fg="#c7d5e0")

    def change_category(self, category):
        if self.current_category != category:
            self.current_category = category
            self.update_tab_buttons_ui()
            if self.selected_game:
                self.load_wordcloud_image()

    def load_wordcloud_image(self):
        if not self.selected_game:
            return
        appid = self.selected_game["appid"]
        img_path = f"wordclouds/{appid}_{self.current_category}.png"
        
        if os.path.exists(img_path):
            self.render_wordcloud_file(img_path)
            self.generate_btn.grid_remove()
        else:
            if self.auto_cloud_var.get():
                success = self.generate_wordcloud_on_the_fly(appid, self.current_category)
                if success and os.path.exists(img_path):
                    self.render_wordcloud_file(img_path)
                    self.generate_btn.grid_remove()
                else:
                    self.wc_label.config(image="", text="WordCloud indisponível ou erro na geração.\nClique abaixo para gerar.")
                    self.generate_btn.grid()
            else:
                self.wc_label.config(image="", text="A imagem desta nuvem ainda não existe.\nClique no botão abaixo para gerá-la.")
                self.generate_btn.grid()

    def render_wordcloud_file(self, filepath):
        try:
            img = Image.open(filepath)
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                resample = Image.ANTIALIAS
            img_resized = img.resize((520, 260), resample)
            photo = ImageTk.PhotoImage(img_resized)
            self.wc_label.config(image=photo, text="")
            self.wc_label.image = photo
        except Exception as e:
            self.wc_label.config(image="", text=f"Erro ao renderizar imagem:\n{e}")

    def generate_selected_wordcloud(self):
        if not self.selected_game:
            return
        appid = self.selected_game["appid"]
        success = self.generate_wordcloud_on_the_fly(appid, self.current_category)
        if success:
            img_path = f"wordclouds/{appid}_{self.current_category}.png"
            if os.path.exists(img_path):
                self.render_wordcloud_file(img_path)
                self.generate_btn.grid_remove()
        else:
            messagebox.showerror("Erro", "Não foi possível gerar a WordCloud.")

    def generate_wordcloud_on_the_fly(self, appid, category):
        """Carrega os comentários brutos do cache e gera a WordCloud sob demanda."""
        if not HAS_WORDCLOUD:
            return False
        
        # Carrega o cache de reviews para obter a frequência das palavras
        cache_path = f"steam_reviews_500_cache/{appid}.json"
        if not os.path.exists(cache_path):
            print(f"[WordCloud] Cache não encontrado: {cache_path}")
            return False
            
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            reviews = cache_data.get("reviews", [])
            
            # Filtra reviews pela categoria
            filtered_texts = []
            for r in reviews:
                voted_up = r.get("voted_up", True)
                text = r.get("review", "")
                if not text:
                    continue
                if category == 'positive' and not voted_up:
                    continue
                if category == 'negative' and voted_up:
                    continue
                
                text_clean = re.sub(r'\[\/?\w+\]', '', text).lower().strip()
                if text_clean:
                    filtered_texts.append(text_clean)
                    
            if not filtered_texts:
                return False
                
            # Extrai e conta palavras
            words_list = []
            for t in filtered_texts:
                # Divide palavras básicas
                tokens = re.findall(r'\b\w+\b', t)
                for tok in tokens:
                    if len(tok) > 2 and tok not in GAME_STOPWORDS:
                        words_list.append(tok)
                        
            if not words_list:
                return False
                
            frequencies = Counter(words_list)
            
            # Define cores
            bg_color = 'grey'
            if category == 'positive':
                bg_color = 'white'
            elif category == 'negative':
                bg_color = 'black'
                
            os.makedirs("wordclouds", exist_ok=True)
            wc = WordCloud(width=800, height=400, background_color=bg_color)
            wc.generate_from_frequencies(frequencies)
            
            img_path = f"wordclouds/{appid}_{category}.png"
            wc.to_file(img_path)
            print(f"[WordCloud] Gerada em tempo de execução para AppID {appid}")
            return True
        except Exception as e:
            print(f"[Erro WordCloud] {e}")
            return False

# ---------------------------------------------------------
# Ponto de Entrada
# ---------------------------------------------------------
def main():
    database_path = "steam_embedding_results.json"
    engine = SemanticRecommendationEngine(database_path)
    success = engine.load_database()
    
    root = tk.Tk()
    if not success:
        root.withdraw()
        messagebox.showerror("Erro", f"Base de embeddings '{database_path}' não encontrada.\n\nPor favor, execute o script steam_embedding_analyzer.py primeiro.")
        root.destroy()
        return
        
    app = AppGUI(root, engine)
    root.mainloop()

if __name__ == "__main__":
    main()

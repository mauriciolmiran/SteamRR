# 📜 Proveniência de Dados (Data Provenance)

A **proveniência de dados (Data Provenance / Rastreabilidade)** neste projeto é estruturada em **3 níveis de linhagem (Lineage)**, garantindo a auditabilidade e reprodutibilidade desde a coleta bruta até a inferência vetorial.

---

## 1. Origem dos Dados Brutos (Data Source Lineage)

Cada dado do sistema possui uma fonte primária identificável e auditável:

- **Entidade Principal (Jogos):** Origem no repositório de catálogo `games_to_analyze_10k.json` (mapeados via `AppID` oficial da Steam).
- **Análises (Reviews de Usuários):** Coletadas via requisições HTTP REST diretas à API Oficial da Steam:
  `https://store.steampowered.com/appreviews/{appid}`
  - Parâmetros fixados para reprodutibilidade: `language=english`, ordenadas por `votes_up` (helpfulness).
- **Gêneros e Categorias (Tags):** Coletadas via API pública do **SteamSpy**:
  `https://steamspy.com/api.php?request=appdetails&appid={appid}`

---

## 2. Rastreabilidade Intermediária e Cache Auditável (Raw Data Cache)

Antes do cálculo dos embeddings, o script `steam_embedding_analyzer.py` persiste o estado bruto de cada jogo no diretório `steam_reviews_500_cache/{appid}.json`:

```json
{
    "appid": 730,
    "name": "Counter-Strike: Global Offensive",
    "tags": ["FPS", "Multiplayer", "Shooter", "Competitive"],
    "reviews": [ ... lista bruta das 500 reviews com 'review', 'voted_up', 'votes_up' ... ]
}
```

- **Garantia de Proveniência:** Permite re-auditar os comentários originais de cada jogo a qualquer momento sem necessidade de realizar novas chamadas de rede.

---

## 3. Metadados de Transformação e Modelo (Feature & Vector Provenance)

No arquivo final `steam_embedding_results.json`, a proveniência de cada vetor de embedding é enriquecida com a proveniência estatística do cálculo:

- **Modelo Utilizado:** Modelo neural pré-treinado `BAAI/bge-small-en-v1.5` (SentenceTransformers, 384 dimensões).
- **Limpeza/Transformação Aplicada:** Remoção de marcações BBCode (`[b]`, `[h1]`), normalização vetorial em espaço **L2** ($\|v\|_2 = 1$) e média aritmética simples dos vetores de cada review.
- **Metadados Associados (Audit Trail):**
  ```json
  "stats": {
      "total_reviews": 500,
      "positive_reviews": 432,
      "negative_reviews": 68
  }
  ```

---

## 4. Transparência na Interface do Usuário (`indicacao_embedding.py`)

Na interface gráfica, a proveniência e explicabilidade do resultado são apresentadas ao usuário final em tempo real:

- **Grau de Relevância:** Exibido como pontuação percentual ($Score = \cos(\theta) \times 100\%$).
- **Fator de Confiança:** Exibe no painel direito exatamente em quantas análises aquele resultado foi baseado (*"Sentimento baseado em 500 comentários"*), além do detalhamento de votos positivos/negativos.
- **Origem Visual:** Gera a WordCloud a partir do cache preservado de comentários originais para a categoria selecionada (Geral, Positiva ou Negativa).

# 🎬 SONAR LSE STUDIO — Legendagem Descritiva de Foley & Sonoplastia

> **Desenvolvido para a Sonar** para atender a demandas de pós-produção audiovisual e acessibilidade no **Festival Internacional de Animação de Pernambuco (Animage)**.

O **Sonar LSE Studio** é uma plataforma especializada na criação automatizada de **Legendas para Surdos e Ensurdecidos (LSE / Closed Captions - SDH)** focadas especificamente em **efeitos sonoros (foley), ruídos de cena, ambiência e trilha musical**, suprindo a grande lacuna das ferramentas convencionais de mercado que apenas transcrevem falas humanas.

---

## 🎯 O Problema que Resolve

Em curtas-metragens de animação e filmes com estética puramente acústica:
1. **Não existem diálogos falados** ou as falas são mínimas e secundárias.
2. A história é inteiramente narrada através da **sonoplastia** (portas rangendo, passos na madeira, vento, baques metálicos, instrumentos e transições musicais).
3. Ferramentas como Whisper, Descript, Premiere Auto-Captions e CapCut **falham completamente** por serem modelos estritos de fala (ASR). Quando não há fala, produzem legendas vazias ou geram alucinações de palavras inexistentes.

O **Sonar LSE Studio** utiliza **IA Multimodal Acústica (Google Gemini)** para "ouvir" o áudio bruto e o espectrograma completo, detectando e sincronizando eventos acústicos no formato padrão **SRT** conforme a norma **ABNT NBR 15290**.

---

## 🚀 Principais Funcionalidades

- **Processamento em Lote (Batch Processing):** Carregue 20 ou 30 filmes de uma só vez para cumprir prazos de festivais com tranquilidade.
- **Extração de Áudio Integrada com FFmpeg:** Aceita arquivos de vídeo (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`) e de áudio (`.ogg`, `.mp3`, `.wav`, `.m4a`).
- **3 Modos de Análise:**
  1. **Sonoplastia & Foley Puro:** Foco total em ruídos, impactos e música entre colchetes `[...]` (ideal para animações mudas).
  2. **LSE Completo:** Transcrição de falas intercalada com os ruídos de foley.
  3. **Trilha Sonora & Ambiência:** Mapeamento minucioso de instrumentos, andamento musical e clima acústico.
- **Monitor Acústico & Editor Sincronizado:**
  - Player de som integrado com atalhos de teclado (`[Espaço]` Play/Pause, `[J]` -2s, `[L]` +2s).
  - Tabela interativa que destaca a legenda ativa na linha do tempo.
  - Permite clicar em qualquer legenda para saltar o áudio para aquele timestamp.
  - Edição direta de textos e timestamps com botão de salvar.
- **Exportação Multiformato:**
  - Download individual em `.SRT` e `.VTT`.
  - Download em lote de todas as legendas em um único arquivo `.ZIP`.
- **Interface Web Cinematográfica:** Tema dark profissional nas cores oficiais da Sonar (Slate, Amber e Cyan).
- **CLI Headless (`sonar_cli.py`):** Automação rápida pelo terminal para usuários avançados.
- **Inicializador 1-Clique (`iniciar.bat`):** Basta clicar duas vezes no Windows para abrir o app no navegador.

---

## 🛠️ Tecnologias e Dependências

- **Linguagem:** Python 3.12+ gerenciado via `uv`
- **Framework Web:** FastAPI + Uvicorn
- **Inteligência Acústica:** Google GenAI SDK (`gemini-2.5-flash` / `gemini-1.5-flash` / `gemini-3.8-flash`)
- **Processamento de Mídia:** FFmpeg
- **Front-end:** HTML5, CSS3 Custom Design System (Dark Studio), Vanilla JS reativo

---

## ⚡ Como Iniciar

### 1. Início Rápido no Windows
Basta dar dois cliques no arquivo:
```cmd
iniciar.bat
```
O script instalará as dependências automaticamente e abrirá o estúdio em seu navegador padrão em `http://127.0.0.1:8000`.

### 2. Execução via Terminal (com UV)
```powershell
cd C:\Users\alexk\projects\sonar-lse-studio
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Execução em Lote via Linha de Comando (CLI)
Para processar uma pasta cheia de curtas de uma vez só sem abrir o navegador:
```powershell
uv run python sonar_cli.py "C:\caminho\dos\curtas" --mode foley_only --output "C:\caminho\legendas_prontas"
```

---

## 🔑 Configuração da API

Consulte o arquivo **[GUIA_CONFIGURACAO_API.md](file:///C:/Users/alexk/projects/sonar-lse-studio/GUIA_CONFIGURACAO_API.md)** para o passo a passo com link para gerar a chave gratuita no Google AI Studio e cadastrá-la com 1 clique pela tela de configurações do próprio aplicativo.

---

## 🌐 Ecossistema Sonar

- **Site Oficial em Produção:** [https://sonaracess.vercel.app](https://sonaracess.vercel.app)
- **Repositório do Site:** [https://github.com/alexmsza/sonar-site](https://github.com/alexmsza/sonar-site)
- **Planejamento Estratégico & Unit Economics:** [PLANEJAMENTO_ESTRATEGICO_SONAR.md](file:///C:/Users/alexk/projects/sonar-lse-studio/PLANEJAMENTO_ESTRATEGICO_SONAR.md)

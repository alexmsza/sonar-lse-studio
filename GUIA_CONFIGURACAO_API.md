# 🔑 Guia de APIs e Configuração — Sonar LSE Studio

Este guia foi elaborado para a equipe da **Sonar** configurar em poucos minutos a infraestrutura de inteligência acústica necessária para processar os curtas-metragens do **Festival Animage** e demandas frequentes de legendagem descritiva (LSE / SDH).

---

## 1. Qual API é necessária e por quê?

### 🎯 API Principal Obrigatória: **Google Gemini API** (Google AI Studio)

| Característica | Detalhes |
| :--- | :--- |
| **Provedor** | Google DeepMind / Google AI Studio |
| **Modelos Recomendados** | `gemini-2.5-flash` ou `gemini-1.5-flash` |
| **Custo** | **Gratuito** (Camada Free com 15 requisições por minuto - mais que suficiente para processar todos os curtas do festival sem pagar nada). |
| **Capacidade Chave** | **Compreensão Acústica Multimodal Nativa**. Escuta o áudio/espectrograma bruto e detecta ruídos, passos, portas rangendo, instrumentos musicais e foley. |

### ❓ Por que o Whisper e outras ferramentas pagas falham nessa demanda?
Como você bem observou no dia a dia, ferramentas convencionais (OpenAI Whisper, Premiere Auto-Captions, CapCut, Descript, Veed.io) foram desenvolvidas estritamente para **ASR (Automatic Speech Recognition - Reconhecimento de Fala)**. Elas buscam fonemas falados da boca humana.
- **Quando o filme não tem falas** (como muitos curtas de animação), o Whisper considera o áudio "silêncio" ou tenta inventar palavras aleatórias (alucinações).
- O **Google Gemini**, por outro lado, é um modelo multimodal que "ouve" o som completo, identificando timbres, instrumentos, impactos físicos e ruídos de cena com marcação temporal precisa.

---

## 2. Passo a Passo: Como Obter a Chave de API (Grátis)

1. Acesse o portal do desenvolvedor do Google:
   👉 **[https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)**
2. Faça login com qualquer conta Google (Gmail ou Workspace da Sonar).
3. Clique no botão azul **"Create API Key"** (Criar chave de API).
4. Selecione ou crie um projeto padrão e confirme.
5. Copie a chave gerada (ela começa com `AIzaSy...`).

> [!TIP]
> Guarde essa chave em um local seguro. Ela concede acesso à cota gratuita do Google AI Studio para sua empresa.

---

## 3. Como Cadastrar a Chave no Sonar LSE Studio

Você tem **duas formas super fáceis** de cadastrar a chave no aplicativo:

### Opção A: Pela Interface Web (Recomendado)
1. Inicie o programa dando 2 cliques em `iniciar.bat`.
2. No canto superior direito da tela, clique no botão **"⚙️ Configurar API"**.
3. Cole a sua chave no campo **"Chave da Google Gemini API"**.
4. Clique em **"🧪 Testar Conexão"** — o app fará um teste em tempo real e mostrará um indicador verde `✓ Conexão com a Google Gemini API validada com sucesso!`.
5. Clique em **"💾 Salvar Configurações"**. O app salvará automaticamente no seu `.env` local.

### Opção B: Direto no Arquivo `.env`
1. Abra a pasta do programa `sonar-lse-studio`.
2. Abra o arquivo `.env` (ou duplique o `.env.example` para `.env`).
3. Insira sua chave:
   ```env
   GEMINI_API_KEY=AIzaSySuaChaveAqui123456789
   GEMINI_MODEL=gemini-2.5-flash
   ```
4. Salve o arquivo.

---

## 4. Ferramenta Local Auxiliar: FFmpeg

O sistema utiliza o **FFmpeg** em segundo plano para extrair o áudio dos vídeos (`.mp4`, `.mov`, `.mkv`) em alta fidelidade acústica antes de enviar para a IA.
- O FFmpeg já está instalado no seu computador e é chamado automaticamente pelo programa.
- Caso utilize em outra máquina no futuro, basta instalar via winget:
  ```powershell
  winget install Gyan.FFmpeg
  ```

---

## 5. Estratégia de Entrega para os 7 Dias do Animage

1. **Agrupamento em Lote:** Coloque todos os arquivos de vídeo ou áudio dos curtas em uma pasta.
2. **Importação:** Arraste todos os arquivos de uma vez para o dropzone do Sonar LSE Studio.
3. **Modo Recomendado:**
   - Selecione **"🔊 Sonoplastia & Foley Puro"** para animações sem falas.
   - Deixe a sensibilidade em **"Alta Sensibilidade"** para registrar os mínimos efeitos de cena (portas, passos, vento, impacto).
4. **Exportação:** Após a fila concluir, clique em **"📦 Baixar Tudo (.ZIP)"** para receber todas as legendas `.srt` padronizadas na ABNT NBR 15290 prontas para entrega ao festival.

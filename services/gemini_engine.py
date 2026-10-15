"""
Motor de Inteligência Acústica da Sonar com Google Gemini API.
Analisa espectrogramas e fluxos acústicos de áudio para gerar LSE (SDH) e Foley.
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

from services.srt_formatter import parse_srt_to_entries, entries_to_srt, clean_llm_srt_output


SYSTEM_PROMPT_FOLEY_ONLY = """Você é um Engenheiro de Som Sênior e Especialista em Acessibilidade Audiovisual (LSE - Legenda para Surdos e Ensurdecidos / SDH), prestando serviços para a produtora Sonar no Festival Internacional de Animação de Pernambuco (Animage).

O filme analisado é um curta-metragem de animação que NÃO possui diálogos falados (ou quase nenhum). Toda a narrativa dramática, cômica ou emotiva é transmitida através da SONOPLASTIA, EFEITOS SONOROS (FOLEY), RUÍDOS DE AMBIÊNCIA e TRILHA MUSICAL.

Sua missão é ouvir atentamente toda a extensão do áudio e produzir uma legenda descritiva LSE rigorosamente no formato de arquivo SRT (.srt), em conformidade estrita com a ABNT NBR 15290.

DIRETRIZES DE FOLEY E SONOPLASTIA:
1. DESCRITORES ENTRE COLCHETES: Todas as descrições de ruídos e músicas DEVEM estar obrigatoriamente entre colchetes `[...]`.
   Exemplos reais:
   - [Porta rangendo vagarosamente]
   - [Passos pesados no assoalho de madeira]
   - [Vento forte soprando pelas frestas]
   - [Música instrumental alegre com xilofone]
   - [Goteira metálica ritmada]
   - [Ruído de estática e interferência]
   - [Música cessa abruptamente]
   - [Suspiro ofegante]
   - [Trilha de suspense com cordas tensas]
   - [Batida metálica estrondosa]

2. DETALHAMENTO ACÚSTICO:
   - Capture tanto sons de primeiro plano (ações dos personagens, impactos, ferramentas) quanto de plano de fundo (ambiências, pássaros, trovões distantes).
   - Identifique os instrumentos principais e o clima emotivo da música.

3. PRECISÃO DE TIMESTAMPS:
   - O formato deve ser SRT padrão:
     1
     00:00:01,200 --> 00:00:03,800
     [Música suave de piano ao fundo]

     2
     00:00:04,100 --> 00:00:06,500
     [Passos apressados na calçada]

   - Respeite o início exato e fim de cada efeito sonoro.
   - Duração de cada bloco de legenda entre 1.2s e 5.0s para permitir leitura confortável.

4. SAÍDA PURA:
   - Responda EXCLUSIVAMENTE com o conteúdo SRT válido.
   - NUNCA inclua explicações, comentários, tags extras de markdown ou saudações antes ou depois do SRT.
"""

SYSTEM_PROMPT_FULL_SDH = """Você é um Especialista Sênior em Acessibilidade Audiovisual (LSE - Legenda para Surdos e Ensurdecidos / SDH) da produtora Sonar.

Sua missão é analisar o áudio e produzir uma legenda mista completa no formato SRT (.srt), contendo tanto os DIÁLOGOS FALADOS quanto a SONOPLASTIA, RUÍDOS (FOLEY) e TRILHA MUSICAL (ABNT NBR 15290).

DIRETRIZES:
1. Diálogos falados devem ser transcritos textualmente com clareza.
2. Efeitos sonoros, ruídos, reações vocais não-verbais e músicas devem estar SEMPRE entre colchetes `[...]`.
   Exemplo:
   1
   00:00:02,000 --> 00:00:04,500
   [Porta abrindo bruscamente]

   2
   00:00:05,000 --> 00:00:07,300
   - Quem está aí?

   3
   00:00:07,800 --> 00:00:10,200
   [Música tensa de suspense com violinos]

3. Retorne EXCLUSIVAMENTE o arquivo SRT válido, sem introduções ou observações.
"""

SYSTEM_PROMPT_MUSIC_AMBIENCE = """Você é um Designer de Som e Musicólogo da produtora Sonar.
Sua missão é mapear e descrever com riqueza toda a TRILHA MUSICAL e AMBIÊNCIA SONORA da obra no formato SRT.

DIRETRIZES:
1. Descreva gênero musical, instrumentos dominantes, andamento e transições emocionais entre colchetes `[...]`.
2. Exemplo: `[Música orquestral dramática em crescendo]`, `[Trilha eletrônica com batida pulsante]`, `[Silêncio absoluto quebrado por eco distante]`.
3. Retorne EXCLUSIVAMENTE o bloco SRT.
"""


class GeminiLSEEngine:
    """Motor de análise acústica e geração de legendas LSE da Sonar."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key.strip()
        self.model_name = model_name.strip() if model_name else "gemini-2.5-flash"
        self.client = genai.Client(api_key=self.api_key)

    def generate_lse_subtitles(
        self,
        audio_path: Path,
        mode: str = "foley_only",
        detail_level: str = "high",
        language: str = "pt-br"
    ) -> Dict[str, Any]:
        """
        Envia o áudio para o Google Gemini e gera as legendas descritivas.
        Retorna dicionário com o SRT limpo, lista de entradas e metadados.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_path}")

        # Seleciona o system prompt adequado
        if mode == "full_sdh":
            system_prompt = SYSTEM_PROMPT_FULL_SDH
        elif mode == "music_ambience":
            system_prompt = SYSTEM_PROMPT_MUSIC_AMBIENCE
        else:
            system_prompt = SYSTEM_PROMPT_FOLEY_ONLY

        # Ajusta instrução complementar
        extra_instruction = f"\n\nATENÇÃO: O idioma das descrições deve ser rigorosamente {language.upper()}."
        if detail_level == "high":
            extra_instruction += " Forneça máxima sensibilidade aos menores ruídos de sonoplastia, cliques, respirações e variações da trilha sonora."

        user_prompt = f"{system_prompt}{extra_instruction}\n\nAnalise o arquivo de áudio anexo e gere o arquivo SRT completo:"

        # Upload do arquivo de áudio na Google Gemini Files API
        uploaded_file = self.client.files.upload(
            file=str(audio_path)
        )

        try:
            # Lista de modelos para tentativa em cascata caso o especificado não esteja ativo na chave
            models_to_try = [self.model_name, "gemini-2.5-flash", "gemini-1.5-flash", "gemini-3.8-flash"]
            seen = set()
            clean_models = [m for m in models_to_try if not (m in seen or seen.add(m))]

            raw_response_text = ""
            active_model = self.model_name
            last_err = None

            for m in clean_models:
                try:
                    response = self.client.models.generate_content(
                        model=m,
                        contents=[uploaded_file, user_prompt],
                        config=types.GenerateContentConfig(
                            temperature=0.2,  # Baixa temperatura para precisão temporal e consistência
                            top_p=0.95
                        )
                    )
                    if response and response.text:
                        raw_response_text = response.text
                        active_model = m
                        break
                except Exception as ex:
                    last_err = ex
                    continue

            if not raw_response_text:
                raise RuntimeError(f"A API Gemini não retornou texto válido. Último erro: {last_err}")

            # Limpa e processa o SRT
            clean_srt = clean_llm_srt_output(raw_response_text)
            entries = parse_srt_to_entries(clean_srt)

            # Se por ventura a lista vier vazia, garante que a string original seja tratada
            if not entries and clean_srt:
                entries = parse_srt_to_entries(raw_response_text)

            reformatted_srt = entries_to_srt(entries)

            return {
                "success": True,
                "model_used": active_model,
                "raw_text": raw_response_text,
                "srt_content": reformatted_srt,
                "entries": entries,
                "entry_count": len(entries)
            }

        finally:
            # Limpa o arquivo na nuvem após processamento para privacidade e conformidade
            try:
                self.client.files.delete(name=uploaded_file.name)
            except Exception:
                pass

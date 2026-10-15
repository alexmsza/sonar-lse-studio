"""
Sonar CLI — Interface de Linha de Comando para Automação em Lote.
Processa dezenas de filmes e animações em alta velocidade gerando arquivos .SRT de LSE.
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis
load_dotenv()

from services.audio_processor import AudioProcessor, AUDIO_EXTENSIONS, VIDEO_EXTENSIONS
from services.gemini_engine import GeminiLSEEngine
from services.config_manager import get_gemini_api_key, get_default_model


def main():
    parser = argparse.ArgumentParser(
        description="Sonar LSE Studio CLI — Gerador de Legendas Descritivas para Festivais de Cinema (Animage)"
    )
    parser.add_argument("input_path", type=str, help="Caminho do arquivo ou diretório contendo os filmes/áudios")
    parser.add_argument("-o", "--output", type=str, default="./outputs", help="Diretório onde os arquivos .SRT serão salvos")
    parser.add_argument("-m", "--mode", choices=["foley_only", "full_sdh", "music_ambience"], default="foley_only", help="Modo de análise (default: foley_only)")
    parser.add_argument("-d", "--detail", choices=["high", "medium"], default="high", help="Sensibilidade da detecção de som (default: high)")
    parser.add_argument("-l", "--language", default="pt-br", help="Idioma das descrições (default: pt-br)")
    parser.add_argument("--key", type=str, default="", help="Chave Google Gemini API (opcional se já salva em .env)")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="Modelo Gemini (default: gemini-2.5-flash)")

    args = parser.parse_args()

    api_key = args.key or get_gemini_api_key()
    if not api_key:
        print("\n[ERRO CRÍTICO] Chave da API do Google Gemini não encontrada!")
        print("Defina no arquivo .env (GEMINI_API_KEY=sua_chave) ou passe o parâmetro --key AIzaSy...")
        sys.exit(1)

    input_path = Path(args.input_path)
    if not input_path.exists():
        print(f"[ERRO] Caminho de entrada não existe: {input_path}")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = output_dir / "temp_audio"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Coleta arquivos para processar
    valid_extensions = AUDIO_EXTENSIONS.union(VIDEO_EXTENSIONS)
    files_to_process = []

    if input_path.is_file():
        if input_path.suffix.lower() in valid_extensions:
            files_to_process.append(input_path)
    elif input_path.is_dir():
        for f in input_path.iterdir():
            if f.is_file() and f.suffix.lower() in valid_extensions:
                files_to_process.append(f)

    if not files_to_process:
        print(f"[AVISO] Nenhum arquivo de áudio ou vídeo compatível encontrado em: {input_path}")
        sys.exit(0)

    print(f"\n==========================================================")
    print(f"🎬 SONAR LSE STUDIO — Automação em Lote")
    print(f"📁 Arquivos para processar: {len(files_to_process)}")
    print(f"⚙️  Modo: {args.mode} | Modelo: {args.model} | Idioma: {args.language}")
    print(f"==========================================================\n")

    engine = GeminiLSEEngine(api_key=api_key, model_name=args.model)

    success_count = 0
    for idx, media_file in enumerate(files_to_process, start=1):
        print(f"[{idx}/{len(files_to_process)}] Processando: {media_file.name}...")
        try:
            # 1. Extração / Normalização de áudio
            print(f"  -> Extraindo áudio via FFmpeg...")
            audio_path, duration, mime = AudioProcessor.prepare_audio_for_analysis(media_file, temp_dir)
            print(f"  -> Duração: {duration:.1f}s")

            # 2. Análise com IA
            print(f"  -> Analisando sonoplastia e gerando legendas com IA...")
            res = engine.generate_lse_subtitles(
                audio_path=audio_path,
                mode=args.mode,
                detail_level=args.detail,
                language=args.language
            )

            # 3. Salva SRT
            srt_dest = output_dir / f"{media_file.stem}.srt"
            srt_dest.write_text(res["srt_content"], encoding="utf-8")
            print(f"  -> [SUCESSO] Legenda salva em: {srt_dest.name} ({res['entry_count']} eventos detectados)\n")
            success_count += 1

        except Exception as e:
            print(f"  -> [FALHA] Erro ao processar {media_file.name}: {e}\n")

    print(f"==========================================================")
    print(f"✓ Concluído: {success_count}/{len(files_to_process)} legendas geradas com sucesso!")
    print(f"📂 Diretório de saída: {output_dir.resolve()}")
    print(f"==========================================================\n")


if __name__ == "__main__":
    main()

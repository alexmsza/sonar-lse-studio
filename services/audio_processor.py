"""
Processador de Áudio e Vídeo via FFmpeg para a Sonar.
Extrai, converte e normaliza fluxos acústicos de filmes e animações.
"""

import os
import subprocess
import json
import re
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac", ".wma", ".opus"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv", ".m4v"}


class AudioProcessor:
    """Gerencia extração, download de streaming e normalização de áudio para legendagem e audiodescrição."""

    @staticmethod
    def get_duration(file_path: Path) -> float:
        """Obtém a duração total do arquivo em segundos via FFmpeg."""
        cmd = [
            "ffmpeg",
            "-i", str(file_path),
            "-f", "null",
            "-"
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", result.stderr)
            if match:
                hours = float(match.group(1))
                minutes = float(match.group(2))
                seconds = float(match.group(3))
                return hours * 3600 + minutes * 60 + seconds
        except Exception as e:
            print(f"Erro ao obter duração: {e}")
        return 0.0

    @staticmethod
    def is_video_file(file_path: Path) -> bool:
        """Verifica se o arquivo é um formato de vídeo."""
        return file_path.suffix.lower() in VIDEO_EXTENSIONS

    @staticmethod
    def download_media_from_url(url: str, output_dir: Path) -> Tuple[Path, str, float]:
        """
        Baixa o vídeo/áudio a partir de um link da web (YouTube, Vimeo, redes ou links diretos MP4).
        Utiliza yt-dlp com seleção de formato compatível com browsers (MP4 H.264/AAC).
        Retorna (caminho_arquivo_baixado, titulo_do_video, duracao_segundos).
        """
        import yt_dlp

        output_dir.mkdir(parents=True, exist_ok=True)
        # Template seguro de arquivo
        outtmpl = str(output_dir / "%(id)s_%(title).60s.%(ext)s")

        ydl_opts = {
            "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise ValueError("Não foi possível extrair informações do link fornecido.")

            title = info.get("title") or "Streaming_Video"
            duration = float(info.get("duration") or 0.0)

            # Localiza o arquivo gerado
            expected_filename = ydl.prepare_filename(info)
            downloaded_path = Path(expected_filename)

            # Se o arquivo foi convertido para mp4
            if not downloaded_path.exists():
                mp4_variant = downloaded_path.with_suffix(".mp4")
                if mp4_variant.exists():
                    downloaded_path = mp4_variant
                else:
                    # Busca o arquivo mais recente no diretório
                    candidates = sorted(output_dir.glob(f"{info.get('id', '')}*"), key=os.path.getmtime, reverse=True)
                    if candidates:
                        downloaded_path = candidates[0]
                    else:
                        raise FileNotFoundError(f"Arquivo baixado não foi encontrado em: {output_dir}")

            if duration == 0.0:
                duration = AudioProcessor.get_duration(downloaded_path)

            return downloaded_path, title, duration

    @staticmethod
    def prepare_audio_for_analysis(input_path: Path, output_dir: Path) -> Tuple[Path, float, str]:
        """
        Garante que o arquivo de entrada seja processado para um áudio otimizado (MP3/OGG).
        Se for vídeo, extrai a trilha de som sem tocar no vídeo original.
        Retorna (caminho_do_audio, duracao_segundos, mime_type).
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        ext = input_path.suffix.lower()

        base_name = input_path.stem
        target_audio_path = output_dir / f"{base_name}_extracted.mp3"

        is_video = ext in VIDEO_EXTENSIONS
        needs_conversion = is_video or (ext not in {".mp3", ".ogg", ".wav"})

        if needs_conversion or not target_audio_path.exists():
            cmd = [
                "ffmpeg",
                "-y",
                "-i", str(input_path),
                "-vn",
                "-acodec", "libmp3lame",
                "-ab", "128k",
                "-ar", "44100",
                str(target_audio_path)
            ]
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")
            if process.returncode != 0:
                if ext in AUDIO_EXTENSIONS:
                    target_audio_path = input_path
                else:
                    raise RuntimeError(f"Falha ao extrair áudio do arquivo: {process.stderr}")

        duration = AudioProcessor.get_duration(target_audio_path)
        mime_type = "audio/mp3" if target_audio_path.suffix.lower() == ".mp3" else "audio/ogg"

        return target_audio_path, duration, mime_type

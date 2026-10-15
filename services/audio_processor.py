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
    """Gerencia extração e normalização de áudio para legendagem descritiva."""

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
            # Busca 'Duration: 00:00:48.55'
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
    def prepare_audio_for_analysis(input_path: Path, output_dir: Path) -> Tuple[Path, float, str]:
        """
        Garante que o arquivo de entrada seja processado para um áudio otimizado (MP3/OGG).
        Se for vídeo, extrai a trilha de som.
        Se for áudio incompatível, converte para MP3 44.1kHz / 128k estéreo.
        Retorna (caminho_do_audio, duracao_segundos, mime_type).
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        ext = input_path.suffix.lower()

        base_name = input_path.stem
        target_audio_path = output_dir / f"{base_name}_extracted.mp3"

        # Se já é um arquivo de áudio leve e suportado diretamente, podemos usar ou converter
        is_video = ext in VIDEO_EXTENSIONS
        needs_conversion = is_video or (ext not in {".mp3", ".ogg", ".wav"})

        if needs_conversion or not target_audio_path.exists():
            # Executa FFmpeg para extrair áudio preservando dinâmica acústica
            cmd = [
                "ffmpeg",
                "-y",  # overwrite
                "-i", str(input_path),
                "-vn",  # no video
                "-acodec", "libmp3lame",
                "-ab", "128k",
                "-ar", "44100",
                str(target_audio_path)
            ]
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")
            if process.returncode != 0:
                # Se falhar a conversão direta, tenta manter cópia se for áudio
                if ext in AUDIO_EXTENSIONS:
                    target_audio_path = input_path
                else:
                    raise RuntimeError(f"Falha ao extrair áudio do arquivo: {process.stderr}")

        duration = AudioProcessor.get_duration(target_audio_path)
        mime_type = "audio/mp3" if target_audio_path.suffix.lower() == ".mp3" else "audio/ogg"

        return target_audio_path, duration, mime_type

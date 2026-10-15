"""
Gerenciador de Fila e Processamento em Lote para a Sonar.
Permite enfileirar dezenas de curtas-metragens para o festival e processar de forma assíncrona.
"""

import os
import uuid
import time
import zipfile
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

from services.audio_processor import AudioProcessor
from services.gemini_engine import GeminiLSEEngine
from services.config_manager import get_gemini_api_key, get_default_model
from services.srt_formatter import entries_to_srt, entries_to_vtt, parse_srt_to_entries


class JobManager:
    """Gerencia a fila de trabalhos, estados e persistência de arquivos SRT."""

    def __init__(self, upload_dir: Path, output_dir: Path):
        self.upload_dir = upload_dir
        self.output_dir = output_dir
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def create_job(
        self,
        filename: str,
        saved_file_path: Path,
        mode: str = "foley_only",
        detail_level: str = "high",
        language: str = "pt-br",
        custom_api_key: Optional[str] = None,
        custom_model: Optional[str] = None
    ) -> str:
        """Cria um novo trabalho de processamento de filme/áudio."""
        job_id = str(uuid.uuid4())[:8]

        with self.lock:
            self.jobs[job_id] = {
                "id": job_id,
                "filename": filename,
                "original_path": str(saved_file_path),
                "audio_path": None,
                "duration": 0.0,
                "status": "queued",  # queued, extracting_audio, analyzing_ai, completed, error
                "progress": 5,
                "status_message": "Aguardando na fila...",
                "mode": mode,
                "detail_level": detail_level,
                "language": language,
                "custom_api_key": custom_api_key,
                "custom_model": custom_model,
                "srt_content": "",
                "vtt_content": "",
                "entries": [],
                "error_message": "",
                "created_at": time.time(),
                "completed_at": None
            }

        # Dispara thread assíncrona de processamento
        thread = threading.Thread(target=self._process_job_worker, args=(job_id,), daemon=True)
        thread.start()

        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retorna o estado de um trabalho específico."""
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            return dict(job)

    def list_jobs(self) -> List[Dict[str, Any]]:
        """Retorna a lista de todos os trabalhos ordenados pelo mais recente."""
        with self.lock:
            job_list = list(self.jobs.values())
            job_list.sort(key=lambda x: x["created_at"], reverse=True)
            return job_list

    def update_job_entries(self, job_id: str, new_entries: List[Dict[str, Any]]) -> bool:
        """Permite que o usuário edite o texto ou timestamps das legendas diretamente na interface."""
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False

            new_srt = entries_to_srt(new_entries)
            new_vtt = entries_to_vtt(new_entries)

            job["entries"] = new_entries
            job["srt_content"] = new_srt
            job["vtt_content"] = new_vtt

            # Atualiza o arquivo físico em disco se já existia
            srt_path = self.output_dir / f"{Path(job['filename']).stem}.srt"
            srt_path.write_text(new_srt, encoding="utf-8")

            return True

    def create_batch_zip(self) -> Optional[Path]:
        """Gera um arquivo ZIP com todas as legendas .SRT concluídas."""
        with self.lock:
            completed_jobs = [j for j in self.jobs.values() if j["status"] == "completed" and j["srt_content"]]

        if not completed_jobs:
            return None

        zip_path = self.output_dir / "Sonar_Legendas_LSE_Animage_Lote.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for j in completed_jobs:
                base_name = Path(j["filename"]).stem
                srt_filename = f"{base_name}.srt"
                zip_file.writestr(srt_filename, j["srt_content"].encode("utf-8"))

        return zip_path

    def _process_job_worker(self, job_id: str):
        """Worker que executa a esteira de processamento do áudio/vídeo."""
        try:
            with self.lock:
                job = self.jobs[job_id]
                original_path = Path(job["original_path"])
                mode = job["mode"]
                detail_level = job["detail_level"]
                language = job["language"]
                api_key = job.get("custom_api_key") or get_gemini_api_key()
                model_name = job.get("custom_model") or get_default_model()

            if not api_key:
                raise ValueError("Chave de API do Google Gemini não configurada. Por favor cadastre sua chave nas configurações.")

            # Passo 1: Extração e normalização do áudio com FFmpeg
            with self.lock:
                self.jobs[job_id]["status"] = "extracting_audio"
                self.jobs[job_id]["status_message"] = "Extraindo e normalizando áudio via FFmpeg..."
                self.jobs[job_id]["progress"] = 25

            audio_path, duration, mime_type = AudioProcessor.prepare_audio_for_analysis(
                original_path,
                self.upload_dir
            )

            with self.lock:
                self.jobs[job_id]["audio_path"] = str(audio_path)
                self.jobs[job_id]["duration"] = duration
                self.jobs[job_id]["status"] = "analyzing_ai"
                self.jobs[job_id]["status_message"] = f"Analisando sonoplastia e foley com IA ({model_name})..."
                self.jobs[job_id]["progress"] = 50

            # Passo 2: Análise acústica com o Google Gemini
            engine = GeminiLSEEngine(api_key=api_key, model_name=model_name)
            result = engine.generate_lse_subtitles(
                audio_path=audio_path,
                mode=mode,
                detail_level=detail_level,
                language=language
            )

            srt_content = result["srt_content"]
            entries = result["entries"]
            vtt_content = entries_to_vtt(entries)

            # Salva o arquivo .srt no diretório de outputs
            base_name = original_path.stem
            srt_output_file = self.output_dir / f"{base_name}.srt"
            srt_output_file.write_text(srt_content, encoding="utf-8")

            # Salva também cópia .vtt para uso web
            vtt_output_file = self.output_dir / f"{base_name}.vtt"
            vtt_output_file.write_text(vtt_content, encoding="utf-8")

            with self.lock:
                self.jobs[job_id]["status"] = "completed"
                self.jobs[job_id]["status_message"] = f"Concluído com sucesso! ({len(entries)} eventos de som detectados)"
                self.jobs[job_id]["progress"] = 100
                self.jobs[job_id]["srt_content"] = srt_content
                self.jobs[job_id]["vtt_content"] = vtt_content
                self.jobs[job_id]["entries"] = entries
                self.jobs[job_id]["completed_at"] = time.time()

        except Exception as e:
            err_msg = str(e)
            with self.lock:
                self.jobs[job_id]["status"] = "error"
                self.jobs[job_id]["status_message"] = f"Erro no processamento: {err_msg}"
                self.jobs[job_id]["error_message"] = err_msg
                self.jobs[job_id]["progress"] = 100

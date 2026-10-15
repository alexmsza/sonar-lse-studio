import os
import uuid
import time
import zipfile
import threading
import copy
from pathlib import Path
from typing import Dict, Any, List, Optional

from services.audio_processor import AudioProcessor
from services.gemini_engine import GeminiLSEEngine
from services.config_manager import get_gemini_api_key, get_default_model
from services.srt_formatter import (
    entries_to_srt,
    entries_to_vtt,
    parse_srt_to_entries,
    entries_to_technical_script
)


class JobManager:
    """
    Gerencia a fila de trabalhos, estados, persistência, streaming de URLs e versionamento de legendas.
    """

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
        """Cria um novo trabalho a partir de arquivo local (vídeo ou áudio)."""
        job_id = str(uuid.uuid4())[:8]
        is_video = AudioProcessor.is_video_file(saved_file_path)

        with self.lock:
            self.jobs[job_id] = {
                "id": job_id,
                "source_type": "file",
                "source_url": None,
                "filename": filename,
                "original_path": str(saved_file_path),
                "is_video": is_video,
                "audio_path": None,
                "duration": 0.0,
                "status": "queued",  # queued, downloading_url, extracting_audio, analyzing_ai, completed, error
                "progress": 5,
                "status_message": "Aguardando na fila da Sonar...",
                "mode": mode,
                "detail_level": detail_level,
                "language": language,
                "custom_api_key": custom_api_key,
                "custom_model": custom_model,
                "srt_content": "",
                "vtt_content": "",
                "entries": [],
                "history": [],  # Snapshots de revisões [{revision_id, timestamp, description, entries}]
                "current_revision_id": None,
                "error_message": "",
                "created_at": time.time(),
                "completed_at": None
            }

        thread = threading.Thread(target=self._process_job_worker, args=(job_id,), daemon=True)
        thread.start()
        return job_id

    def create_job_from_url(
        self,
        url: str,
        mode: str = "foley_only",
        detail_level: str = "high",
        language: str = "pt-br",
        custom_api_key: Optional[str] = None,
        custom_model: Optional[str] = None
    ) -> str:
        """Cria um novo trabalho a partir de link de streaming web (YouTube, Vimeo, MP4 direto)."""
        job_id = str(uuid.uuid4())[:8]

        with self.lock:
            self.jobs[job_id] = {
                "id": job_id,
                "source_type": "url",
                "source_url": url,
                "filename": "Baixando vídeo via streaming...",
                "original_path": None,
                "is_video": True,
                "audio_path": None,
                "duration": 0.0,
                "status": "downloading_url",
                "progress": 10,
                "status_message": f"Conectando ao stream: {url[:45]}...",
                "mode": mode,
                "detail_level": detail_level,
                "language": language,
                "custom_api_key": custom_api_key,
                "custom_model": custom_model,
                "srt_content": "",
                "vtt_content": "",
                "entries": [],
                "history": [],
                "current_revision_id": None,
                "error_message": "",
                "created_at": time.time(),
                "completed_at": None
            }

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

    def update_job_entries(self, job_id: str, new_entries: List[Dict[str, Any]], description: str = "Edição manual") -> bool:
        """
        Atualiza as legendas e registra um novo snapshot imutável no histórico de versões (Undo/Redo).
        """
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False

            new_srt = entries_to_srt(new_entries)
            new_vtt = entries_to_vtt(new_entries)

            job["entries"] = new_entries
            job["srt_content"] = new_srt
            job["vtt_content"] = new_vtt

            # Registra versão no histórico
            rev_num = len(job["history"]) + 1
            rev_id = f"v{rev_num}"
            snapshot = {
                "revision_id": rev_id,
                "timestamp": time.time(),
                "description": description,
                "entry_count": len(new_entries),
                "entries": copy.deepcopy(new_entries),
                "srt_content": new_srt
            }
            job["history"].append(snapshot)
            job["current_revision_id"] = rev_id

            # Atualiza arquivos físicos
            if job.get("filename"):
                stem = Path(job["filename"]).stem
                srt_path = self.output_dir / f"{stem}.srt"
                srt_path.write_text(new_srt, encoding="utf-8")
                vtt_path = self.output_dir / f"{stem}.vtt"
                vtt_path.write_text(new_vtt, encoding="utf-8")

            return True

    def rollback_job_version(self, job_id: str, target_revision_id: str) -> Optional[Dict[str, Any]]:
        """
        Restaura o trabalho para qualquer snapshot anterior no histórico.
        """
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return None

            target_snap = None
            for snap in job["history"]:
                if snap["revision_id"] == target_revision_id:
                    target_snap = snap
                    break

            if not target_snap:
                return None

            restored_entries = copy.deepcopy(target_snap["entries"])
            new_srt = target_snap["srt_content"]
            new_vtt = entries_to_vtt(restored_entries)

            job["entries"] = restored_entries
            job["srt_content"] = new_srt
            job["vtt_content"] = new_vtt
            job["current_revision_id"] = target_revision_id

            # Adiciona registro de auditoria no histórico
            audit_rev_num = len(job["history"]) + 1
            audit_id = f"v{audit_rev_num}"
            job["history"].append({
                "revision_id": audit_id,
                "timestamp": time.time(),
                "description": f"Restaurado para {target_revision_id} ({target_snap['description']})",
                "entry_count": len(restored_entries),
                "entries": copy.deepcopy(restored_entries),
                "srt_content": new_srt
            })
            job["current_revision_id"] = audit_id

            # Atualiza em disco
            if job.get("filename"):
                stem = Path(job["filename"]).stem
                (self.output_dir / f"{stem}.srt").write_text(new_srt, encoding="utf-8")
                (self.output_dir / f"{stem}.vtt").write_text(new_vtt, encoding="utf-8")

            return {
                "success": True,
                "active_revision": audit_id,
                "entries": restored_entries,
                "srt_content": new_srt
            }

    def get_job_history(self, job_id: str) -> List[Dict[str, Any]]:
        """Retorna a lista resumida de histórico de versões para o painel de Undo/Rollback."""
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return []
            history_summary = []
            for h in job.get("history", []):
                history_summary.append({
                    "revision_id": h["revision_id"],
                    "timestamp": h["timestamp"],
                    "description": h["description"],
                    "entry_count": h["entry_count"]
                })
            return history_summary

    def get_technical_script(self, job_id: str, fps: float = 24.0) -> Optional[str]:
        """Gera o Roteiro Técnico de Metragem Audiovisual (SMPTE) para a obra."""
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or not job.get("entries"):
                return None
            title = Path(job.get("filename", "Filme")).stem
            return entries_to_technical_script(job["entries"], title=title, fps=fps, mode=job.get("mode", "lse"))

    def create_batch_zip(self) -> Optional[Path]:
        """Gera um arquivo ZIP com todas as legendas .SRT e roteiros técnicos concluídos."""
        with self.lock:
            completed_jobs = [j for j in self.jobs.values() if j["status"] == "completed" and j["srt_content"]]

        if not completed_jobs:
            return None

        zip_path = self.output_dir / "Sonar_Legendas_LSE_Animage_Lote.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for j in completed_jobs:
                base_name = Path(j["filename"]).stem
                # Salva SRT
                zip_file.writestr(f"{base_name}.srt", j["srt_content"].encode("utf-8"))
                # Salva Roteiro Técnico SMPTE
                script = entries_to_technical_script(j["entries"], title=base_name, fps=24.0, mode=j.get("mode", "lse"))
                zip_file.writestr(f"{base_name}_Roteiro_Metragem_SMPTE.txt", script.encode("utf-8"))

        return zip_path

    def _process_job_worker(self, job_id: str):
        """Worker assíncrono que processa o fluxo completo."""
        try:
            with self.lock:
                job = self.jobs[job_id]
                source_type = job["source_type"]
                mode = job["mode"]
                detail_level = job["detail_level"]
                language = job["language"]
                api_key = job.get("custom_api_key") or get_gemini_api_key()
                model_name = job.get("custom_model") or get_default_model()

            if not api_key:
                raise ValueError("Chave de API do Google Gemini não configurada. Por favor cadastre sua chave nas configurações.")

            # Se a origem for URL de streaming (YouTube, Vimeo, MP4 remoto)
            if source_type == "url":
                with self.lock:
                    self.jobs[job_id]["status"] = "downloading_url"
                    self.jobs[job_id]["status_message"] = "Baixando vídeo e extraindo fluxo com yt-dlp..."
                    self.jobs[job_id]["progress"] = 15

                downloaded_file, title, duration = AudioProcessor.download_media_from_url(
                    job["source_url"],
                    self.upload_dir
                )

                with self.lock:
                    self.jobs[job_id]["filename"] = f"{title}.mp4"
                    self.jobs[job_id]["original_path"] = str(downloaded_file)
                    self.jobs[job_id]["is_video"] = AudioProcessor.is_video_file(downloaded_file)
                    self.jobs[job_id]["duration"] = duration

            with self.lock:
                original_path = Path(self.jobs[job_id]["original_path"])

            # Extração de áudio via FFmpeg
            with self.lock:
                self.jobs[job_id]["status"] = "extracting_audio"
                self.jobs[job_id]["status_message"] = "Extraindo e normalizando áudio via FFmpeg..."
                self.jobs[job_id]["progress"] = 35

            audio_path, duration, mime_type = AudioProcessor.prepare_audio_for_analysis(
                original_path,
                self.upload_dir
            )

            with self.lock:
                self.jobs[job_id]["audio_path"] = str(audio_path)
                if not self.jobs[job_id].get("duration") or self.jobs[job_id]["duration"] == 0:
                    self.jobs[job_id]["duration"] = duration
                self.jobs[job_id]["status"] = "analyzing_ai"
                if mode == "audiodescricao":
                    self.jobs[job_id]["status_message"] = f"Roteirizando Audiodescrição (AD) com IA ({model_name})..."
                else:
                    self.jobs[job_id]["status_message"] = f"Analisando sonoplastia e foley com IA ({model_name})..."
                self.jobs[job_id]["progress"] = 60

            # Análise acústica com Google Gemini
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

            # Salva arquivos físicos
            base_name = original_path.stem
            (self.output_dir / f"{base_name}.srt").write_text(srt_content, encoding="utf-8")
            (self.output_dir / f"{base_name}.vtt").write_text(vtt_content, encoding="utf-8")

            # Cria Snapshot v1 no histórico
            initial_snapshot = {
                "revision_id": "v1",
                "timestamp": time.time(),
                "description": f"Análise inicial por IA ({mode.upper()})",
                "entry_count": len(entries),
                "entries": copy.deepcopy(entries),
                "srt_content": srt_content
            }

            with self.lock:
                self.jobs[job_id]["status"] = "completed"
                desc_label = "audiodescrições" if mode == "audiodescricao" else "sons detectados"
                self.jobs[job_id]["status_message"] = f"Concluído com sucesso! ({len(entries)} {desc_label})"
                self.jobs[job_id]["progress"] = 100
                self.jobs[job_id]["srt_content"] = srt_content
                self.jobs[job_id]["vtt_content"] = vtt_content
                self.jobs[job_id]["entries"] = entries
                self.jobs[job_id]["history"] = [initial_snapshot]
                self.jobs[job_id]["current_revision_id"] = "v1"
                self.jobs[job_id]["completed_at"] = time.time()

        except Exception as e:
            err_msg = str(e)
            with self.lock:
                self.jobs[job_id]["status"] = "error"
                self.jobs[job_id]["status_message"] = f"Erro no processamento: {err_msg}"
                self.jobs[job_id]["error_message"] = err_msg
                self.jobs[job_id]["progress"] = 100


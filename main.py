"""
Servidor Principal da Sonar LSE Studio (FastAPI).
Plataforma de Legendagem Descritiva de Foley, Sonoplastia e Acessibilidade para Cinema e Festivais.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.config_manager import (
    get_gemini_api_key,
    get_default_model,
    save_api_config,
    test_gemini_connection
)
from services.job_manager import JobManager

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
STATIC_DIR = BASE_DIR / "static"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Sonar LSE Studio",
    description="Sistema de Legendagem Descritiva de Sonoplastia, Ruídos e Foley para o Festival Animage",
    version="1.0.0"
)

# CORS liberado para integração local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

job_manager = JobManager(upload_dir=UPLOAD_DIR, output_dir=OUTPUT_DIR)


# Schemas
class ConfigRequest(BaseModel):
    gemini_api_key: str
    gemini_model: Optional[str] = "gemini-2.5-flash"


class UpdateEntriesRequest(BaseModel):
    entries: List[dict]


# Rotas de Configuração
@app.get("/api/config")
def get_config():
    """Retorna o status da configuração da API da Sonar."""
    key = get_gemini_api_key()
    masked_key = ""
    if key:
        if len(key) > 8:
            masked_key = f"{key[:4]}...{key[-4:]}"
        else:
            masked_key = "***"

    return {
        "gemini_configured": bool(key),
        "gemini_key_masked": masked_key,
        "gemini_model": get_default_model()
    }


@app.post("/api/config")
def update_config(req: ConfigRequest):
    """Atualiza e salva as credenciais da API em .env."""
    success = save_api_config(req.gemini_api_key, req.gemini_model or "gemini-2.5-flash")
    if not success:
        raise HTTPException(status_code=500, detail="Erro ao salvar configurações no servidor.")
    return {"success": True, "message": "Configurações salvas com sucesso!"}


@app.post("/api/config/test")
def test_config(req: ConfigRequest):
    """Testa a conectividade da chave fornecida com a Google Gemini API."""
    result = test_gemini_connection(req.gemini_api_key, req.gemini_model or "gemini-2.5-flash")
    return result


# Rotas de Upload e Processamento
@app.post("/api/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    mode: str = Form("foley_only"),
    detail_level: str = Form("high"),
    language: str = Form("pt-br"),
    custom_api_key: Optional[str] = Form(None),
    custom_model: Optional[str] = Form(None)
):
    """
    Recebe um ou múltiplos arquivos de filme/áudio, enfileira e inicia o processamento.
    """
    api_key_to_use = custom_api_key or get_gemini_api_key()
    if not api_key_to_use:
        raise HTTPException(
            status_code=400,
            detail="Chave de API do Google Gemini não configurada. Por favor acesse as Configurações e cadastre sua chave."
        )

    job_ids = []
    for upload in files:
        safe_filename = upload.filename.replace(" ", "_")
        dest_path = UPLOAD_DIR / f"{safe_filename}"

        # Se já existir arquivo com mesmo nome, prefixa com timestamp
        if dest_path.exists():
            dest_path = UPLOAD_DIR / f"{int(time.time())}_{safe_filename}"

        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)

        job_id = job_manager.create_job(
            filename=upload.filename,
            saved_file_path=dest_path,
            mode=mode,
            detail_level=detail_level,
            language=language,
            custom_api_key=api_key_to_use,
            custom_model=custom_model
        )
        job_ids.append(job_id)

    return {
        "success": True,
        "message": f"{len(job_ids)} arquivo(s) adicionado(s) à fila de processamento da Sonar.",
        "job_ids": job_ids
    }


@app.get("/api/jobs")
def list_jobs():
    """Retorna todos os trabalhos de legendagem."""
    return {"jobs": job_manager.list_jobs()}


@app.get("/api/jobs/{job_id}")
def get_job_detail(job_id: str):
    """Retorna detalhes de um trabalho específico."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Trabalho não encontrado.")
    return job


@app.put("/api/jobs/{job_id}/entries")
def update_entries(job_id: str, req: UpdateEntriesRequest):
    """Atualiza as legendas de um trabalho após edição do usuário."""
    success = job_manager.update_job_entries(job_id, req.entries)
    if not success:
        raise HTTPException(status_code=404, detail="Trabalho não encontrado ou erro ao atualizar.")
    return {"success": True, "message": "Legendas atualizadas com sucesso!"}


# Rotas de Mídia e Download
@app.get("/api/media/{job_id}")
def stream_media(job_id: str):
    """Disponibiliza o fluxo de áudio para o player nativo do navegador."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Trabalho não encontrado.")

    # Se o áudio já foi extraído, usa o áudio extraído (mais leve para streaming)
    media_path = None
    if job.get("audio_path") and Path(job["audio_path"]).exists():
        media_path = Path(job["audio_path"])
    elif job.get("original_path") and Path(job["original_path"]).exists():
        media_path = Path(job["original_path"])

    if not media_path or not media_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de mídia não encontrado em disco.")

    suffix = media_path.suffix.lower()
    media_type = "audio/mpeg" if suffix == ".mp3" else ("audio/ogg" if suffix == ".ogg" else "video/mp4")

    return FileResponse(path=str(media_path), media_type=media_type, filename=media_path.name)


@app.get("/api/jobs/{job_id}/download-srt")
def download_srt(job_id: str):
    """Faz o download do arquivo .SRT daquele filme."""
    job = job_manager.get_job(job_id)
    if not job or not job.get("srt_content"):
        raise HTTPException(status_code=404, detail="Legenda não disponível para este trabalho.")

    filename_base = Path(job["filename"]).stem
    srt_filename = f"{filename_base}_LSE_Sonar.srt"
    srt_path = OUTPUT_DIR / f"{Path(job['filename']).stem}.srt"

    if srt_path.exists():
        return FileResponse(path=str(srt_path), filename=srt_filename, media_type="text/plain; charset=utf-8")

    # Retorna dinâmico se arquivo não estiver em disco
    return StreamingResponse(
        iter([job["srt_content"].encode("utf-8")]),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{srt_filename}"'}
    )


@app.get("/api/jobs/{job_id}/download-vtt")
def download_vtt(job_id: str):
    """Faz o download do arquivo .VTT para exibição web."""
    job = job_manager.get_job(job_id)
    if not job or not job.get("vtt_content"):
        raise HTTPException(status_code=404, detail="Legenda VTT não disponível.")

    filename_base = Path(job["filename"]).stem
    vtt_filename = f"{filename_base}_LSE_Sonar.vtt"

    return StreamingResponse(
        iter([job["vtt_content"].encode("utf-8")]),
        media_type="text/vtt; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{vtt_filename}"'}
    )


@app.get("/api/download-all-zip")
def download_all_zip():
    """Gera e baixa um arquivo ZIP com todas as legendas concluídas da fila."""
    zip_path = job_manager.create_batch_zip()
    if not zip_path or not zip_path.exists():
        raise HTTPException(status_code=400, detail="Nenhuma legenda concluída disponível para empacotar em lote.")

    return FileResponse(
        path=str(zip_path),
        filename="Sonar_Legendas_LSE_Lote.zip",
        media_type="application/zip"
    )


# Rota da Interface Web Principal
@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return JSONResponse({"status": "Sonar LSE Studio API Ativa", "ui": "Carregando interface..."})
    return FileResponse(str(index_file))


# Monta arquivos estáticos (CSS, JS, imagens)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

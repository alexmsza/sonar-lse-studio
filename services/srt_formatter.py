"""
Formatador, Validador e Parser de Legendas SRT / VTT para a Sonar.
Garante estrita conformidade com os padrões de exibição e acessibilidade ABNT NBR 15290.
"""

import re
from typing import List, Dict, Any, Optional


def seconds_to_srt_time(seconds: float) -> str:
    """Converte segundos float em formato SRT HH:MM:SS,mmm"""
    if seconds < 0:
        seconds = 0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        secs += 1
        millis -= 1000
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def srt_time_to_seconds(time_str: str) -> float:
    """Converte HH:MM:SS,mmm ou HH:MM:SS.mmm em segundos float."""
    clean = time_str.strip().replace(".", ",")
    parts = clean.split(":")
    if len(parts) == 3:
        h, m, rest = parts
        s, ms = rest.split(",") if "," in rest else (rest, "0")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
    elif len(parts) == 2:
        m, rest = parts
        s, ms = rest.split(",") if "," in rest else (rest, "0")
        return int(m) * 60 + int(s) + int(ms) / 1000.0
    return 0.0


def seconds_to_smpte(seconds: float, fps: float = 24.0) -> str:
    """
    Converte segundos float em timecode cinematográfico SMPTE HH:MM:SS:FF.
    Padrão para festivais de animação e cinema (24 fps), TV (25 ou 29.97 fps) ou digital (30 fps).
    """
    if seconds < 0:
        seconds = 0.0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    remainder = seconds - int(seconds)
    frame = int(round(remainder * fps))
    if frame >= int(fps):
        secs += 1
        frame = 0
    if secs >= 60:
        mins += 1
        secs = 0
    if mins >= 60:
        hrs += 1
        mins = 0
    return f"{hrs:02d}:{mins:02d}:{secs:02d}:{frame:02d}"


def smpte_to_seconds(smpte_str: str, fps: float = 24.0) -> float:
    """Converte SMPTE HH:MM:SS:FF em segundos float."""
    clean = smpte_str.strip()
    parts = clean.split(":")
    if len(parts) == 4:
        h, m, s, f = parts
        return int(h) * 3600 + int(m) * 60 + int(s) + (int(f) / fps)
    return srt_time_to_seconds(clean)


def clean_llm_srt_output(raw_text: str) -> str:
    """Remove blocos de código markdown ou saudações da resposta da IA."""
    text = raw_text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n```$", "", text, flags=re.MULTILINE)
    text = text.replace("```", "").strip()

    match = re.search(r"(\b1\s*\n\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->)", text)
    if match:
        text = text[match.start():]

    return text.strip()


def parse_srt_to_entries(srt_content: str, fps: float = 24.0) -> List[Dict[str, Any]]:
    """
    Analisa uma string SRT e converte em lista de dicionários estruturados,
    incluindo metadados de timecode SMPTE e metragem precisa.
    """
    clean_text = clean_llm_srt_output(srt_content)
    blocks = re.split(r"\n\s*\n", clean_text.strip())
    entries = []

    sub_index = 1
    for block in blocks:
        lines = [line.strip() for line in block.strip().split("\n") if line.strip()]
        if not lines:
            continue

        time_line_idx = -1
        for idx, line in enumerate(lines):
            if "-->" in line:
                time_line_idx = idx
                break

        if time_line_idx == -1:
            continue

        time_part = lines[time_line_idx]
        parts = time_part.split("-->")
        if len(parts) != 2:
            continue

        start_str = parts[0].strip()
        end_str = parts[1].strip()

        text_lines = lines[time_line_idx + 1:]
        sub_text = " ".join(text_lines).strip()
        if not sub_text:
            continue

        start_sec = srt_time_to_seconds(start_str)
        end_sec = srt_time_to_seconds(end_str)

        if end_sec <= start_sec:
            end_sec = start_sec + 2.0

        formatted_text = sub_text
        if not (formatted_text.startswith("[") or formatted_text.startswith("(") or formatted_text.startswith("-")):
            formatted_text = f"[{formatted_text}]"

        entries.append({
            "id": sub_index,
            "start": seconds_to_srt_time(start_sec),
            "end": seconds_to_srt_time(end_sec),
            "start_seconds": round(start_sec, 3),
            "end_seconds": round(end_sec, 3),
            "smpte_start": seconds_to_smpte(start_sec, fps),
            "smpte_end": seconds_to_smpte(end_sec, fps),
            "duration": round(end_sec - start_sec, 2),
            "text": formatted_text
        })
        sub_index += 1

    return entries


def entries_to_srt(entries: List[Dict[str, Any]]) -> str:
    """Converte lista de entradas de legenda no formato padrão .SRT."""
    lines = []
    for idx, item in enumerate(entries, start=1):
        lines.append(str(idx))
        start_time = item.get("start") or seconds_to_srt_time(item.get("start_seconds", 0))
        end_time = item.get("end") or seconds_to_srt_time(item.get("end_seconds", 0))
        lines.append(f"{start_time} --> {end_time}")
        lines.append(item.get("text", "").strip())
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def entries_to_vtt(entries: List[Dict[str, Any]]) -> str:
    """Converte lista de entradas de legenda no formato .VTT para exibição web nativa."""
    lines = ["WEBVTT", ""]
    for idx, item in enumerate(entries, start=1):
        lines.append(str(idx))
        start_time = (item.get("start") or seconds_to_srt_time(item.get("start_seconds", 0))).replace(",", ".")
        end_time = (item.get("end") or seconds_to_srt_time(item.get("end_seconds", 0))).replace(",", ".")
        lines.append(f"{start_time} --> {end_time}")
        lines.append(item.get("text", "").strip())
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def entries_to_technical_script(entries: List[Dict[str, Any]], title: str = "Filme", fps: float = 24.0, mode: str = "lse") -> str:
    """
    Gera um Roteiro Técnico de Metragem Audiovisual (Padrão ANCINE / Festivais / TV / Cinema).
    Exporta tabela legível com Minutagem Exata, SMPTE Timecode e Roteiro de Locução/Sonoplastia.
    """
    header_type = "AUDIODESCRIÇÃO (AD)" if "audio" in mode.lower() else "LEGENDAGEM DESCRITIVA (LSE / FOLEY)"
    doc_lines = [
        "=" * 80,
        f"SONAR ACESSIBILIDADE AUDIOVISUAL — ROTEIRO TÉCNICO DE {header_type}",
        f"Obra: {title}",
        f"Timecode Base: SMPTE @ {fps:.2f} fps (Metragem Exata de Cinema / TV)",
        f"Conformidade: ABNT NBR 15290 (LSE) / ABNT NBR 16452 (Audiodescrição)",
        "=" * 80,
        "",
        f"{'#':<4} | {'INÍCIO (SRT)':<12} | {'FIM (SRT)':<12} | {'SMPTE TC (24fps)':<16} | {'DUR':<5} | DESCRIÇÃO / ROTEIRO",
        "-" * 80
    ]

    for item in entries:
        idx = item.get("id", 1)
        srt_s = item.get("start", "00:00:00,000")
        srt_e = item.get("end", "00:00:00,000")
        smpte_s = item.get("smpte_start") or seconds_to_smpte(item.get("start_seconds", 0), fps)
        smpte_e = item.get("smpte_end") or seconds_to_smpte(item.get("end_seconds", 0), fps)
        tc_display = f"{smpte_s} - {smpte_e}"
        dur = f"{item.get('duration', 0.0):.1f}s"
        txt = item.get("text", "")
        doc_lines.append(f"{idx:<4} | {srt_s:<12} | {srt_e:<12} | {tc_display:<16} | {dur:<5} | {txt}")

    doc_lines.append("")
    doc_lines.append("=" * 80)
    doc_lines.append("Gerado automaticamente por SONAR LSE Studio — Tecnologia Asza Company")
    doc_lines.append("=" * 80)

    return "\n".join(doc_lines)


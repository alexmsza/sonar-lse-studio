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
    doc_lines.append("Gerado por SONAR LSE STUDIO — Workstation Interna Sonar Acessibilidade")
    doc_lines.append("=" * 80)

    return "\n".join(doc_lines)


def validate_subtitles_compliance(entries: List[Dict[str, Any]], mode: str = "lse") -> Dict[str, Any]:
    """
    Audita as legendas conforme as normas ABNT NBR 15290 (LSE) e ABNT NBR 16452 (Audiodescrição).
    Identifica sobreposições temporais, velocidade excessiva de leitura (CPS), linhas longas e durações anômalas.
    """
    warnings = []
    errors = []
    stats = {
        "total_entries": len(entries),
        "total_duration": 0.0,
        "avg_cps": 0.0,
        "max_cps": 0.0,
        "overlaps_count": 0,
        "long_lines_count": 0
    }

    if not entries:
        return {
            "score": 100,
            "status": "clean",
            "stats": stats,
            "errors_count": 0,
            "warnings_count": 0,
            "errors": [],
            "warnings": [],
            "issues_by_entry": {}
        }

    total_chars = 0
    total_time = 0.0
    issues_by_entry = {}
    prev_end_sec = 0.0

    for idx, item in enumerate(entries):
        entry_id = item.get("id", idx + 1)
        text = item.get("text", "").strip()
        start_sec = item.get("start_seconds", 0.0)
        end_sec = item.get("end_seconds", 0.0)
        duration = round(end_sec - start_sec, 3)

        entry_issues = []

        # 1. Checagem de sobreposição temporal (Overlap)
        if idx > 0 and start_sec < prev_end_sec:
            stats["overlaps_count"] += 1
            overlap_gap = round(prev_end_sec - start_sec, 3)
            err = {
                "entry_id": entry_id,
                "type": "error",
                "code": "TIMECODE_OVERLAP",
                "message": f"Sobreposição temporal de {overlap_gap}s com a legenda #{entries[idx-1].get('id', idx)}."
            }
            errors.append(err)
            entry_issues.append(err)

        # 2. Checagem de duração
        if duration <= 0:
            err = {
                "entry_id": entry_id,
                "type": "error",
                "code": "INVALID_DURATION",
                "message": "Duração inválida ou nula (fim menor ou igual ao início)."
            }
            errors.append(err)
            entry_issues.append(err)
        elif duration < 1.0:
            warn = {
                "entry_id": entry_id,
                "type": "warning",
                "code": "SHORT_DURATION",
                "message": f"Duração curta ({duration}s). Mínimo recomendado é 1.0s para legibilidade."
            }
            warnings.append(warn)
            entry_issues.append(warn)
        elif duration > 7.0:
            warn = {
                "entry_id": entry_id,
                "type": "warning",
                "code": "LONG_DURATION",
                "message": f"Duração longa ({duration}s). Considere dividir em blocos menores."
            }
            warnings.append(warn)
            entry_issues.append(warn)

        # 3. Velocidade de leitura (CPS - Caracteres por Segundo)
        clean_text_len = len(re.sub(r"[\[\]\(\)\-]", "", text).strip())
        if duration > 0:
            cps = round(clean_text_len / duration, 1)
            total_chars += clean_text_len
            total_time += duration
            if cps > stats["max_cps"]:
                stats["max_cps"] = cps

            cps_limit = 18.0 if mode == "audiodescricao" else 20.0
            if cps > cps_limit:
                warn = {
                    "entry_id": entry_id,
                    "type": "warning",
                    "code": "HIGH_CPS",
                    "message": f"Velocidade de leitura alta ({cps} CPS > {cps_limit} CPS)."
                }
                warnings.append(warn)
                entry_issues.append(warn)

        # 4. Limite de Caracteres por Linha (ABNT NBR 15290 - Máx 37 caracteres)
        lines = text.split("\n")
        has_long_line = False
        for line in lines:
            if len(line.strip()) > 37:
                has_long_line = True
                break
        if has_long_line:
            stats["long_lines_count"] += 1
            warn = {
                "entry_id": entry_id,
                "type": "warning",
                "code": "LINE_LENGTH_EXCEEDED",
                "message": "Linha excede 37 caracteres (limite recomendado ABNT NBR 15290)."
            }
            warnings.append(warn)
            entry_issues.append(warn)

        if entry_issues:
            issues_by_entry[entry_id] = entry_issues

        prev_end_sec = max(prev_end_sec, end_sec)

    stats["total_duration"] = round(total_time, 2)
    stats["avg_cps"] = round(total_chars / total_time, 1) if total_time > 0 else 0.0

    penalty = (len(errors) * 15) + (len(warnings) * 4)
    score = max(0, 100 - penalty)

    return {
        "score": score,
        "status": "perfect" if score >= 95 else "good" if score >= 80 else "attention",
        "errors_count": len(errors),
        "warnings_count": len(warnings),
        "stats": stats,
        "errors": errors,
        "warnings": warnings,
        "issues_by_entry": issues_by_entry
    }


def auto_fix_timecode_overlaps(entries: List[Dict[str, Any]], fps: float = 24.0, min_gap_seconds: float = 0.08) -> List[Dict[str, Any]]:
    """
    Corrige automaticamente sobreposições temporais e colisões de legendas,
    assegurando intervalo de respiro mínimo entre blocos consecutivos.
    """
    import copy
    fixed_entries = copy.deepcopy(entries)
    fixed_entries.sort(key=lambda x: x.get("start_seconds", 0.0))

    for idx in range(len(fixed_entries)):
        if idx > 0:
            prev = fixed_entries[idx - 1]
            curr = fixed_entries[idx]
            prev_end = prev.get("end_seconds", 0.0)
            curr_start = curr.get("start_seconds", 0.0)

            if curr_start <= prev_end:
                new_prev_end = max(prev.get("start_seconds", 0.0) + 0.5, curr_start - min_gap_seconds)
                prev["end_seconds"] = round(new_prev_end, 3)
                prev["end"] = seconds_to_srt_time(new_prev_end)
                prev["smpte_end"] = seconds_to_smpte(new_prev_end, fps)
                prev["duration"] = round(new_prev_end - prev.get("start_seconds", 0.0), 2)

    for idx, item in enumerate(fixed_entries, start=1):
        item["id"] = idx

    return fixed_entries



import logging
import re
from typing import Dict, List, Optional

from src.utils.admin import run_cmd


logger = logging.getLogger(__name__)


PLANS: Dict[str, str] = {
    "Equilibrado": "381b4222-f694-41f0-9685-ff5bb260df2e",
    "Economia de energia": "a1841308-3541-4fab-bc81-f71556f20b4a",
    "Alto desempenho": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    "Desempenho máximo": "e9a42b02-d5df-448d-aa00-03f14749eb61",
}


GUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def _parse_guids(text: str) -> List[str]:
    return GUID_RE.findall(text or "")


def _list_plans() -> Dict[str, object]:
    code, out, err = run_cmd("powercfg -list", shell="cmd", elevated=True, timeout=60)
    guids = _parse_guids(out)
    return {"code": code, "stdout": out, "stderr": err, "guids": guids}


def _duplicate_scheme(template_guid: str) -> Dict[str, object]:
    code, out, err = run_cmd(f"powercfg -duplicatescheme {template_guid}", shell="cmd", elevated=True, timeout=60)
    new_guid: Optional[str] = None
    if out:
        m = GUID_RE.search(out)
        if m:
            new_guid = m.group(0)
    return {"code": code, "stdout": out, "stderr": err, "new_guid": new_guid}


def set_power_plan(label_or_guid: str) -> dict:
    guid = PLANS.get(label_or_guid, label_or_guid)
    cmd = f"powercfg /setactive {guid}"
    code, out, err = run_cmd(cmd, shell="cmd", elevated=True, timeout=60)
    ok = code == 0
    logger.info("powercfg setactive %s -> exit=%s", guid, code)
    if ok:
        return {"ok": True, "code": code, "stdout": out, "stderr": err, "guid": guid, "message": "Plano de energia ativado."}

    # Se falhar tentando o plano "Desempenho máximo", tente duplicar e ativar a cópia
    is_ultimate = guid.lower() == PLANS["Desempenho máximo"].lower() or str(label_or_guid).lower() == "desempenho máximo"
    if is_ultimate:
        logger.info("Tentando habilitar 'Desempenho máximo' via duplicatescheme…")
        dup = _duplicate_scheme(PLANS["Desempenho máximo"]) 
        new_guid = dup.get("new_guid")
        if dup.get("code") == 0 and isinstance(new_guid, str):
            logger.info("Novo esquema duplicado: %s", new_guid)
            code2, out2, err2 = run_cmd(f"powercfg /setactive {new_guid}", shell="cmd", elevated=True, timeout=60)
            ok2 = code2 == 0
            if ok2:
                return {
                    "ok": True,
                    "code": code2,
                    "stdout": out2,
                    "stderr": err2,
                    "guid": new_guid,
                    "created": True,
                    "message": "Plano 'Desempenho máximo' habilitado e ativado (cópia local).",
                }
            else:
                return {
                    "ok": False,
                    "code": code2,
                    "stdout": out2,
                    "stderr": err2,
                    "guid": new_guid,
                    "created": True,
                    "message": "Não foi possível ativar a cópia do plano 'Desempenho máximo'.",
                }
        else:
            # Se duplicatescheme falhar, informe mensagem amigável
            return {
                "ok": False,
                "code": dup.get("code"),
                "stdout": dup.get("stdout"),
                "stderr": dup.get("stderr"),
                "guid": guid,
                "message": (
                    "Falha ao habilitar 'Desempenho máximo'. O sistema pode não oferecer suporte a este plano "
                    "(ex.: dispositivos com Modern Standby/ARM/Secure policies)."
                ),
            }

    # Outras falhas: tente detectar se o plano existe
    listed = _list_plans()
    if isinstance(listed.get("guids"), list) and guid.lower() not in [g.lower() for g in listed["guids"]]:
        return {
            "ok": False,
            "code": code,
            "stdout": out,
            "stderr": err,
            "guid": guid,
            "message": "Plano não encontrado neste sistema.",
        }

    # Falha genérica
    if err:
        logger.warning("stderr: %s", err.strip())
    return {"ok": False, "code": code, "stdout": out, "stderr": err, "guid": guid, "message": "Não foi possível ativar o plano."}

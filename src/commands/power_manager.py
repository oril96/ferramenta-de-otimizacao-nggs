import logging
from typing import Dict

from src.utils.admin import run_cmd


logger = logging.getLogger(__name__)


PLANS: Dict[str, str] = {
    "Equilibrado": "381b4222-f694-41f0-9685-ff5bb260df2e",
    "Economia de energia": "a1841308-3541-4fab-bc81-f71556f20b4a",
    "Alto desempenho": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    "Desempenho máximo": "e9a42b02-d5df-448d-aa00-03f14749eb61",
}


def set_power_plan(label_or_guid: str) -> dict:
    guid = PLANS.get(label_or_guid, label_or_guid)
    cmd = f"powercfg /setactive {guid}"
    code, out, err = run_cmd(cmd, shell="cmd", elevated=True, timeout=60)
    ok = code == 0
    logger.info("powercfg setactive %s -> exit=%s", guid, code)
    if err:
        logger.warning("stderr: %s", err.strip())
    return {"ok": ok, "code": code, "stdout": out, "stderr": err, "guid": guid}


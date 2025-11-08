import logging
import json
from typing import Callable, Any

from PyQt6 import QtCore, QtWidgets

from src.commands import network_cache, local_cache, power_manager, game_optimizer
from src.ui.strings import (
    APP_TITLE,
    SECTION_NETWORK_SYSTEM,
    SECTION_GAMES,
    SECTION_POWER,
    BTN_CLEAR_NETWORK_CACHE,
    BTN_CLEAR_LOCAL_CACHE,
    BTN_CLEAR_LOCAL_CACHE_FORCE,
    BTN_OPTIMIZE_GAMES,
    BTN_POWER_BALANCED,
    BTN_POWER_ECO,
    BTN_POWER_HIGH,
    BTN_POWER_ULTIMATE,
    POWER_PAYLOAD_BALANCED,
    POWER_PAYLOAD_ECO,
    POWER_PAYLOAD_HIGH,
    POWER_PAYLOAD_ULTIMATE,
)


logger = logging.getLogger(__name__)


class Worker(QtCore.QThread):
    finished = QtCore.pyqtSignal(object)

    def __init__(self, fn: Callable, *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as ex:  # noqa: BLE001
            result = {"ok": False, "error": str(ex)}
        self.finished.emit(result)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(820, 540)

        self.status = self.statusBar()
        self.status.showMessage("Pronto")

        central = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(12)

        # Section: Rede e Sistema
        box_rs = QtWidgets.QGroupBox(SECTION_NETWORK_SYSTEM)
        lay_rs = QtWidgets.QHBoxLayout(box_rs)
        btn_net = QtWidgets.QPushButton(BTN_CLEAR_NETWORK_CACHE)
        btn_sys = QtWidgets.QPushButton(BTN_CLEAR_LOCAL_CACHE)
        btn_sys_force = QtWidgets.QPushButton(BTN_CLEAR_LOCAL_CACHE_FORCE)
        lay_rs.addWidget(btn_net)
        lay_rs.addWidget(btn_sys)
        lay_rs.addWidget(btn_sys_force)
        layout.addWidget(box_rs)

        # Section: Jogos
        box_g = QtWidgets.QGroupBox(SECTION_GAMES)
        lay_g = QtWidgets.QHBoxLayout(box_g)
        btn_games = QtWidgets.QPushButton(BTN_OPTIMIZE_GAMES)
        lay_g.addWidget(btn_games)
        layout.addWidget(box_g)

        # Section: Energia
        box_p = QtWidgets.QGroupBox(SECTION_POWER)
        lay_p = QtWidgets.QHBoxLayout(box_p)
        btn_bal = QtWidgets.QPushButton(BTN_POWER_BALANCED)
        btn_eco = QtWidgets.QPushButton(BTN_POWER_ECO)
        btn_perf = QtWidgets.QPushButton(BTN_POWER_HIGH)
        btn_ult = QtWidgets.QPushButton(BTN_POWER_ULTIMATE)
        for b in (btn_bal, btn_eco, btn_perf, btn_ult):
            lay_p.addWidget(b)
        layout.addWidget(box_p)

        layout.addStretch(1)
        self.setCentralWidget(central)

        # Wire actions
        btn_net.clicked.connect(self._run_clear_network)
        btn_sys.clicked.connect(self._run_clear_local)
        btn_sys_force.clicked.connect(self._run_clear_local_force)
        btn_games.clicked.connect(self._run_optimize_games)
        btn_bal.clicked.connect(lambda: self._run_power(POWER_PAYLOAD_BALANCED))
        btn_eco.clicked.connect(lambda: self._run_power(POWER_PAYLOAD_ECO))
        btn_perf.clicked.connect(lambda: self._run_power(POWER_PAYLOAD_HIGH))
        btn_ult.clicked.connect(lambda: self._run_power(POWER_PAYLOAD_ULTIMATE))

    # Helpers
    def _start_worker(self, fn: Callable, *a: Any, **kw: Any) -> None:
        self.status.showMessage("Executando…")
        w = Worker(fn, *a, **kw)
        w.finished.connect(self._on_result)
        w.finished.connect(lambda _: self.status.showMessage("Concluído"))
        w.start()
        # keep reference to avoid GC
        self._last_worker = w  # type: ignore[attr-defined]

    def _on_result(self, result: object) -> None:
        logger.info("Resultado: %s", result)
        title = "Optimus Toolbox"

        def detail_text(data: object) -> str:
            try:
                return json.dumps(data, ensure_ascii=False, indent=2)
            except Exception:  # noqa: BLE001
                return str(data)

        if not isinstance(result, dict):
            m = QtWidgets.QMessageBox(self)
            m.setWindowTitle(title)
            m.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            m.setText("Falhou: resultado inesperado.")
            m.setDetailedText(detail_text(result))
            m.addButton(QtWidgets.QMessageBox.StandardButton.Ok)
            m.exec()
            return

        ok = bool(result.get("ok"))
        partial = bool(result.get("partial"))
        message = result.get("message")

        # Compact detail line quando houver contadores
        totals = result.get("totals")
        summary_line = None
        if isinstance(totals, dict):
            # cache local
            if {"removed", "locked", "failed"}.issubset(set(totals.keys())):
                summary_line = (
                    f"Resumo - removidos: {totals.get('removed', 0)}, "
                    f"bloqueados: {totals.get('locked', 0)}, "
                    f"falhas: {totals.get('failed', 0)}"
                )
            # steps (rede/jogos)
            elif {"success", "failed"}.issubset(set(totals.keys())):
                summary_line = (
                    f"Resumo - êxitos: {totals.get('success', 0)}, "
                    f"falhas: {totals.get('failed', 0)}"
                )

        text = message or ("Tarefa executada com sucesso." if ok else "Falhou.")
        if summary_line:
            text += f"\n{summary_line}"

        # Use QMessageBox com texto detalhado expansível
        mbox = QtWidgets.QMessageBox(self)
        mbox.setWindowTitle(title)
        mbox.setText(text)
        mbox.setDetailedText(detail_text(result))
        mbox.setIcon(QtWidgets.QMessageBox.Icon.Information if ok else QtWidgets.QMessageBox.Icon.Warning)
        mbox.addButton(QtWidgets.QMessageBox.StandardButton.Ok)
        mbox.exec()

    # Actions
    def _run_clear_network(self) -> None:
        self._start_worker(network_cache.clear_network_cache)

    def _run_clear_local(self) -> None:
        self._start_worker(local_cache.clear_local_cache)

    def _run_clear_local_force(self) -> None:
        reply = QtWidgets.QMessageBox.warning(
            self,
            "Confirmação",
            (
                "A limpeza forçada pode encerrar processos de atualizadores (Discord/Teams/Chrome/Edge).\n"
                "Deseja continuar?"
            ),
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self._start_worker(local_cache.force_clear_local_cache)

    def _run_optimize_games(self) -> None:
        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirmação",
            "Otimizações de jogos alteram configurações avançadas do sistema (BCD/Registro).\nDeseja continuar?",
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self._start_worker(game_optimizer.optimize_pubg, True)

    def _run_power(self, label: str) -> None:
        self._start_worker(power_manager.set_power_plan, label)

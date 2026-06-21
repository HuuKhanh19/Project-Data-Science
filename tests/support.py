import sys
import types


def install_loguru_stub():
    if "loguru" in sys.modules:
        return

    loguru_module = types.ModuleType("loguru")

    class _Logger:
        def add(self, *args, **kwargs):
            return None

        def info(self, *args, **kwargs):
            return None

        def warning(self, *args, **kwargs):
            return None

        def error(self, *args, **kwargs):
            return None

        def debug(self, *args, **kwargs):
            return None

    loguru_module.logger = _Logger()
    sys.modules["loguru"] = loguru_module


def install_requests_stub():
    if "requests" in sys.modules and "requests.exceptions" in sys.modules:
        return

    requests_module = sys.modules.get("requests", types.ModuleType("requests"))

    class RequestException(Exception):
        pass

    class HTTPError(RequestException):
        def __init__(self, *args, response=None, **kwargs):
            super().__init__(*args)
            self.response = response

    class Session:
        def __init__(self):
            self.headers = {}

        def get(self, *args, **kwargs):
            raise NotImplementedError("Session.get is not implemented in test stub")

        def close(self):
            return None

    requests_module.RequestException = RequestException
    requests_module.Session = Session
    sys.modules["requests"] = requests_module

    exceptions_module = types.ModuleType("requests.exceptions")
    exceptions_module.RequestException = RequestException
    exceptions_module.HTTPError = HTTPError
    sys.modules["requests.exceptions"] = exceptions_module


def install_ta_stub():
    if "ta" in sys.modules:
        return

    ta_module = types.ModuleType("ta")
    ta_module.trend = types.SimpleNamespace(
        sma_indicator=lambda *args, **kwargs: None,
        ema_indicator=lambda *args, **kwargs: None,
        MACD=lambda *args, **kwargs: None,
    )
    ta_module.momentum = types.SimpleNamespace(rsi=lambda *args, **kwargs: None)
    ta_module.volatility = types.SimpleNamespace(
        BollingerBands=lambda *args, **kwargs: None,
        average_true_range=lambda *args, **kwargs: None,
    )
    ta_module.volume = types.SimpleNamespace(on_balance_volume=lambda *args, **kwargs: None)
    sys.modules["ta"] = ta_module

from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @abstractmethod
    def auditar_item(self, prod: dict, regime_tributario: str, **kwargs) -> list:
        """Método obrigatório que todas as estratégias de subgrupo devem implementar."""
        pass
import uuid

from django.db import models


class ExecutionStatus(models.IntegerChoices):
    SUCCESS = 0, "Success"
    FAILED = 1, "Failed"


class ScalingStrategy(models.IntegerChoices):
    STATIC = 0, "Static"
    DYNAMIC = 1, "Dynamic"
    GUIDED = 2, "Guided"


# --- CLASSE BASE ---
class BaseExecution(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )  # Identificador único universal[cite: 1]
    scaling_strategy = models.IntegerField(
        choices=ScalingStrategy.choices
    )  # Estratégia de escalonamento[cite: 1]
    num_threads = models.IntegerField()  # Nível de concorrência de hardware[cite: 1]
    array_size = (
        models.IntegerField()
    )  # Dimensão da matriz do problema matemático[cite: 1]
    status = models.IntegerField(choices=ExecutionStatus.choices, null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    error_detail = models.TextField(null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"Execução {self.id} - Status: {self.get_status_display()}"


# --- MIXINS (Pacotes de Métricas) ---
class SAHPLMetricsMixin(models.Model):
    flow_flops = models.FloatField(
        null=True, blank=True, help_text="Vazão de processamento físico"
    )  # Vazão calculada pós-benchmark[cite: 1]

    class Meta:
        abstract = True


class GSPNMetricsMixin(models.Model):
    estimated_gspn_flow = models.FloatField(
        null=True, blank=True, help_text="Vazão estimada GSPN"
    )  # Vazão teórica calculada pelo modelo[cite: 1]

    class Meta:
        abstract = True


# --- CLASSES FILHAS (Tabelas Reais) ---
class SAHPLExecution(BaseExecution, SAHPLMetricsMixin):
    class Meta:
        verbose_name = "Execução SA-HPL"
        verbose_name_plural = "Execuções SA-HPL"


class GSPNExecution(BaseExecution, GSPNMetricsMixin):
    class Meta:
        verbose_name = "Execução GSPN"
        verbose_name_plural = "Execuções GSPN"


class HybridExecution(BaseExecution, SAHPLMetricsMixin, GSPNMetricsMixin):
    class Meta:
        verbose_name = "Execução Híbrida (SA-HPL vs GSPN)"
        verbose_name_plural = "Execuções Híbridas"
        ordering = ["array_size", "num_threads"]

    @property
    def empirico_flops(self):
        return self.flow_flops

    @property
    def teorico_flops(self):
        return self.estimated_gspn_flow

    @property
    def absolute_error(self):
        if self.flow_flops is not None and self.estimated_gspn_flow is not None:
            return abs(self.flow_flops - self.estimated_gspn_flow)
        return None

    @property
    def relative_error_percentage(self):
        if self.flow_flops and self.estimated_gspn_flow is not None:
            return (
                abs(self.flow_flops - self.estimated_gspn_flow) / self.flow_flops
            ) * 100.0
        return None

    def to_dict(self):
        return {
            "id": str(self.id),
            "matriz": self.array_size,
            "empirico_flops": round(self.flow_flops, 2)
            if self.flow_flops is not None
            else None,
            "teorico_flops": round(self.estimated_gspn_flow, 2)
            if self.estimated_gspn_flow is not None
            else None,
            "scaling_strategy": self.get_scaling_strategy_display(),
            "scaling_strategy_code": self.scaling_strategy,
            "num_threads": self.num_threads,
            "status": self.get_status_display(),
            "duration_seconds": round(self.duration_seconds, 2)
            if self.duration_seconds is not None
            else None,
            "erro_relativo_pct": round(self.relative_error_percentage, 2)
            if self.relative_error_percentage is not None
            else None,
        }

    @classmethod
    def seed_mock_data(cls):
        """Popula execuções de exemplo caso a base esteja vazia."""
        if cls.objects.exists():
            return

        mock_data = [
            # Os 3 pontos base do template original
            {
                "array_size": 10000,
                "num_threads": 8,
                "scaling_strategy": ScalingStrategy.DYNAMIC,
                "flow_flops": 450.5,
                "estimated_gspn_flow": 448.2,
                "duration_seconds": 12.4,
                "status": ExecutionStatus.SUCCESS,
            },
            {
                "array_size": 20000,
                "num_threads": 8,
                "scaling_strategy": ScalingStrategy.DYNAMIC,
                "flow_flops": 890.1,
                "estimated_gspn_flow": 905.4,
                "duration_seconds": 45.1,
                "status": ExecutionStatus.SUCCESS,
            },
            {
                "array_size": 30000,
                "num_threads": 8,
                "scaling_strategy": ScalingStrategy.DYNAMIC,
                "flow_flops": 1250.3,
                "estimated_gspn_flow": 1260.0,
                "duration_seconds": 110.8,
                "status": ExecutionStatus.SUCCESS,
            },
            # Pontos complementares para permitir filtros interativos
            {
                "array_size": 10000,
                "num_threads": 4,
                "scaling_strategy": ScalingStrategy.STATIC,
                "flow_flops": 280.4,
                "estimated_gspn_flow": 275.0,
                "duration_seconds": 19.8,
                "status": ExecutionStatus.SUCCESS,
            },
            {
                "array_size": 20000,
                "num_threads": 4,
                "scaling_strategy": ScalingStrategy.STATIC,
                "flow_flops": 550.8,
                "estimated_gspn_flow": 562.1,
                "duration_seconds": 72.3,
                "status": ExecutionStatus.SUCCESS,
            },
            {
                "array_size": 30000,
                "num_threads": 4,
                "scaling_strategy": ScalingStrategy.STATIC,
                "flow_flops": 790.2,
                "estimated_gspn_flow": 810.5,
                "duration_seconds": 178.6,
                "status": ExecutionStatus.SUCCESS,
            },
            {
                "array_size": 10000,
                "num_threads": 16,
                "scaling_strategy": ScalingStrategy.GUIDED,
                "flow_flops": 620.7,
                "estimated_gspn_flow": 612.0,
                "duration_seconds": 8.9,
                "status": ExecutionStatus.SUCCESS,
            },
            {
                "array_size": 20000,
                "num_threads": 16,
                "scaling_strategy": ScalingStrategy.GUIDED,
                "flow_flops": 1180.5,
                "estimated_gspn_flow": 1205.8,
                "duration_seconds": 32.4,
                "status": ExecutionStatus.SUCCESS,
            },
            {
                "array_size": 30000,
                "num_threads": 16,
                "scaling_strategy": ScalingStrategy.GUIDED,
                "flow_flops": 1680.0,
                "estimated_gspn_flow": 1655.4,
                "duration_seconds": 81.2,
                "status": ExecutionStatus.SUCCESS,
            },
        ]

        for item in mock_data:
            cls.objects.create(**item)

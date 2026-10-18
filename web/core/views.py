from io import BytesIO

from django.contrib import messages
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.models import HybridExecution, ScalingStrategy

THREAD_OPTIONS = (2, 4, 8, 12, 16, 32)
MATRIX_OPTIONS = (10000, 20000, 30000)
MATRIX_SIZE = 8000

# Mean values below come from results/; theoretical values and timestamps are illustrative.
MEASURED_RUNS = (
    ("serial-1-8000", "Serial", 1, 437.225, 0.468447, 780.974, 0.836299, 764.2),
    ("dynamic-2-8000", "Dynamic", 2, 270.29, 6.30544, 1263.94, 29.9659, 1240.0),
    ("dynamic-4-8000", "Dynamic", 4, 144.398, 4.39816, 2366.69, 71.7047, 2410.0),
    ("dynamic-8-8000", "Dynamic", 8, 99.58, 0.825849, 3429.23, 28.525, 3500.0),
    ("dynamic-12-8000", "Dynamic", 12, 93.037, 4.57521, 3677.8, 172.652, 3720.0),
    ("dynamic-16-8000", "Dynamic", 16, 62.6971, 4.4719, 5469.77, 367.973, 5590.0),
    ("guided-2-8000", "Guided", 2, 273.013, 1.69424, 1250.76, 7.72485, 1279.0),
    ("guided-4-8000", "Guided", 4, 146.025, 3.78172, 2339.81, 61.4699, 2320.0),
    ("guided-8-8000", "Guided", 8, 98.8213, 1.09386, 3455.72, 38.1998, 3492.0),
    ("guided-12-8000", "Guided", 12, 93.9361, 5.04235, 3644.27, 191.321, 3590.0),
    ("guided-16-8000", "Guided", 16, 64.5717, 3.53375, 5303.12, 305.519, 5420.0),
    ("static-2-8000", "Static", 2, 273.32, 2.98694, 1249.45, 13.5684, 1280.0),
    ("static-4-8000", "Static", 4, 149.569, 4.48822, 2284.74, 65.8901, 2240.0),
    ("static-8-8000", "Static", 8, 100.27, 0.513818, 3405.49, 17.4142, 3500.0),
    ("static-12-8000", "Static", 12, 96.1162, 7.38147, 3570.98, 266.779, 3655.0),
    ("static-16-8000", "Static", 16, 68.9214, 4.46066, 4973.3, 325.622, 4850.0),
)


def _obter_execucoes_demo():
    """Combina medições SA-HPL com pares híbridos estimados para demonstração."""
    execucoes = []
    hibridas = []
    for index, (
        execution_id,
        strategy,
        threads,
        duration,
        duration_std,
        flow,
        flow_std,
        estimated_flow,
    ) in enumerate(MEASURED_RUNS):
        execucoes.append(
            {
                "id": execution_id,
                "tipo": "SA-HPL",
                "scaling_strategy": strategy,
                "num_threads": threads,
                "array_size": MATRIX_SIZE,
                "started_at": f"17/10/2026 18:{index:02d}",
                "started_at_sort": f"2026-10-17T18:{index:02d}:00",
                "status": "SUCCESS",
                "status_code": 0,
                "duration_seconds": duration,
                "duration_std": duration_std,
                "flow_flops": flow,
                "flow_std": flow_std,
                "estimated_gspn_flow": None,
                "error_detail": "",
                "source_file": (
                    "results/serial/serial-1-8000.txt"
                    if strategy == "Serial"
                    else f"results/{strategy.lower()}/omp-{strategy.lower()}-{threads}-8000.txt"
                ),
            }
        )
        hibridas.append(
            {
                "id": f"hybrid-{execution_id}",
                "tipo": "Híbrido",
                "scaling_strategy": strategy,
                "num_threads": threads,
                "array_size": MATRIX_SIZE,
                "started_at": f"17/10/2026 19:{index:02d}",
                "started_at_sort": f"2026-10-17T19:{index:02d}:00",
                "status": "SUCCESS",
                "status_code": 0,
                "duration_seconds": duration,
                "duration_std": duration_std,
                "flow_flops": flow,
                "flow_std": flow_std,
                "estimated_gspn_flow": estimated_flow,
                "error_detail": "",
                "source_file": "Dados híbridos fictícios para demonstração",
            }
        )

    execucoes.extend(hibridas)
    execucoes.append(
        {
            "id": "mock-failure-8000",
            "tipo": "SA-HPL",
            "scaling_strategy": "Dynamic",
            "num_threads": 8,
            "array_size": MATRIX_SIZE,
            "started_at": "17/10/2026 18:30",
            "started_at_sort": "2026-10-17T18:30:00",
            "status": "FAILED",
            "status_code": 1,
            "duration_seconds": None,
            "duration_std": None,
            "flow_flops": None,
            "flow_std": None,
            "estimated_gspn_flow": None,
            "error_detail": (
                "Falha demonstrativa: o processo de benchmark foi encerrado "
                "antes de produzir métricas. Este registro não corresponde a "
                "uma execução real."
            ),
            "source_file": "Registro fictício",
        }
    )
    return execucoes


def _obter_execucoes_visiveis(request):
    excluidas = set(request.session.get("deleted_demo_execution_ids", []))
    return [
        item for item in _obter_execucoes_demo() if item["id"] not in excluidas
    ]


def execution_delete_view(request):
    """Remove uma ou mais execuções demonstrativas do histórico da sessão."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    action = request.POST.get("action")
    if action == "single":
        requested_ids = [request.POST.get("execution_id", "")]
    elif action == "bulk":
        requested_ids = list(dict.fromkeys(request.POST.getlist("ids")))
    else:
        return HttpResponse("Ação de exclusão inválida.", status=400)

    if not requested_ids or any(not execution_id for execution_id in requested_ids):
        return HttpResponse("Selecione ao menos uma execução.", status=400)

    visible_ids = {item["id"] for item in _obter_execucoes_visiveis(request)}
    if any(execution_id not in visible_ids for execution_id in requested_ids):
        return HttpResponse(
            "Uma ou mais execuções selecionadas não existem.",
            status=400,
            content_type="text/plain; charset=utf-8",
        )

    deleted_ids = set(request.session.get("deleted_demo_execution_ids", []))
    deleted_ids.update(requested_ids)
    request.session["deleted_demo_execution_ids"] = sorted(deleted_ids)
    count = len(requested_ids)
    messages.success(
        request,
        f"{count} execução(ões) excluída(s) do histórico desta sessão.",
    )
    return redirect("history")


def _selecionar_execucoes_comparacao(request):
    execucoes = _obter_execucoes_visiveis(request)
    validas = {execucao["id"]: execucao for execucao in execucoes}
    ids_solicitados = list(dict.fromkeys(_query_values(request, "ids")))
    if not ids_solicitados:
        if request.GET.get("selection") == "history":
            return [], "Selecione ao menos uma execução para comparar."
        return [item for item in execucoes if item["status_code"] == 0], ""
    if len(ids_solicitados) > 20:
        return [], "Selecione no máximo 20 execuções para comparar."

    selecionadas = [validas[item] for item in ids_solicitados if item in validas]
    if len(selecionadas) != len(ids_solicitados):
        return [], "Uma ou mais execuções selecionadas não existem."
    if any(item["status_code"] != 0 for item in selecionadas):
        return [], "Somente execuções bem-sucedidas podem ser comparadas."
    if not selecionadas:
        return [], "Selecione ao menos uma execução para comparar."
    return selecionadas, ""


def _dados_graficos(execucoes):
    return [
        {
            "id": item["id"],
            "type": item["tipo"],
            "strategy": item["scaling_strategy"],
            "threads": item["num_threads"],
            "matrix": item["array_size"],
            "status": item["status"],
            "empirical": item["flow_flops"],
            "empirical_std": item["flow_std"],
            "theoretical": (
                item["estimated_gspn_flow"]
                if item["tipo"] in {"GSPN", "Híbrido"}
                else None
            ),
            "duration": item["duration_seconds"],
            "duration_std": item["duration_std"],
        }
        for item in execucoes
    ]


def _aplicar_filtros(execucoes, request):
    types = set(_query_values(request, "type"))
    strategies = set(_query_values(request, "strategy"))
    threads = set(_query_values(request, "threads"))
    matrices = set(_query_values(request, "matrix"))
    if types:
        execucoes = [item for item in execucoes if item["tipo"] in types]
    if strategies:
        execucoes = [
            item for item in execucoes if item["scaling_strategy"] in strategies
        ]
    if threads:
        execucoes = [
            item for item in execucoes if str(item["num_threads"]) in threads
        ]
    if matrices:
        execucoes = [
            item for item in execucoes if str(item["array_size"]) in matrices
        ]
    if request.GET.get("include_theoretical") == "0":
        for item in execucoes:
            item["estimated_gspn_flow"] = None
    return execucoes


def _query_values(request, key):
    return [
        value
        for raw_value in request.GET.getlist(key)
        for value in raw_value.split(",")
        if value
    ]


def _opcoes_filtros(execucoes):
    return {
        "strategies": sorted({item["scaling_strategy"] for item in execucoes}),
        "threads": sorted({item["num_threads"] for item in execucoes}),
        "matrices": sorted({item["array_size"] for item in execucoes}),
    }


def _filter_options_with_types(execucoes):
    return {
        **_opcoes_filtros(execucoes),
        "types": sorted({item["tipo"] for item in execucoes}),
    }


def execution_form_view(request):
    """Valida a configuração da execução e informa quando falta o executor HPC."""
    valores = {
        "task": request.POST.get("task", "SA-HPL"),
        "scaling_strategy": request.POST.get("scaling_strategy", ""),
        "num_threads": request.POST.get("num_threads", "8"),
        "array_size": request.POST.get("array_size", ""),
    }
    erros = {}
    erro_execucao = ""

    if request.method == "POST":
        if valores["task"] not in {"SA-HPL", "GSPN", "HYBRID"}:
            erros["task"] = "Selecione SA-HPL, GSPN ou Híbrido."

        valid_strategies = {str(code) for code, _ in ScalingStrategy.choices}
        if valores["scaling_strategy"] not in valid_strategies:
            erros["scaling_strategy"] = "Selecione uma estratégia válida."

        try:
            threads = int(valores["num_threads"])
            if not 1 <= threads <= 32:
                raise ValueError
        except (TypeError, ValueError):
            erros["num_threads"] = "Informe um número inteiro entre 1 e 32."

        try:
            array_size = int(valores["array_size"])
            if array_size < 1:
                raise ValueError
        except (TypeError, ValueError):
            erros["array_size"] = "Informe uma dimensão inteira maior que zero."

        if not erros:
            erro_execucao = (
                "Os parâmetros são válidos, mas o teste não foi executado: "
                "o projeto ainda não contém um executor HPC configurado."
            )

    contexto = {
        "estrategias": ScalingStrategy.choices,
        "thread_options": THREAD_OPTIONS,
        "matrix_options": MATRIX_OPTIONS,
        "valores": valores,
        "erros": erros,
        "erro_execucao": erro_execucao,
        "form_submitted": request.method == "POST",
        "custom_threads": (
            bool(valores["num_threads"])
            and valores["num_threads"] not in {str(value) for value in THREAD_OPTIONS}
        ),
        "custom_matrix": (
            bool(valores["array_size"])
            and valores["array_size"] not in {str(value) for value in MATRIX_OPTIONS}
        ),
        "nav_active": "home",
    }
    return render(
        request,
        "execution_form.html",
        contexto,
        status=503 if erro_execucao else 200,
    )


def history_view(request):
    """Lista as medições demonstrativas e permite abrir detalhes ou compará-las."""
    execucoes = _obter_execucoes_visiveis(request)
    return render(
        request,
        "execution_history.html",
        {
            "execucoes": execucoes,
            "chart_data": _dados_graficos(execucoes),
            "filter_options": _filter_options_with_types(execucoes),
            "nav_active": "history",
        },
    )


def execution_detail_view(request, execution_id):
    """Exibe parâmetros, métricas e erro de uma execução demonstrativa."""
    execucao = next(
        (
            item
            for item in _obter_execucoes_visiveis(request)
            if item["id"] == execution_id
        ),
        None,
    )
    if execucao is None:
        raise Http404("Execução não encontrada.")

    todas_execucoes = _obter_execucoes_visiveis(request)
    baseline = next(
        (item for item in todas_execucoes if item["id"] == "serial-1-8000"),
        None,
    )
    if execucao["flow_flops"] and baseline and baseline["flow_flops"]:
        execucao["speedup_vs_serial"] = round(
            execucao["flow_flops"] / baseline["flow_flops"], 2
        )
        execucao["gain_vs_serial_pct"] = round(
            (execucao["flow_flops"] / baseline["flow_flops"] - 1) * 100, 1
        )
    else:
        execucao["speedup_vs_serial"] = None
        execucao["gain_vs_serial_pct"] = None
    return render(
        request,
        "execution_detail.html",
        {
            "execucao": execucao,
            "chart_data": _dados_graficos(
                [execucao]
                if execucao["status_code"] == 0
                and execucao["tipo"] in {"GSPN", "Híbrido"}
                else []
            ),
            "show_chart": (
                execucao["status_code"] == 0
                and execucao["tipo"] in {"GSPN", "Híbrido"}
            ),
            "filter_options": _opcoes_filtros([execucao]),
            "nav_active": "history",
        },
    )


def execution_compare_view(request):
    """Compara até 20 execuções bem-sucedidas selecionadas."""
    execucoes, erro = _selecionar_execucoes_comparacao(request)
    status = 400 if erro else 200
    return render(
        request,
        "execution_compare.html",
        {
            "execucoes": execucoes,
            "erro": erro,
            "chart_data": _dados_graficos(execucoes),
            "filter_options": _filter_options_with_types(
                _obter_execucoes_visiveis(request)
            ),
            "nav_active": "history",
        },
        status=status,
    )


def comparison_pdf_view(request):
    """Gera o PDF da comparação com tabela consolidada e gráfico."""
    execucoes, erro = _selecionar_execucoes_comparacao(request)
    if erro:
        return HttpResponse(erro, status=400, content_type="text/plain; charset=utf-8")

    execucoes = _aplicar_filtros(execucoes, request)
    if not execucoes:
        return HttpResponse(
            "Os filtros não correspondem a nenhuma execução.",
            status=400,
            content_type="text/plain; charset=utf-8",
        )
    return _gerar_relatorio_pdf(
        execucoes,
        "Relatório comparativo SA-HPL & GSPN",
        focused_execution_id=None,
    )


def history_pdf_view(request):
    """Exporta todo o histórico ou apenas os IDs selecionados, incluindo falhas."""
    execucoes = _obter_execucoes_visiveis(request)
    ids_solicitados = list(dict.fromkeys(_query_values(request, "ids")))
    if ids_solicitados or request.GET.get("selection") == "filtered":
        validas = {execucao["id"]: execucao for execucao in execucoes}
        if any(execution_id not in validas for execution_id in ids_solicitados):
            return HttpResponse(
                "Uma ou mais execuções selecionadas não existem.",
                status=400,
                content_type="text/plain; charset=utf-8",
            )
        execucoes = [validas[execution_id] for execution_id in ids_solicitados]
    execucoes = _aplicar_filtros(execucoes, request)
    if request.GET.get("selection") == "filtered" and not execucoes:
        return HttpResponse(
            "Os filtros não correspondem a nenhuma execução.",
            status=400,
            content_type="text/plain; charset=utf-8",
        )

    titulo = (
        "Relatório do histórico de execuções"
        if not ids_solicitados and request.GET.get("selection") != "filtered"
        else "Relatório das execuções selecionadas"
    )
    return _gerar_relatorio_pdf(execucoes, titulo)


def execution_pdf_view(request, execution_id):
    """Exporta uma execução específica com gráficos exclusivos do próprio teste."""
    todas_execucoes = _obter_execucoes_visiveis(request)
    execucao = next((item for item in todas_execucoes if item["id"] == execution_id), None)
    if execucao is None:
        raise Http404("Execução não encontrada.")
    return _gerar_relatorio_pdf(
        [execucao],
        f"Detalhamento da execução {execution_id}",
        focused_execution_id=execution_id,
        include_theoretical=request.GET.get("include_theoretical", "1") != "0",
    )


def _gerar_relatorio_pdf(
    execucoes, titulo, focused_execution_id=None, include_theoretical=True
):
    """Gera relatório PDF tabular com os cinco gráficos analíticos."""
    execucoes = [dict(item) for item in execucoes]
    if not include_theoretical:
        for item in execucoes:
            item["estimated_gspn_flow"] = None
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=titulo,
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#006b3c"),
            fontSize=16,
        )
    )
    body = [
        Paragraph(titulo.replace("&", "&amp;"), styles["ReportTitle"]),
        Spacer(1, 4 * mm),
        Paragraph(f"{len(execucoes)} execução(ões) exportada(s)", styles["Normal"]),
        Paragraph(
            "Vazões teóricas e datas são ilustrativas. A vazão SA-HPL e o tempo "
            "são medições dos arquivos em results/.",
            styles["Normal"],
        ),
        Spacer(1, 5 * mm),
    ]
    cell_style = ParagraphStyle(
        "ReportCell",
        parent=styles["Normal"],
        fontSize=6.5,
        leading=8,
        wordWrap="CJK",
    )
    table_data = [
        [
            "ID",
            "Tipo",
            "Estratégia",
            "Threads",
            "Matriz",
            "Status",
            "Tempo (s)",
            "SA-HPL (MFLOPS)",
            "GSPN (MFLOPS)",
            "Data/hora",
            "Detalhe da falha",
        ]
    ]
    for item in execucoes:
        table_data.append(
            [
                Paragraph(item["id"], cell_style),
                item["tipo"],
                item["scaling_strategy"],
                str(item["num_threads"]),
                str(item["array_size"]),
                item["status"],
                f"{item['duration_seconds']:.2f}"
                if item["duration_seconds"] is not None
                else "—",
                f"{item['flow_flops']:.2f}" if item["flow_flops"] is not None else "—",
                f"{item['estimated_gspn_flow']:.2f}"
                if item["estimated_gspn_flow"] is not None
                else "—",
                item["started_at"],
                Paragraph(
                    item["error_detail"].replace("&", "&amp;").replace("<", "&lt;"),
                    cell_style,
                )
                if item["error_detail"]
                else "—",
            ]
        )

    table = Table(
        table_data,
        colWidths=[30 * mm, 20 * mm, 20 * mm, 12 * mm, 17 * mm, 17 * mm, 19 * mm, 26 * mm, 26 * mm, 30 * mm, 52 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#052414")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#17231c")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b7c9be")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#edf5ef")],
                ),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEADING", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    body.append(table)

    for graph_title, drawing in _criar_graficos_pdf(
        execucoes, focused_execution_id, include_theoretical
    ):
        body.extend(
            [
                PageBreak(),
                Paragraph(graph_title, styles["Heading2"]),
                Spacer(1, 5 * mm),
                drawing,
            ]
        )
    document.build(body)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="relatorio-execucoes.pdf"'
    return response


def _media_por_chave(execucoes, chave, metric):
    grupos = {}
    for execucao in execucoes:
        valor = execucao[metric]
        if valor is not None:
            grupos.setdefault(execucao[chave], []).append(valor)
    return {
        chave_valor: sum(valores) / len(valores)
        for chave_valor, valores in grupos.items()
    }


def _criar_graficos_pdf(
    execucoes, focused_execution_id=None, include_theoretical=True
):
    """Renderiza como gráficos vetoriais os cinco painéis do dashboard exemplo."""
    sucesso = [item for item in execucoes if item["status_code"] == 0]
    if not sucesso:
        titles = (
            "Comparativo por Threads (Barras)",
            "Escalabilidade por Threads (Linhas)",
            "Eficiência por Estratégia OpenMP",
            "Heatmap: Erro Relativo (Matriz vs Threads)",
            "Dispersão de Vazão por Dimensão da Matriz",
        )
        empty_charts = []
        for title in titles:
            drawing = Drawing(700, 440)
            drawing.add(
                String(
                    350,
                    220,
                    "Sem medições disponíveis para esta execução.",
                    textAnchor="middle",
                    fontSize=12,
                    fillColor=colors.HexColor("#526157"),
                )
            )
            empty_charts.append((title, drawing))
        return empty_charts

    threads = sorted({item["num_threads"] for item in sucesso})
    strategies = sorted(
        {item["scaling_strategy"] for item in sucesso if item["scaling_strategy"] != "Serial"}
    )
    if not strategies:
        strategies = ["Serial"]
    matrices = sorted({item["array_size"] for item in sucesso})

    thread_empirical = _media_por_chave(sucesso, "num_threads", "flow_flops")
    thread_theoretical = _media_por_chave(
        sucesso, "num_threads", "estimated_gspn_flow"
    )
    strategy_empirical = _media_por_chave(sucesso, "scaling_strategy", "flow_flops")
    strategy_theoretical = _media_por_chave(
        sucesso, "scaling_strategy", "estimated_gspn_flow"
    )
    if not include_theoretical:
        thread_theoretical = {}
        strategy_theoretical = {}
    labels = [f"{item['scaling_strategy']}-{item['num_threads']}T" for item in sucesso]

    def draw_axes(drawing, y_max):
        left, bottom, width, height = 58, 52, 620, 330
        drawing.add(Line(left, bottom, left + width, bottom, strokeColor=colors.HexColor("#66756b")))
        drawing.add(Line(left, bottom, left, bottom + height, strokeColor=colors.HexColor("#66756b")))
        for tick in range(5):
            value = y_max * tick / 4
            y = bottom + height * tick / 4
            drawing.add(
                Line(left, y, left + width, y, strokeColor=colors.HexColor("#d9e2dc"), strokeWidth=0.35)
            )
            drawing.add(
                String(left - 8, y - 2, f"{value:.0f}", textAnchor="end", fontSize=8, fillColor=colors.HexColor("#526157"))
            )
        return left, bottom, width, height

    def draw_series_chart(title, x_labels, series, kind, highlight_index=None):
        drawing = Drawing(700, 440)
        values = [value for _, values, _ in series for value in values if value is not None]
        y_max = max(values, default=1) * 1.15
        left, bottom, width, height = draw_axes(drawing, y_max or 1)
        count = max(1, len(x_labels))
        slot = width / count
        for series_index, (name, values, color) in enumerate(series):
            points = []
            for index, value in enumerate(values):
                if value is None:
                    continue
                x_center = left + slot * (index + 0.5)
                y = bottom + height * value / y_max
                if kind == "bar":
                    bar_width = min(18, slot / (len(series) + 1))
                    x = x_center + (series_index - (len(series) - 1) / 2) * bar_width
                    drawing.add(
                        Rect(x, bottom, bar_width * 0.85, max(1, y - bottom), fillColor=color, strokeColor=None)
                    )
                elif kind == "line":
                    points.append((x_center, y))
                    if len(points) > 1:
                        drawing.add(
                            Line(*points[-2], *points[-1], strokeColor=color, strokeWidth=2)
                        )
                    marker_color = (
                        colors.HexColor("#f7c843")
                        if highlight_index == index
                        else color
                    )
                    drawing.add(Circle(x_center, y, 3.5, fillColor=marker_color, strokeColor=marker_color))
            if series_index < len(series):
                legend_x = left + series_index * 190
                drawing.add(Rect(legend_x, 414, 10, 10, fillColor=color, strokeColor=None))
                drawing.add(String(legend_x + 15, 415, name, fontSize=8, fillColor=colors.HexColor("#25352b")))
        for index, label in enumerate(x_labels):
            x = left + slot * (index + 0.5)
            drawing.add(String(x, bottom - 16, str(label)[:18], textAnchor="middle", fontSize=6, fillColor=colors.HexColor("#526157")))
        return drawing

    chart1 = draw_series_chart(
        "Comparativo por Threads",
        [f"{thread}T" for thread in threads],
        [
            ("SA-HPL medido", [thread_empirical.get(thread) for thread in threads], colors.HexColor("#00a85a")),
            ("GSPN estimado", [thread_theoretical.get(thread) for thread in threads], colors.HexColor("#5187a8")),
        ],
        "bar",
    )
    chart2 = draw_series_chart(
        "Escalabilidade por Threads",
        [f"{thread}T" for thread in threads],
        [
            ("SA-HPL medido", [thread_empirical.get(thread) for thread in threads], colors.HexColor("#00a85a")),
            ("GSPN estimado", [thread_theoretical.get(thread) for thread in threads], colors.HexColor("#5187a8")),
        ],
        "line",
        next(
            (
                index
                for index, thread in enumerate(threads)
                if any(item["id"] == focused_execution_id and item["num_threads"] == thread for item in sucesso)
            ),
            None,
        ),
    )
    chart3 = draw_series_chart(
        "Eficiência por Estratégia OpenMP",
        strategies,
        [
            ("SA-HPL medido", [strategy_empirical.get(strategy) for strategy in strategies], colors.HexColor("#00a85a")),
            ("GSPN estimado", [strategy_theoretical.get(strategy) for strategy in strategies], colors.HexColor("#5187a8")),
        ],
        "bar",
    )

    heatmap = Drawing(700, 440)
    left, bottom, width, height = 75, 62, 590, 310
    thread_slot = width / max(1, len(threads))
    matrix_slot = height / max(1, len(matrices))
    for row, matrix in enumerate(matrices):
        for column, thread in enumerate(threads):
            cell_runs = [
                item for item in sucesso
                if item["array_size"] == matrix and item["num_threads"] == thread
                and item["flow_flops"] and item["estimated_gspn_flow"] is not None
            ]
            error = (
                sum(abs(item["flow_flops"] - item["estimated_gspn_flow"]) / item["flow_flops"] * 100 for item in cell_runs)
                / len(cell_runs)
                if cell_runs else None
            )
            if error is not None:
                intensity = min(error / 15, 1)
                color = colors.Color(0.08 + 0.75 * intensity, 0.78 - 0.55 * intensity, 0.36 - 0.26 * intensity)
                x = left + column * thread_slot
                y = bottom + height - (row + 1) * matrix_slot
                heatmap.add(Rect(x, y, thread_slot - 2, matrix_slot - 2, fillColor=color, strokeColor=colors.white))
                heatmap.add(String(x + thread_slot / 2, y + matrix_slot / 2, f"{error:.1f}%", textAnchor="middle", fontSize=7))
        heatmap.add(String(left - 8, bottom + height - (row + 0.65) * matrix_slot, f"N={matrix}", textAnchor="end", fontSize=7))
    for column, thread in enumerate(threads):
        heatmap.add(String(left + (column + 0.5) * thread_slot, bottom - 14, f"{thread}T", textAnchor="middle", fontSize=7))
    heatmap.add(String(left + width / 2, 18, "Concorrência (Threads) · cor mais quente = maior erro relativo", textAnchor="middle", fontSize=8))

    scatter = Drawing(700, 440)
    x_values = [item["array_size"] for item in sucesso]
    y_values = [
        value for item in sucesso
        for value in (item["flow_flops"], item["estimated_gspn_flow"])
        if value is not None
    ]
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values, default=0), max(y_values, default=1)
    s_left, s_bottom, s_width, s_height = 58, 52, 620, 330
    scatter.add(Line(s_left, s_bottom, s_left + s_width, s_bottom, strokeColor=colors.HexColor("#66756b")))
    scatter.add(Line(s_left, s_bottom, s_left, s_bottom + s_height, strokeColor=colors.HexColor("#66756b")))
    for index, item in enumerate(sucesso):
        x_value = item["array_size"]
        x = s_left + s_width * ((x_value - x_min) / (x_max - x_min or 1))
        x += (index % 5 - 2) * 5
        for metric, color in (
            (item["flow_flops"], colors.HexColor("#00a85a")),
            (item["estimated_gspn_flow"], colors.HexColor("#5187a8")),
        ):
            if metric is not None:
                y = s_bottom + s_height * ((metric - y_min) / (y_max - y_min or 1))
                point_color = colors.HexColor("#f7c843") if item["id"] == focused_execution_id else color
                scatter.add(Circle(x, y, 3.5, fillColor=point_color, strokeColor=point_color))
    for index in range(5):
        value = y_min + (y_max - y_min) * index / 4
        y = s_bottom + s_height * index / 4
        scatter.add(String(s_left - 8, y - 2, f"{value:.0f}", textAnchor="end", fontSize=8))
        scatter.add(Line(s_left, y, s_left + s_width, y, strokeColor=colors.HexColor("#d9e2dc"), strokeWidth=0.35))
    for index, matrix in enumerate(matrices):
        x = s_left + s_width * (index / max(1, len(matrices) - 1))
        scatter.add(String(x, s_bottom - 16, f"N={matrix}", textAnchor="middle", fontSize=8))
    scatter.add(Rect(s_left + 10, 412, 10, 10, fillColor=colors.HexColor("#00a85a"), strokeColor=None))
    scatter.add(String(s_left + 25, 413, "SA-HPL medido", fontSize=8))
    scatter.add(Rect(s_left + 145, 412, 10, 10, fillColor=colors.HexColor("#5187a8"), strokeColor=None))
    scatter.add(String(s_left + 160, 413, "GSPN estimado", fontSize=8))

    return [
        ("Comparativo por Threads (Barras)", chart1),
        ("Escalabilidade por Threads (Linhas)", chart2),
        ("Eficiência por Estratégia OpenMP", chart3),
        ("Heatmap: Erro Relativo (Matriz vs Threads)", heatmap),
        ("Dispersão de Vazão por Dimensão da Matriz", scatter),
    ]


def _obter_dados_execucoes():
    """Recupera as execuções híbridas persistidas para a API."""
    if not HybridExecution.objects.exists():
        HybridExecution.seed_mock_data()

    execucoes = HybridExecution.objects.all().order_by("-started_at")
    dados = []
    for execucao in execucoes:
        item = execucao.to_dict()
        item["tipo"] = "Híbrido"
        item["started_at"] = timezone.localtime(execucao.started_at).strftime(
            "%d/%m/%Y %H:%M"
        )
        dados.append(item)
    return dados


def _calcular_kpis(dados):
    """Calcula estatísticas agregadas de desempenho e acurácia teórica."""
    if not dados:
        return {
            "total_execucoes": 0,
            "media_empirico": 0.0,
            "media_teorico": 0.0,
            "pico_empirico": 0.0,
            "erro_medio_pct": 0.0,
            "acuracia_media_pct": 0.0,
        }

    valid_empirico = [
        d["empirico_flops"] for d in dados if d.get("empirico_flops") is not None
    ]
    valid_teorico = [
        d["teorico_flops"] for d in dados if d.get("teorico_flops") is not None
    ]
    valid_erros = [
        d["erro_relativo_pct"] for d in dados if d.get("erro_relativo_pct") is not None
    ]

    media_empirico = (
        sum(valid_empirico) / len(valid_empirico) if valid_empirico else 0.0
    )
    media_teorico = sum(valid_teorico) / len(valid_teorico) if valid_teorico else 0.0
    pico_empirico = max(valid_empirico) if valid_empirico else 0.0
    erro_medio = sum(valid_erros) / len(valid_erros) if valid_erros else 0.0
    acuracia_media = max(0.0, 100.0 - erro_medio)

    return {
        "total_execucoes": len(dados),
        "media_empirico": round(media_empirico, 1),
        "media_teorico": round(media_teorico, 1),
        "pico_empirico": round(pico_empirico, 1),
        "erro_medio_pct": round(erro_medio, 2),
        "acuracia_media_pct": round(acuracia_media, 2),
    }


def executions_api_view():
    """Endpoint REST que expõe os dados de execução e métricas para integrações."""
    dados = _obter_dados_execucoes()
    kpis = _calcular_kpis(dados)
    return JsonResponse({"status": "success", "kpis": kpis, "data": dados})

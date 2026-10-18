from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse


class ExecutionDemoViewsTests(TestCase):
    def test_history_lists_measured_runs_and_failure_example(self):
        response = self.client.get(reverse("history"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "serial-1-8000")
        self.assertContains(response, "dynamic-16-8000")
        self.assertContains(response, "FAILED")
        self.assertContains(response, "GSPN")
        self.assertContains(response, "Híbrido")
        self.assertContains(response, "analysis-filter-type")
        self.assertContains(response, 'name="selection" value="filtered"')
        self.assertContains(response, "delete-confirmation-modal")
        self.assertContains(response, "Confirmar exclusão")
        self.assertContains(response, 'id="delete-selected-button" disabled')
        self.assertNotContains(response, "window.confirm")
        self.assertContains(response, "graficoComparativo")
        self.assertNotContains(response, "graficoHeatmap")
        self.assertEqual(len(response.context["chart_data"]), 33)
        measured = next(
            item
            for item in response.context["chart_data"]
            if item["id"] == "dynamic-16-8000"
        )
        hybrid = next(
            item
            for item in response.context["chart_data"]
            if item["id"] == "hybrid-dynamic-16-8000"
        )
        self.assertIsNone(measured["theoretical"])
        self.assertIsNotNone(hybrid["theoretical"])
        self.assertContains(response, "0 execuções selecionadas")
        self.assertContains(
            response,
            'aria-label="Comparar execuções selecionadas" disabled',
        )

    @patch("core.views._obter_execucoes_demo", return_value=[])
    def test_history_disables_comparison_when_there_are_no_executions(self, _mock_runs):
        response = self.client.get(reverse("history"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhuma execução disponível para exibir.")
        self.assertContains(response, "0 execuções selecionadas")
        self.assertContains(
            response,
            'aria-label="Comparar execuções selecionadas" disabled',
        )

    def test_history_can_delete_one_execution_and_hide_its_detail(self):
        response = self.client.post(
            reverse("execution_delete"),
            {"action": "single", "execution_id": "dynamic-16-8000"},
        )

        self.assertRedirects(
            response, reverse("history"), fetch_redirect_response=False
        )
        history = self.client.get(reverse("history"))
        visible_ids = [item["id"] for item in history.context["execucoes"]]
        self.assertNotIn("dynamic-16-8000", visible_ids)
        self.assertIn("hybrid-dynamic-16-8000", visible_ids)
        self.assertEqual(
            [str(message) for message in history.context["messages"]],
            ["1 execução(ões) excluída(s) do histórico desta sessão."],
        )
        detail = self.client.get(
            reverse("execution_detail", args=["dynamic-16-8000"])
        )
        self.assertEqual(detail.status_code, 404)

    def test_history_can_delete_multiple_selected_executions(self):
        response = self.client.post(
            reverse("execution_delete"),
            {
                "action": "bulk",
                "ids": ["dynamic-16-8000", "hybrid-dynamic-16-8000"],
            },
        )

        self.assertRedirects(
            response, reverse("history"), fetch_redirect_response=False
        )
        history = self.client.get(reverse("history"))
        visible_ids = [item["id"] for item in history.context["execucoes"]]
        self.assertNotIn("dynamic-16-8000", visible_ids)
        self.assertNotIn("hybrid-dynamic-16-8000", visible_ids)
        self.assertEqual(
            [str(message) for message in history.context["messages"]],
            ["2 execução(ões) excluída(s) do histórico desta sessão."],
        )

    def test_delete_rejects_get_and_unknown_execution_ids(self):
        get_response = self.client.get(reverse("execution_delete"))
        self.assertEqual(get_response.status_code, 405)

        invalid_response = self.client.post(
            reverse("execution_delete"),
            {"action": "single", "execution_id": "missing-run"},
        )
        self.assertEqual(invalid_response.status_code, 400)

    def test_detail_shows_measured_metrics_and_baseline_comparison(self):
        response = self.client.get(
            reverse("execution_detail", args=["dynamic-16-8000"])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "5469.77")
        self.assertContains(response, "MFLOPS")
        self.assertContains(response, "Referência serial")
        self.assertContains(response, "Exportar execução")
        self.assertContains(response, "Tipo: SA-HPL")
        self.assertNotContains(response, "graficoComparativo")
        self.assertNotContains(response, "Gráficos desta execução")
        self.assertNotContains(response, "Vazão estimada")
        self.assertNotContains(response, 'for="analysis-filter-strategy"')
        self.assertEqual(response.context["chart_data"], [])

    def test_hybrid_detail_compares_real_and_simulated_values_in_one_chart(self):
        response = self.client.get(
            reverse("execution_detail", args=["hybrid-dynamic-16-8000"])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tipo: Híbrido")
        self.assertContains(response, "Vazão estimada")
        self.assertContains(response, "graficoComparativo")
        self.assertNotContains(response, "graficoHeatmap")
        self.assertTrue(response.context["show_chart"])
        self.assertEqual(len(response.context["chart_data"]), 1)
        self.assertEqual(response.context["chart_data"][0]["theoretical"], 5590.0)

    def test_detail_shows_error_trace_for_failed_run(self):
        response = self.client.get(
            reverse("execution_detail", args=["mock-failure-8000"])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rastreamento demonstrativo")
        self.assertContains(response, "não corresponde a uma execução real")

    def test_detail_returns_404_for_unknown_run(self):
        response = self.client.get(reverse("execution_detail", args=["missing-run"]))

        self.assertEqual(response.status_code, 404)

    def test_comparison_defaults_to_all_successful_runs(self):
        response = self.client.get(reverse("execution_compare"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-kpi="count"')
        self.assertContains(response, "dynamic-16-8000")
        self.assertContains(response, "graficoComparativo")
        self.assertNotContains(response, "graficoHeatmap")
        self.assertContains(response, "Tipo")

    def test_comparison_uses_requested_ids_and_rejects_failed_runs(self):
        response = self.client.get(
            reverse("execution_compare"),
            {"ids": ["serial-1-8000", "dynamic-16-8000"]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "serial-1-8000")
        self.assertContains(response, "dynamic-16-8000")
        self.assertNotContains(response, "static-2-8000")

        failed_response = self.client.get(
            reverse("execution_compare"), {"ids": "mock-failure-8000"}
        )
        self.assertEqual(failed_response.status_code, 400)
        self.assertContains(
            failed_response,
            "Somente execuções bem-sucedidas",
            status_code=400,
        )

    def test_comparison_requires_selection_from_history_and_caps_selection(self):
        empty_response = self.client.get(
            reverse("execution_compare"), {"selection": "history"}
        )
        self.assertEqual(empty_response.status_code, 400)
        self.assertContains(
            empty_response,
            "Selecione ao menos uma execução",
            status_code=400,
        )

        too_many_response = self.client.get(
            reverse("execution_compare"),
            {"ids": [f"run-{index}" for index in range(21)]},
        )
        self.assertEqual(too_many_response.status_code, 400)
        self.assertContains(too_many_response, "no máximo 20", status_code=400)

    def test_pdf_download_contains_a_pdf_document(self):
        response = self.client.get(
            reverse("comparison_pdf"), {"ids": ["serial-1-8000", "dynamic-16-8000"]}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-"))

    def test_history_pdf_exports_all_runs_and_selected_failed_runs(self):
        full_history = self.client.get(reverse("history_pdf"))
        self.assertEqual(full_history.status_code, 200)
        self.assertEqual(full_history["Content-Type"], "application/pdf")
        self.assertTrue(full_history.content.startswith(b"%PDF-"))

        selected = self.client.get(
            reverse("history_pdf"),
            {"ids": ["dynamic-16-8000", "mock-failure-8000"]},
        )
        self.assertEqual(selected.status_code, 200)
        self.assertEqual(selected["Content-Type"], "application/pdf")
        self.assertTrue(selected.content.startswith(b"%PDF-"))

    def test_history_pdf_rejects_unknown_execution_ids(self):
        response = self.client.get(
            reverse("history_pdf"), {"ids": "execution-does-not-exist"}
        )

        self.assertEqual(response.status_code, 400)

    @patch("core.views._gerar_relatorio_pdf", return_value=HttpResponse("pdf"))
    def test_execution_pdf_contains_only_the_requested_execution(self, make_pdf):
        response = self.client.get(
            reverse("execution_pdf", args=["dynamic-16-8000"]),
            {
                "strategy": "Dynamic",
                "threads": "16",
                "include_theoretical": "0",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"pdf")
        self.assertEqual(
            [item["id"] for item in make_pdf.call_args.args[0]],
            ["dynamic-16-8000"],
        )

    @patch("core.views._gerar_relatorio_pdf", return_value=HttpResponse("pdf"))
    def test_history_pdf_exports_filtered_history(self, make_pdf):
        response = self.client.get(
            reverse("history_pdf"),
            {
                "selection": "filtered",
                "ids": ["dynamic-16-8000", "mock-failure-8000"],
                "type": "SA-HPL",
                "strategy": "Dynamic",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in make_pdf.call_args.args[0]],
            ["dynamic-16-8000", "mock-failure-8000"],
        )

    def test_comparison_pdf_applies_analysis_filters(self):
        response = self.client.get(
            reverse("comparison_pdf"),
            {
                "ids": "serial-1-8000,dynamic-16-8000",
                "type": "SA-HPL",
                "strategy": "Dynamic",
                "include_theoretical": "0",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF-"))

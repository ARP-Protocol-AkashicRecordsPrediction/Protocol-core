from django.test import TestCase
from rest_framework.test import APIClient

from simulator.models import Agenda, PopulationCluster, PredictionRun, ShockEvent


class APITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_agenda_crud(self):
        response = self.client.post(
            "/api/agendas/",
            {
                "title": "AI search regulation",
                "description": "Predict public reaction.",
                "target_region": "US",
                "target_population": "online users",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        agenda_id = response.data["id"]

        detail = self.client.get(f"/api/agendas/{agenda_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["title"], "AI search regulation")

    def test_expand_clusters_preserves_seed_weight_without_llm(self):
        agenda = Agenda.objects.create(title="Agenda", description="Description")
        response = self.client.post(
            f"/api/agendas/{agenda.id}/clusters/expand/",
            {
                "desired_count": 1,
                "seed_clusters": [
                    {
                        "name": "Privacy-first skeptics",
                        "description": "Concerned about tracking.",
                        "weight": 0.22,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        cluster = PopulationCluster.objects.get(agenda=agenda)
        self.assertEqual(cluster.weight, 0.22)
        self.assertEqual(cluster.weight_source, PopulationCluster.WEIGHT_EXPLICIT)

    def test_create_prediction_run_with_shocks(self):
        agenda = Agenda.objects.create(title="Agenda", description="Description")
        response = self.client.post(
            "/api/prediction-runs/",
            {
                "agenda_id": str(agenda.id),
                "config": {"hybrid_sampling": False},
                "shock_events": [
                    {
                        "order": 1,
                        "title": "Announcement",
                        "description": "Policy announced.",
                        "event_type": "policy",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        run = PredictionRun.objects.get(id=response.data["id"])
        self.assertEqual(run.shock_events.count(), 1)

    def test_start_prediction_run_sync_without_clusters(self):
        agenda = Agenda.objects.create(title="Agenda", description="Description")
        run = PredictionRun.objects.create(agenda=agenda)
        ShockEvent.objects.create(
            prediction_run=run,
            order=1,
            title="Announcement",
            description="Policy announced.",
        )
        response = self.client.post(
            f"/api/prediction-runs/{run.id}/start/",
            {"run_async": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        run.refresh_from_db()
        self.assertEqual(run.status, PredictionRun.STATUS_COMPLETED)


class UITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_dashboard_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Agenda Dashboard")

    def test_dashboard_creates_agenda(self):
        response = self.client.post(
            "/",
            {
                "title": "Public AI reaction",
                "description": "Predict social reaction.",
                "target_region": "US",
                "target_population": "online users",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Agenda.objects.filter(title="Public AI reaction").exists())

    def test_agenda_detail_adds_cluster_and_run(self):
        agenda = Agenda.objects.create(title="Agenda", description="Description")
        cluster_response = self.client.post(
            f"/agendas/{agenda.id}/",
            {
                "action": "add_cluster",
                "name": "Privacy skeptics",
                "description": "Concerned about opaque AI.",
                "weight": "0.4",
                "confidence": "0.8",
            },
        )
        self.assertEqual(cluster_response.status_code, 302)
        self.assertTrue(PopulationCluster.objects.filter(agenda=agenda, name="Privacy skeptics").exists())

        run_response = self.client.post(
            f"/agendas/{agenda.id}/",
            {
                "action": "create_run",
                "shock_title": "Policy announcement",
                "shock_description": "A new rule is announced.",
                "event_type": "policy",
            },
        )
        self.assertEqual(run_response.status_code, 302)
        self.assertEqual(PredictionRun.objects.filter(agenda=agenda).count(), 1)

    def test_run_detail_renders(self):
        agenda = Agenda.objects.create(title="Agenda", description="Description")
        run = PredictionRun.objects.create(agenda=agenda)
        response = self.client.get(f"/runs/{run.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Prediction run")

from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import Agenda, PopulationCluster, PredictionRun, ShockEvent


@require_http_methods(["GET", "POST"])
def dashboard(request):
    if request.method == "POST":
        Agenda.objects.create(
            title=request.POST.get("title", "").strip(),
            description=request.POST.get("description", "").strip(),
            target_region=request.POST.get("target_region", "").strip(),
            target_population=request.POST.get("target_population", "").strip(),
        )
        return redirect("ui-dashboard")

    agendas = (
        Agenda.objects.prefetch_related("clusters", "prediction_runs")
        .all()
        .order_by("-created_at")
    )
    recent_runs = PredictionRun.objects.select_related("agenda").order_by("-created_at")[:8]
    return render(
        request,
        "simulator/dashboard.html",
        {
            "agendas": agendas,
            "recent_runs": recent_runs,
        },
    )


@require_http_methods(["GET", "POST"])
def agenda_detail(request, agenda_id):
    agenda = get_object_or_404(Agenda, id=agenda_id)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_cluster":
            weight_raw = request.POST.get("weight", "1")
            confidence_raw = request.POST.get("confidence", "0.7")
            PopulationCluster.objects.update_or_create(
                agenda=agenda,
                name=request.POST.get("name", "").strip(),
                defaults={
                    "description": request.POST.get("description", "").strip(),
                    "weight": float(weight_raw or 1),
                    "weight_source": PopulationCluster.WEIGHT_EXPLICIT,
                    "confidence": float(confidence_raw or 0.7),
                },
            )
        elif action == "create_run":
            prediction_run = PredictionRun.objects.create(
                agenda=agenda,
                config={"hybrid_sampling": request.POST.get("hybrid_sampling") == "on"},
            )
            ShockEvent.objects.create(
                prediction_run=prediction_run,
                order=1,
                title=request.POST.get("shock_title", "").strip(),
                description=request.POST.get("shock_description", "").strip(),
                event_type=request.POST.get("event_type", "").strip(),
            )
            return redirect("ui-run-detail", run_id=prediction_run.id)
        return redirect("ui-agenda-detail", agenda_id=agenda.id)

    clusters = agenda.clusters.order_by("name")
    runs = agenda.prediction_runs.order_by("-created_at")
    topics = agenda.memory_topics.select_related("cluster").order_by("-importance_score", "title")
    return render(
        request,
        "simulator/agenda_detail.html",
        {
            "agenda": agenda,
            "clusters": clusters,
            "runs": runs,
            "topics": topics,
        },
    )


def run_detail(request, run_id):
    prediction_run = get_object_or_404(
        PredictionRun.objects.select_related("agenda").prefetch_related("shock_events"),
        id=run_id,
    )
    states = (
        prediction_run.cluster_states.select_related("cluster", "shock_event")
        .all()
        .order_by("shock_event__order", "cluster__name")
    )
    turns = (
        prediction_run.turns.select_related("cluster", "shock_event")
        .all()
        .order_by("created_at")
    )
    return render(
        request,
        "simulator/run_detail.html",
        {
            "run": prediction_run,
            "states": states,
            "turns": turns,
        },
    )


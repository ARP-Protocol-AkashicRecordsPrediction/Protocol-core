from celery import shared_task

from simulator.models import PredictionRun
from simulator.services.prediction_service import PredictionService


def _run_prediction(prediction_run_id: str) -> str:
    try:
        PredictionService().run_prediction(prediction_run_id)
    except Exception as exc:
        PredictionRun.objects.filter(id=prediction_run_id).update(
            status=PredictionRun.STATUS_FAILED,
            error_message=str(exc),
        )
        raise
    return prediction_run_id


run_prediction_task = shared_task(name="simulator.run_prediction")(_run_prediction)

from celery import Celery

from app.core.config import settings

# Broker Y backend de resultados son el mismo Redis (DB 1, separada de la
# DB 0 donde vive la memoria de corto plazo del chat). Para esta escala de
# proyecto, no hace falta un backend de resultados distinto — Redis sirve
# para las dos cosas sin problema.
celery_app = Celery(
    "englia",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url,
)

celery_app.conf.broker_connection_retry_on_startup = True

celery_app.autodiscover_tasks(["app.workers"])

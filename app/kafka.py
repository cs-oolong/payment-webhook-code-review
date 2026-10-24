import json

from kafka import KafkaProducer

from app.settings import settings

producer = KafkaProducer(
    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
    api_version=(0, 10, 0),
    value_serializer=lambda value: json.dumps(value).encode(),
)

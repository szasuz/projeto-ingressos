import json
import os
import uuid
from pathlib import Path
import pika
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles

load_dotenv()

app = FastAPI(title="API de Reserva de Ingressos")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = "ingressos.topic"
ROUTING_KEY = "reserva.criada"
FRONTEND_FILE = Path(__file__).resolve().parent.parent / "frontend" / "index.html"


class ReservaRequest(BaseModel):
    cliente: str = Field(..., min_length=2)
    documento: str = Field(..., min_length=5)
    email: str = Field(..., min_length=5)
    evento: str
    setor: str
    quantidade: int = Field(..., ge=1)
    pagamento: str
    valor_total: float
    simular_erro: bool = False


def publicar_evento(payload: dict):
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    try:
        channel = connection.channel()
        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type="topic",
            durable=True,
        )
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=ROUTING_KEY,
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistência em disco
                content_type="application/json",
            ),
        )
    finally:
        connection.close()


@app.get("/")
def home():
    return FileResponse(FRONTEND_FILE)


@app.post("/reservas", status_code=status.HTTP_202_ACCEPTED)
def criar_reserva(reserva: ReservaRequest):
    reserva_id = f"RES-{uuid.uuid4().hex[:6].upper()}"
    evento_payload = {"reserva_id": reserva_id, **reserva.model_dump()}

    try:
        publicar_evento(evento_payload)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Erro ao publicar evento no RabbitMQ: {e}",
        )

    return {
        "reserva_id": reserva_id,
        "status": "Reserva Recebida / Em Processamento",
    }

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
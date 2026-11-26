import json
import os
import time
import pika
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = "ingressos.topic"
DLX_NAME = "ingressos.dlx"

QUEUE_NAME = "fila_estoque"
ROUTING_KEY_IN = "reserva.criada"

DLQ_NAME = "fila_estoque_dlq"
DLQ_ROUTING_KEY = "estoque.erro"


def configurar_topologia(channel):
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
    channel.exchange_declare(exchange=DLX_NAME, exchange_type="direct", durable=True)

    channel.queue_declare(queue=DLQ_NAME, durable=True)
    channel.queue_bind(exchange=DLX_NAME, queue=DLQ_NAME, routing_key=DLQ_ROUTING_KEY)

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": DLX_NAME,
            "x-dead-letter-routing-key": DLQ_ROUTING_KEY,
        },
    )
    channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=ROUTING_KEY_IN)


def callback_estoque(ch, method, properties, body):
    dados = json.loads(body.decode("utf-8"))
    reserva_id = dados.get("reserva_id")
    evento = dados.get("evento")
    setor = dados.get("setor")
    qtd = dados.get("quantidade", 1)

    print(f"\n[ESTOQUE] Bloqueando {qtd}x ingresso(s) | Evento: {evento} ({setor}) | Reserva: {reserva_id}")
    time.sleep(1)

    print(f"[ESTOQUE] Inventário atualizado para reserva {reserva_id}.")
    ch.basic_ack(delivery_tag=method.delivery_tag)


def iniciar():
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    configurar_topologia(channel)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=callback_estoque,
        auto_ack=False,
    )

    print(f"[*] WORKER ESTOQUE (PID {os.getpid()}) aguardando em '{QUEUE_NAME}'... CTRL+C para sair.")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\n[!] Worker Estoque interrompido manualmente.")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    iniciar()
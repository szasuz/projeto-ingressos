import json
import os
import time
import pika
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = "ingressos.topic"
DLX_NAME = "ingressos.dlx"

QUEUE_NAME = "fila_pagamentos"
ROUTING_KEY_IN = "reserva.criada"
ROUTING_KEY_OUT = "pagamento.aprovado"

DLQ_NAME = "fila_pagamentos_dlq"
DLQ_ROUTING_KEY = "pagamento.erro"


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


def callback_pagamento(ch, method, properties, body):
    dados = json.loads(body.decode("utf-8"))
    reserva_id = dados.get("reserva_id")
    cliente = dados.get("cliente")
    valor = dados.get("valor_total", 0.0)
    simular_erro = dados.get("simular_erro", False)

    print(f"\n[PAGAMENTO] Processando reserva {reserva_id} | Cliente: {cliente} | Valor: R$ {valor:.2f}")
    time.sleep(2)  

    if simular_erro:
        print(f"[PAGAMENTO] ERRO SIMULADO na reserva {reserva_id}! Rejeitando mensagem -> DLQ ({DLQ_NAME}).")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    evento_aprovado = {
        **dados,
        "status_pagamento": "APROVADO",
        "timestamp_aprovacao": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    ch.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key=ROUTING_KEY_OUT,
        body=json.dumps(evento_aprovado),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
        ),
    )

    print(f"[PAGAMENTO] Reserva {reserva_id} APROVADA! Evento '{ROUTING_KEY_OUT}' publicado.")
    ch.basic_ack(delivery_tag=method.delivery_tag)


def iniciar():
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    configurar_topologia(channel)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=callback_pagamento,
        auto_ack=False,
    )

    print(f"[*] WORKER PAGAMENTOS (PID {os.getpid()}) aguardando em '{QUEUE_NAME}'... CTRL+C para sair.")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\n[!] Worker Pagamentos interrompido manualmente.")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    iniciar()
<div align="center">

# 🎟️ TicketFlow — Reserva de Ingressos Distribuída

**Arquitetura Orientada a Eventos (EDA) com FastAPI, Python e RabbitMQ (CloudAMQP)**

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white)
![CloudAMQP](https://img.shields.io/badge/CloudAMQP-Broker-2C3E50?style=for-the-badge)

*Atividade 04 — Programação Distribuída, Paralela e Concorrente (PDPC) • Grupo Anchieta*

</div>

---

## 📌 Visão Geral

O **TicketFlow** é uma aplicação web de reserva de ingressos projetada para eliminar o acoplamento direto entre serviços. Em vez de chamadas HTTP síncronas e bloqueantes, o sistema opera de forma assíncrona sobre um **Message Broker (RabbitMQ via CloudAMQP)**, garantindo resposta imediata ao usuário, coreografia de eventos, tolerância a falhas com **Dead Letter Queue (DLQ)** e escalabilidade horizontal entre múltiplos workers.

---

## 🔄 Fluxo da Arquitetura

```mermaid
    flowchart LR
    UI[🌐 Frontend Web] -->|POST /reservas| API[⚡ FastAPI Producer]
    API -->|HTTP 202 Accepted| UI
    API -->|reserva.criada| EX((ingressos.topic))

    EX -->|reserva.criada| QP[📥 fila_pagamentos]
    EX -->|reserva.criada| QE[📥 fila_estoque]

    QP --> WP[💳 pagamento_worker.py]
    QE --> WE[📦 estoque_worker.py]

    WP -->|simular_erro = false<br/>pagamento.aprovado| EX
    WP -.->|simular_erro = true<br/>basic_nack| DLX((ingressos.dlx))
    DLX -.->|pagamento.erro| DLQ[🚨 fila_pagamentos_dlq]

    EX -->|pagamento.aprovado| QN[📥 fila_notificacoes]
    QN --> WN[📧 notificacao_worker.py]
    
```

### Etapas do Processamento

1. **Produtor (`api/main.py`):** O frontend dispara o `POST /reservas` para a API em FastAPI, que valida o payload, publica o evento `reserva.criada` na exchange `ingressos.topic` (com `delivery_mode=2` para persistência em disco) e devolve `HTTP 202 Accepted` na hora sem travar a tela do usuário.
2. **Pub/Sub na Entrada:** Dois serviços independentes consomem a mesma chave `reserva.criada` em paralelo:
   * **`workers/estoque_worker.py` (`fila_estoque`):** bloqueia e atualiza o inventário de ingressos do setor selecionado.
   * **`workers/pagamento_worker.py` (`fila_pagamentos`):** processa a cobrança. Se `simular_erro` vier `true`, rejeita a mensagem com `basic_nack(..., requeue=False)` e desvia direto para a `fila_pagamentos_dlq` via `ingressos.dlx`. No fluxo normal, publica o evento resultante `pagamento.aprovado`.
3. **Coreografia (`pagamento.aprovado`):**
   * **`workers/notificacao_worker.py` (`fila_notificacoes`):** reage à aprovação do pagamento, gera o voucher com QR Code e confirma o envio do ingresso ao cliente.

---

## 🗺️ Topologia Configurada no Broker

| Componente | Tipo / Exchange | Routing Key | Durável | Responsabilidade |
| :--- | :--- | :--- | :---: | :--- |
| `ingressos.topic` | Exchange (`topic`) | — | ✅ | Barramento principal de eventos do domínio |
| `ingressos.dlx` | Exchange (`direct`) | — | ✅ | Roteador de mensagens rejeitadas para DLQs |
| `fila_pagamentos` | Queue (`ingressos.topic`) | `reserva.criada` | ✅ | Valida cobrança e encadeia `pagamento.aprovado` |
| `fila_estoque` | Queue (`ingressos.topic`) | `reserva.criada` | ✅ | Reserva a quantidade de ingressos do setor |
| `fila_notificacoes` | Queue (`ingressos.topic`) | `pagamento.aprovado` | ✅ | Emite o QR Code e confirma o envio por e-mail |
| `fila_pagamentos_dlq` | Queue (`ingressos.dlx`) | `pagamento.erro` | ✅ | Isola reservas rejeitadas no pagamento |
| `fila_estoque_dlq` | Queue (`ingressos.dlx`) | `estoque.erro` | ✅ | Dead Letter Queue de falhas de estoque |
| `fila_notificacoes_dlq` | Queue (`ingressos.dlx`) | `notificacao.erro` | ✅ | Dead Letter Queue de falhas de notificação |

---

## 📂 Estrutura do Projeto

```text
projeto-ingressos/
├── api/
│   ├── main.py                  # API Gateway / Produtor FastAPI
│   └── requirements.txt
├── frontend/
│   └── index.html               # Interface Web (TicketFlow)
├── workers/
│   ├── estoque_worker.py        # Consumidor Pub/Sub (Inventário)
│   ├── notificacao_worker.py    # Consumidor Coreografado (QR Code / E-mail)
│   └── pagamento_worker.py      # Consumidor + Produtor + Tratamento DLQ
├── .env                         # Variáveis de ambiente (ignorado no Git)
├── .gitignore
├── requirements.txt             # Dependências gerais do projeto
└── README.md
```

---

## 🚀 Como Rodar Localmente

### 1. Instalar as dependências
```bash
pip install -r requirements.txt
```

### 2. Configurar as variáveis de ambiente
Crie um arquivo `.env` na raiz do projeto com a URL AMQPS da sua instância no CloudAMQP:
```env
RABBITMQ_URL=amqps://usuario:senha@servidor.rmq.cloudamqp.com/vhost
```

### 3. Subir a API e o Frontend
Na raiz do projeto, inicie o servidor Uvicorn:
```bash
uvicorn api.main:app --reload
```
Acesse a interface web em: **`http://127.0.0.1:8000`**

### 4. Subir os Workers
Abra **um terminal separado** para cada serviço consumidor e execute:

```bash
# Terminal 2 — Serviço de Pagamentos
python workers/pagamento_worker.py
```
```bash
# Terminal 3 — Serviço de Estoque
python workers/estoque_worker.py
```
```bash
# Terminal 4 — Serviço de Notificações
python workers/notificacao_worker.py
```

---

## 🧪 Roteiro de Testes Integrados

| Cenário | Como Executar | Resultado Esperado |
| :--- | :--- | :--- |
| **1. Fluxo Normal + Coreografia** | Com API e os 3 workers ativos, realize uma reserva normal pela tela. | `Pagamento` e `Estoque` consomem juntos; `Notificação` dispara logo após a aprovação. |
| **2. Queda de Serviço (Caos)** | Pressione `Ctrl + C` no `pagamento_worker.py`, envie reservas e religue o worker. | As mensagens ficam retidas como `Ready` em `fila_pagamentos` e são drenadas ao religar. |
| **3. Isolamento via DLQ** | Marque a opção **Simular Erro** no formulário e envie a reserva. | O worker executa `basic_nack(..., requeue=False)` e a mensagem vai para `fila_pagamentos_dlq`. |
| **4. Rajada (Escalabilidade)** | Abra 2+ terminais rodando `pagamento_worker.py` e dispare 10 reservas seguidas. | O RabbitMQ distribui a carga automaticamente (Round-Robin) entre os diferentes PIDs. |
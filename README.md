
# Semana 2 – Implementação Básica e Experimentos

## Visão Geral

Este repositório contém o controlador `` escrito em Python usando o framework **Ryu 4.34**.  O script implementa um **switch de camada 2** com aprendizado automático de endereços MAC, encaminhamento direto quando o destino é conhecido, flood quando ainda não é, e instalação de regras de fluxo para evitar que pacotes futuros precisem voltar ao controlador.

> **Entrega exigida na Semana 2:**\
> ▸ Script do controlador  ▸ Testes de conectividade  ▸ Experimentação de roteamento IP básico

---

## Estrutura do Projeto

```
semana2/
├── switch_l2.py          # Controlador L2 com aprendizado de MAC
├── switch_l2.log         # (Gerado em tempo de execução) logs detalhados
└── README.md             # Este arquivo
```

---

## Pré‑requisitos

| Componente   | Versão mínima | Observação                            |
| ------------ | ------------- | ------------------------------------- |
| Python       | 3.8           | Utilizado em `venvSemana2`            |
| Ryu          | 4.34          | Instalado via `pip install ryu==4.34` |
| Mininet      | ≥ 2.3         | Pacote padrão da VM Mininet           |
| Open vSwitch | 2.13+         | Incluído na VM                        |

Crie o ambiente virtual se desejar:

```bash
python3 -m venv venvSemana2
source venvSemana2/bin/activate
pip install -r requirements.txt   # já contém ryu 4.34 e dependências
```

---

## Execução Passo a Passo

1. **Inicie o controlador** (gera `switch_l2.log` automaticamente):
   ```bash
   ryu-manager switch_l2.py
   ```
2. **Abra outro terminal** e execute o Mininet, garantindo OpenFlow 1.3:
   ```bash
   sudo mn --controller=remote,ip=127.0.0.1,port=6653 \
          --topo=single,3 --mac \
          --switch=ovsk,protocol=OpenFlow13
   ```
3. **Teste conectividade**:
   ```mininet
   mininet> pingall
   *** Results: 0% dropped (6/6 received)
   ```
4. **Experimente roteamento IP básico** (ping por IP):
   ```mininet
   mininet> h1 ping -c 3 10.0.0.2
   ```
   A resposta comprova que pacotes IP são encaminhados corretamente através do switch L2.

---

## Exemplo de Log Gerado (`switch_l2.log`)

```
2025-07-01 14:32:08,934 INFO pkt src=00:00:00:00:00:01 → dst=ff:ff:ff:ff:ff:ff (in 1)
2025-07-01 14:32:08,935 INFO pkt src=00:00:00:00:00:02 → dst=00:00:00:00:00:01 (in 2)
2025-07-01 14:32:08,935 INFO pkt src=00:00:00:00:00:01 → dst=00:00:00:00:00:02 (in 1)
...
```

Essas entradas mostram o aprendizado de MAC e o direcionamento correto dos quadros.

---

## Como o Código Funciona (Resumo)

1. **Regra default**: na conexão do switch (`EventOFPSwitchFeatures`) o controlador envia um *flow mod* que encaminha todos os pacotes desconhecidos ao controlador.
2. **Aprendizado**: para cada `PacketIn`, o controlador grava `src MAC → porta` em `self.mac_to_port`.
3. **Encaminhamento**: se já conhece o `dst MAC`, faz unicast; caso contrário, faz flood.
4. **Instalação de fluxos**: quando faz unicast, instala um fluxo específico para agilizar pacotes futuros.

Diagrama:

```
[Host A]──(port1)──┐           ┌──(port2)──[Host B]
                   │  Switch   │
[Controller]◄──────┘  L2 (Ryu) └──(port3)──[Host C]
```

---

## Coletando Logs Alternativamente

Se preferir, redirecione todo o stdout para arquivo:

```bash
ryu-manager switch_l2.py > switch_l2.log 2>&1
```

---

**Autores:** Alice Motin, Caroline Lanzuolo Yamaguchi, Fábio Marcon Siqueira e Ian Andriani Gonçalves – Engenharia de Computação/UFSC – Redes de Computadores

---

## Referências

- [Ryu Book – Switching Hub](https://osrg.github.io/ryu-book/en/html/switching_hub.html)  
  Explica o funcionamento básico de um switch L2 no Ryu, incluindo aprendizado de MAC e comportamento de flood.

- [Exemplo oficial no GitHub – simple_switch_13.py](https://github.com/faucetsdn/ryu/blob/master/ryu/app/simple_switch_13.py)  
  Código referência da própria equipe do Ryu para implementação de switch com aprendizado L2.

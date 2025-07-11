# Semana 2 – Implementação Básica e Experimentos

## Visão Geral

Este repositório contém o controlador \`\` escrito em Python usando o framework **Ryu 4.34**.  O script implementa um **switch de camada 2** com aprendizado automático de endereços MAC, encaminhamento direto quando o destino é conhecido, flood quando ainda não é, e instalação de regras de fluxo para evitar que pacotes futuros precisem voltar ao controlador.

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

## Pré ‑requisitos

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
   Saída esperada:
   ```
   3 packets transmitted, 3 received, 0% packet loss
   ```
   Esse teste comprova que o tráfego IP encapsulado em quadros Ethernet foi corretamente encaminhado pelo switch L2, operando com base no aprendizado de endereços MAC feito dinamicamente pelo controlador Ryu.

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
[Controller]◄─────┘  L2 (Ryu) └──(port3)──[Host C]
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

- [Ryu Book – Switching Hub](https://osrg.github.io/ryu-book/en/html/switching_hub.html)\
  Explica o funcionamento básico de um switch L2 no Ryu, incluindo aprendizado de MAC e comportamento de flood.

- [Exemplo oficial no GitHub – simple\_switch\_13.py](https://github.com/faucetsdn/ryu/blob/master/ryu/app/simple_switch_13.py)\
  Código referência da própria equipe do Ryu para implementação de switch com aprendizado L2.

---

# Semana 3 – Balanceador de Carga SDN

## Visão Geral

Este projeto implementa um **balanceador de carga baseado em ARP spoofing e NAT** utilizando o controlador SDN **Ryu 4.34** com OpenFlow 1.3. O IP virtual `10.0.0.10` é usado para representar um serviço fictício, cujo tráfego é redirecionado de forma transparente para os servidores reais `h5` e `h6`, conectados ao switch nas portas 5 e 6.

O balanceamento ocorre no momento da resolução ARP, alternando entre os dois servidores com uma política de round-robin.

> **Entrega exigida na Semana 3:**\
> ▸ Controlador funcional com balanceamento de carga\
> ▸ Testes de redirecionamento via ICMP (`ping`)\
> ▸ Coleta de logs de roteamento

---

## Estrutura do Projeto

```
semana3/
├── code/
│   ├── balanceador_carga.py     # Controlador SDN com balanceamento
├── results/
│   ├── controller_logs.txt      # Logs do Ryu com redirecionamento ativo
│   └── ping_logs_h1_h2.txt      # Testes de ping via IP virtual
├── examples/
│   └── exemplos_comandos.txt    # Comandos úteis de execução
└── docs/
    └── guia_usuario.md          # Documentação técnica e teórica
```

---

## Pré ‑requisitos

| Componente   | Versão mínima | Observação                            |
| ------------ | ------------- | ------------------------------------- |
| Python       | 3.8           | Utilizado em `venvSemana2`            |
| Ryu          | 4.34          | Instalado via `pip install ryu==4.34` |
| Mininet      | ≥ 2.3         | Pacote padrão da VM Mininet           |
| Open vSwitch | 2.13+         | Incluído na VM                        |

---

## Execução Passo a Passo

1. **Inicie o controlador:**

   ```bash
   ryu-manager code/balanceador_carga.py
   ```

2. **Em outro terminal, execute o Mininet com 6 hosts e OpenFlow 1.3:**

   ```bash
   sudo mn --controller=remote,ip=127.0.0.1,port=6653 \
           --topo=single,6 --mac \
           --switch=ovsk,protocols=OpenFlow13
   ```

3. **Teste o balanceamento com ICMP:**

   ```bash
   mininet> h1 ping 10.0.0.10
   mininet> h2 ping 10.0.0.10
   ```

4. **Verifique os logs no terminal do Ryu:**

   ```
   Pacote recebido: src=00:00:00:00:00:01, dst=ff:ff:ff:ff:ff:ff, porta de entrada=1
   Pacote recebido: src=00:00:00:00:00:05, dst=00:00:00:00:00:01, porta de entrada=5
   ```

---

## Como o Código Funciona (Resumo)

1. **Intercepta ARP:** quando um host tenta resolver o IP `10.0.0.10`, o controlador responde com o MAC de `h5` ou `h6`, alternando a cada nova requisição.

2. **Instala fluxos NAT:**

   - Cliente → IP virtual → servidor real
   - Servidor real → cliente → IP virtual
   - Isso garante que o cliente pense estar se comunicando com `10.0.0.10`, mesmo recebendo pacotes do IP real.

3. **Encaminhamento transparente:** o switch passa a encaminhar pacotes diretamente com base nas regras OpenFlow instaladas.

Diagrama:

```
[h1]──┐
[h2]──┬──(port 1–6)──┐
[h3]──┘              │
                    Switch S1
                   (Controlado Ryu)
[h5] ───(port 5)──────│ ← Servidor 1
[h6] ───(port 6)──────┘ ← Servidor 2
```

---

## Exemplo de Comandos (`examples/exemplos_comandos.txt`)

```
# Iniciar controlador
ryu-manager code/balanceador_carga.py

# Subir topologia
sudo mn --controller=remote,ip=127.0.0.1,port=6653 --topo=single,6 --mac --switch=ovsk,protocols=OpenFlow13

# Testes
mininet> h1 ping 10.0.0.10
mininet> h2 ping 10.0.0.10
```

---

## Coleta de Logs

Salve os logs gerados pelo `ryu-manager` com os pacotes recebidos e redirecionados em:

```
results/controller_logs.txt
```

Salve os testes de `ping` de `h1` e `h2` em:

```
results/ping_logs_h1_h2.txt
```

---

## Bugs Conhecidos

- O balanceamento atual ocorre apenas na primeira resolução ARP. Todos os pacotes seguintes usam o mesmo servidor.
- Se o host pingar constantemente, o fluxo OpenFlow impede a alternância de servidor.

---

## Melhorias Futuras

- Usar `idle_timeout` nos fluxos para alternância real por sessão.
- Implementar suporte a TCP além de ICMP.
- Implementar um dashboard para monitorar o servidor ativo.
- Adicionar lógica de balanceamento por carga real (ex: round-robin, least connections, etc).


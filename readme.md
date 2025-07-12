# Descrição Geral 

Este projeto faz parte da disciplina de Redes de Computadores e tem como foco a aplicação de conceitos de Redes Definidas por Software (SDN), utilizando o controlador Ryu e o simulador Mininet. Durante duas semanas foram desenvolvidos dois sistemas distintos: um switch de camada 2 com aprendizado automático de endereços MAC e um balanceador de carga baseado em técnicas de ARP spoofing e NAT.

---

# Semana 2 – Implementação Básica e Experimentos

Nessa primeira etapa, o objetivo foi criar um controlador que atua como um switch inteligente. Sempre que um pacote chega ao switch e seu destino ainda não é conhecido o controlador envia o pacote para todas as portas. Enquanto isso, ele aprende automaticamente os endereços MAC de origem e associa cada um à porta por onde o pacote entrou. Com isso, nos próximos envios, ele sabe exatamente para onde encaminhar os pacotes, tornando o processo mais rápido e eficiente.

> **Entrega exigida na Semana 2:**\
> ▸ Script do controlador  ▸ Testes de conectividade  ▸ Experimentação de roteamento IP básico

---

## Estrutura do Projeto

```
semana2/
├── code/
│   ├── switch_l2.py # Controlador L2 com aprendizado de
└── results/
    └── switch_l2.log # (Gerado em tempo de execução) logs detalhados
```

---

## Configurando o ambiente

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

## Como Executar o Projeto (Passo a Passo)

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
> [!NOTE]
> Esse teste comprova que o tráfego IP encapsulado em quadros Ethernet foi corretamente encaminhado pelo switch L2, operando com base no aprendizado de endereços MAC feito dinamicamente pelo controlador Ryu.

---

## Exemplo de Log Gerado (`switch_l2.log`)

```
2025-07-01 14:32:08,934 INFO pkt src=00:00:00:00:00:01 → dst=ff:ff:ff:ff:ff:ff (in 1)
2025-07-01 14:32:08,935 INFO pkt src=00:00:00:00:00:02 → dst=00:00:00:00:00:01 (in 2)
2025-07-01 14:32:08,935 INFO pkt src=00:00:00:00:00:01 → dst=00:00:00:00:00:02 (in 1)
...
```

Essas entradas mostram o aprendizado de MAC e o direcionamento correto dos quadros.


Na primeira linha, o computador com endereço MAC 00:00:00:00:00:01 envia um pacote para todo mundo porque ainda não conhece o destino. Na segunda linha, o computador 00:00:00:00:00:02 tenta se comunicar diretamente com o 00:00:00:00:00:01. Como o controlador já aprendeu em qual porta o destinatário está, ele encaminha a mensagem de forma direta. Por fim, 00:00:00:00:00:01 responde a 00:00:00:00:00:02, e novamente ele envia o pacote diretamente.

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

# Semana 3 – Balanceador de Carga SDN

Nessa segunda etapa o foco passou a ser o balanceamento de carga. A ideia foi simular um IP virtual (10.0.0.10) que representa um único serviço, mas na verdade esse IP é atendido por dois servidores reais (os hosts h5 e h6). Quando um cliente da rede tenta se comunicar com esse IP, o controlador intercepta a requisição ARP e responde com o MAC de um dos servidores, alternando entre eles com uma política simples de round-robin. Assim, o tráfego dos clientes é distribuído entre os dois servidores, mesmo que pareça que todos estão se comunicando com o mesmo destino. O projeto também instala regras de NAT para que os pacotes sejam redirecionados de forma transparente, sem quebra de comunicação.

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
└── results/
    ├── controller_logs.txt      # Logs do Ryu com redirecionamento ativo
    └── ping_logs_h1_h2.txt      # Testes de ping via IP virtual
```

---

## Configurando o ambiente

| Componente   | Versão mínima | Observação                            |
| ------------ | ------------- | ------------------------------------- |
| Python       | 3.8           | Utilizado em `venvSemana2`            |
| Ryu          | 4.34          | Instalado via `pip install ryu==4.34` |
| Mininet      | ≥ 2.3         | Pacote padrão da VM Mininet           |
| Open vSwitch | 2.13+         | Incluído na VM                        |

---

## Como Executar o Projeto (Passo a Passo)

1. **Inicie o controlador:** (lembre-se de estar com ambiente virtual ativo)

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

---

## Referências

- [Ryu Book – Switching Hub](https://osrg.github.io/ryu-book/en/html/switching_hub.html)\
  Explica o funcionamento básico de um switch L2 no Ryu, incluindo aprendizado de MAC e comportamento de flood.

- [Exemplo oficial no GitHub – simple\_switch\_13.py](https://github.com/faucetsdn/ryu/blob/master/ryu/app/simple_switch_13.py)\
  Código referência da própria equipe do Ryu para implementação de switch com aprendizado L2.

## **Autores** 
| [<img loading="lazy" src="https://avatars.githubusercontent.com/u/112569754?v=4" width=115><br><sub>Alice Motin</sub>](https://github.com/AliceMotin) | [<img loading="lazy" src="https://avatars.githubusercontent.com/u/147776134?v=4" width=115><br><sub>Caroline Lanzuolo</sub>](https://github.com/carol-lanzu) | [<img loading="lazy" src="https://avatars.githubusercontent.com/u/127808270?v=4" width=115><br><sub>Fabio Siqueira</sub>](https://github.com/Fabioomega) | [<img loading="lazy" src="https://avatars.githubusercontent.com/u/122290431?v=4" width=115><br><sub>Ian Andriani</sub>](https://github.com/ianandriani07) | 
| :---: | :---: | :---: | :---: |

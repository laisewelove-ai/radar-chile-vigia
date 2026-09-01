#!/usr/bin/env python3
"""
Vigia do Radar Chile.

Existe porque o alarme do próprio radar é cego para o pior tipo de falha. O
aviso de "atualização FALHOU" mora dentro do job do GitHub Actions, então
quando o job nem chega a começar (franquia de minutos estourada, pagamento
recusado, agendador parado) não existe ninguém para mandar a mensagem. Foi o
que aconteceu entre 27 e 31/08/2026: o radar ficou cinco dias fora do ar,
servindo câmbio de 26/08 rotulado como "hoje", e nenhum alerta saiu.

Este vigia roda em repositório PÚBLICO de propósito: Actions em repo público
não consome a franquia mensal, então ele continua de pé exatamente na
situação em que o radar cai.

Ele não olha logs nem API do GitHub. Olha o que o público vê: o carimbo de
atualização, a data do câmbio e a captura mensal de passagens na própria
página. Se o sintoma final aparece, alarme, seja qual for a causa.

Decisão por DIA, não por horas corridas: o agendador do GitHub derruba
disparo com frequência (em 01/09/2026 saíram 7 de 24), e contar horas fazia
um simples vão entre execuções virar alarme falso.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

URL = "https://radar-chile.pages.dev/"
CHILE = timezone(timedelta(hours=-4))  # o horário de verão desloca 1h, e as
                                       # folgas abaixo absorvem isso de sobra.

HORA_COBRANCA = 11        # a janela do radar abre às 09h; a partir das 11h no
                          # Chile, não ter atualizado hoje é defeito, não atraso
DIA_TOLERANCIA_PASSAGENS = 2   # a captura mensal roda no dia 1
HORAS_ENTRE_ALARMES = 12  # não repetir o mesmo alarme antes disso
ESTADO = "estado.json"


def carregar_estado() -> dict:
    try:
        with open(ESTADO, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def salvar_estado(d: dict) -> None:
    try:
        with open(ESTADO, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except Exception as e:
        print(f"não consegui gravar o estado: {e}", file=sys.stderr)


def telegram(msg: str) -> bool:
    """Devolve True se a mensagem saiu. Nunca levanta: alarme que estoura no
    meio do caminho é alarme perdido, e o motivo precisa aparecer no log."""
    token, chat = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT")
    if not token or not chat:
        print("Sem credenciais do Telegram; não dá para avisar.", file=sys.stderr)
        return False
    dados = json.dumps({"chat_id": chat, "text": msg}).encode()
    for tentativa in (1, 2, 3):
        try:
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=dados,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=30).read()
            return True
        except Exception as e:
            print(f"Telegram tentativa {tentativa} falhou: {e}", file=sys.stderr)
            if tentativa < 3:
                time.sleep(5)
    return False


def buscar() -> str | None:
    for tentativa in (1, 2, 3):
        try:
            req = urllib.request.Request(
                URL, headers={"User-Agent": "radar-chile-vigia (monitoramento)"}
            )
            with urllib.request.urlopen(req, timeout=45) as r:
                if r.status != 200:
                    raise RuntimeError(f"HTTP {r.status}")
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            print(f"tentativa {tentativa} falhou: {e}", file=sys.stderr)
            if tentativa < 3:
                time.sleep(20)   # soluço de rede não pode virar alarme
    return None


def dia_esperado(agora: datetime) -> tuple[str, str]:
    """Qual é a atualização mais antiga aceitável agora, e como explicá-la."""
    if agora.hour >= HORA_COBRANCA:
        return agora.strftime("%Y-%m-%d"), "hoje"
    ontem = agora - timedelta(days=1)
    return ontem.strftime("%Y-%m-%d"), "ontem"


def main() -> int:
    agora = datetime.now(CHILE)
    html = buscar()
    estado = carregar_estado()
    # Só a data, não a hora: o commit deste arquivo é o que mantém o
    # repositório ativo (o GitHub desativa workflow agendado depois de 60 dias
    # sem atividade, e um vigia que morre sozinho é pior que vigia nenhum).
    # Com granularidade de dia, isso vira 1 commit por dia em vez de 12.
    estado["ultima_checagem"] = agora.strftime("%Y-%m-%d")

    if html is None:
        problemas = ["A página não abriu em três tentativas, com 20 segundos entre elas."]
    else:
        problemas = []

        m = re.search(r"atualizado em (\d{2})/(\d{2})/(\d{4}) às (\d{2}):(\d{2})", html)
        if not m:
            problemas.append(
                "A página abriu, mas não tem carimbo de atualização nenhum. "
                "Ou o gerador quebrou, ou o que está no ar não é o radar."
            )
        else:
            d, mes, ano, hh, mm = (int(x) for x in m.groups())
            atualizado = datetime(ano, mes, d, hh, mm, tzinfo=CHILE)
            limite, palavra = dia_esperado(agora)
            if atualizado.strftime("%Y-%m-%d") < limite:
                horas = (agora - atualizado).total_seconds() / 3600
                problemas.append(
                    f"O site não atualiza desde {atualizado:%d/%m às %H:%M} "
                    f"({horas:.0f} horas atrás). Já deveria ter rodado {palavra}."
                )

        # Sem 'else' aqui seria o pior tipo de furo: a linha do câmbio some da
        # página, a regex volta vazia e o vigia diz "saudável" justamente sobre
        # o sintoma que passou seis dias despercebido em agosto de 2026.
        c = re.search(r"cotação Wise · (\d{2})/(\d{2}) às (\d{2}):(\d{2})", html)
        if not c:
            problemas.append(
                "A página não mostra mais a data da cotação. O bloco de câmbio "
                "sumiu ou mudou de formato, e sem ele ninguém percebe número velho."
            )
        else:
            d, mes, hh, mm = (int(x) for x in c.groups())
            cambio = datetime(agora.year, mes, d, hh, mm, tzinfo=CHILE)
            if cambio > agora + timedelta(days=1):   # virada de ano
                cambio = cambio.replace(year=agora.year - 1)
            limite, palavra = dia_esperado(agora)
            if cambio.strftime("%Y-%m-%d") < limite:
                horas = (agora - cambio).total_seconds() / 3600
                problemas.append(
                    f"A cotação está congelada desde {cambio:%d/%m às %H:%M} "
                    f"({horas:.0f} horas) e o site mostra ela como se fosse de hoje."
                )

        # A captura mensal roda todo dia 1 e é a falha mais fácil de perder de
        # vista, porque acontece uma vez por mês e só incomoda quando alguém vai
        # procurar o preço. Em 01/08/2026 ela rodou, publicou e o commit foi
        # rejeitado; agosto sumiu do site e só voltou em 01/09.
        if agora.day >= DIA_TOLERANCIA_PASSAGENS and f"captured-{agora:%Y-%m}" not in html:
            problemas.append(
                f"A captura de passagens de {agora:%m/%Y} não está no site. "
                "Ela roda todo dia 1; rodar o workflow radar-monthly-flights.yml resolve."
            )

    if not problemas:
        estado["ultimo_estado"] = "ok"
        salvar_estado(estado)
        print(f"Radar saudável às {agora:%d/%m %H:%M} (Chile).")
        return 0

    corpo = "\n".join(f"• {p}" for p in problemas)
    assinatura = "|".join(sorted(problemas))

    # Trava de repetição: sem ela, um defeito que dura o mês inteiro manda a
    # mesma mensagem 12 vezes por dia, e ela para de ser lida. Alarme novo
    # (assinatura diferente) fura a trava na hora.
    ultimo = estado.get("ultimo_alarme_em")
    mesma = estado.get("ultimo_alarme_assinatura") == assinatura
    if ultimo and mesma:
        try:
            passou = (agora - datetime.fromisoformat(ultimo)).total_seconds() / 3600
        except Exception:
            passou = 999
        if passou < HORAS_ENTRE_ALARMES:
            estado["ultimo_estado"] = "alarme (silenciado)"
            salvar_estado(estado)
            print(f"Mesmo alarme de {passou:.1f}h atrás, silenciado.\n{corpo}")
            return 1

    enviado = telegram(
        "🚨 Radar Chile parado\n\n"
        f"{corpo}\n\n"
        "Onde olhar primeiro: se os jobs do radar-chile morrem em segundos, "
        "é franquia de minutos do GitHub Actions ou cobrança recusada "
        "(Settings, Billing). Foi essa a causa do apagão de 27 a 31/08/2026.\n\n"
        f"{URL}"
    )
    estado["ultimo_estado"] = "alarme"
    if enviado:
        estado["ultimo_alarme_em"] = agora.isoformat(timespec="seconds")
        estado["ultimo_alarme_assinatura"] = assinatura
    salvar_estado(estado)
    print(("ALARME enviado:\n" if enviado else "ALARME NÃO ENVIADO (Telegram falhou):\n") + corpo)
    return 1


if __name__ == "__main__":
    sys.exit(main())

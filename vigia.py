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
atualização e a data do câmbio na própria página. Se o sintoma final aparece,
alarme, seja qual for a causa.
"""

import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

URL = "https://radar-chile.pages.dev/"
CHILE = timezone(timedelta(hours=-4))  # o horário de verão desloca 1h, e as
                                       # folgas abaixo absorvem isso de sobra.

# Folga antes de considerar parado. A janela de atualização do radar é 09h-17h
# no Chile, então de madrugada estar velho é o normal, não defeito.
LIMITE_SITE_DIA = 4      # horas, quando já passou da hora de ter atualizado
LIMITE_SITE_NOITE = 20   # horas, de madrugada: só alarma se perdeu o dia todo
LIMITE_CAMBIO = 30       # horas: o câmbio roda 3x/dia, 30h significa dia perdido


def telegram(msg: str) -> None:
    token, chat = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT")
    if not token or not chat:
        print("Sem credenciais do Telegram; não dá para avisar.", file=sys.stderr)
        return
    import json
    dados = json.dumps({"chat_id": chat, "text": msg}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=dados,
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=30).read()


def buscar() -> str | None:
    for tentativa in (1, 2, 3):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "radar-chile-vigia"})
            with urllib.request.urlopen(req, timeout=45) as r:
                if r.status != 200:
                    raise RuntimeError(f"HTTP {r.status}")
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            print(f"tentativa {tentativa} falhou: {e}", file=sys.stderr)
    return None


def idade_horas(dt: datetime, agora: datetime) -> float:
    return (agora - dt).total_seconds() / 3600


def main() -> int:
    agora = datetime.now(CHILE)
    html = buscar()

    if html is None:
        telegram(
            "🚨 Radar Chile fora do ar\n\n"
            f"O vigia não conseguiu abrir {URL} em três tentativas.\n"
            f"Verificado em {agora:%d/%m às %H:%M} no Chile."
        )
        return 1

    problemas = []

    m = re.search(r"atualizado em (\d{2})/(\d{2})/(\d{4}) às (\d{2}):(\d{2})", html)
    if not m:
        problemas.append("A página abriu, mas não tem carimbo de atualização nenhum.")
    else:
        d, mes, ano, hh, mm = (int(x) for x in m.groups())
        atualizado = datetime(ano, mes, d, hh, mm, tzinfo=CHILE)
        idade = idade_horas(atualizado, agora)
        limite = LIMITE_SITE_DIA if 12 <= agora.hour <= 23 else LIMITE_SITE_NOITE
        if idade > limite:
            problemas.append(
                f"O site não atualiza há {idade:.0f} horas "
                f"(última vez: {atualizado:%d/%m às %H:%M})."
            )

    c = re.search(r"cotação Wise · (\d{2})/(\d{2}) às (\d{2}):(\d{2})", html)
    if c:
        d, mes, hh, mm = (int(x) for x in c.groups())
        ano = agora.year
        cambio = datetime(ano, mes, d, hh, mm, tzinfo=CHILE)
        if cambio > agora + timedelta(days=1):   # virada de ano
            cambio = cambio.replace(year=ano - 1)
        idade_c = idade_horas(cambio, agora)
        if idade_c > LIMITE_CAMBIO:
            problemas.append(
                f"A cotação está congelada há {idade_c:.0f} horas "
                f"({cambio:%d/%m às %H:%M}) e o site mostra ela como se fosse de hoje."
            )

    if problemas:
        corpo = "\n".join(f"• {p}" for p in problemas)
        telegram(
            "🚨 Radar Chile parado\n\n"
            f"{corpo}\n\n"
            "Onde olhar primeiro: se os jobs do radar-chile morrem em segundos, "
            "é franquia de minutos do GitHub Actions ou cobrança recusada "
            "(Settings, Billing). Foi essa a causa do apagão de 27 a 31/08/2026.\n\n"
            f"{URL}"
        )
        print("ALARME enviado:\n" + corpo)
        return 1

    print(f"Radar saudável às {agora:%d/%m %H:%M} (Chile).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

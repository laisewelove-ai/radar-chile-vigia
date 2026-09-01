# Vigia do Radar Chile

Confere de quatro em quatro horas se o [Radar Chile](https://radar-chile.pages.dev/)
continua atualizando, e avisa a Laise no Telegram quando para.

## Por que isso mora fora do radar

O alerta do próprio radar vive dentro do job que ele mesmo roda. Quando o job
não chega a começar, não existe ninguém para avisar. Entre 27 e 31 de agosto de
2026 a franquia mensal de minutos do GitHub Actions acabou, o GitHub bloqueou
todos os jobs do radar por cinco dias, e o site ficou servindo a cotação de
26/08 rotulada como "hoje". Nenhum alerta saiu.

Este repositório é **público de propósito**: Actions em repositório público não
consome franquia de minutos, então o vigia continua de pé exatamente na
situação em que o radar cai.

Ele não lê log nem API: olha a página publicada, do mesmo jeito que qualquer
pessoa olharia, e alarma quando o carimbo de atualização ou a data da cotação
ficam velhos demais.

## O que dispara alarme

- A página não abre em três tentativas.
- O carimbo de atualização passa de 4 horas durante o dia, ou de 20 horas de
  madrugada (o radar só roda das 09h às 17h no Chile, então ficar velho à noite
  é o normal).
- A cotação do câmbio passa de 30 horas, que é o sintoma silencioso: o site
  segue no ar, bonito, mostrando número velho como se fosse de hoje.

## Segredos necessários

`TG_TOKEN` e `TG_CHAT`, nas configurações de Actions deste repositório. Nada
sensível vive no código.

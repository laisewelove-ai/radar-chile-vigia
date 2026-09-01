# Vigia do Radar Chile

Confere de duas em duas horas se o [Radar Chile](https://radar-chile.pages.dev/)
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
- O carimbo de atualização não é do dia corrente, cobrado a partir das 11h no
  Chile (a janela do radar abre às 09h, e as duas horas de folga absorvem
  atraso do agendador). Antes das 11h, vale a atualização de ontem.
- A cotação do câmbio não é do dia corrente, pelo mesmo critério. Esse é o
  sintoma silencioso: o site segue no ar, bonito, mostrando número velho como
  se fosse de hoje.
- A linha da cotação some da página. Sem esse caso, a checagem acima ficaria
  cega justamente quando o formato mudasse.
- A captura mensal de passagens do mês corrente não aparece no site a partir do
  dia 2. Ela roda todo dia 1 e é a falha mais fácil de passar batida, porque
  acontece uma vez por mês e só incomoda quando alguém vai procurar o preço.

## Por que ele grava `estado.json`

Duas razões, e as duas vieram de auditoria:

1. **Não repetir alarme.** Sem estado, um defeito que dura um mês manda a mesma
   mensagem 12 vezes por dia e para de ser lido. O mesmo alarme só volta depois
   de 12 horas; alarme diferente fura a trava na hora.
2. **Não se desligar sozinho.** O GitHub desativa workflow agendado depois de
   60 dias sem atividade no repositório, e este aqui, por desenho, nunca
   receberia commit. O estado é gravado uma vez por dia, o que mantém o
   repositório ativo. Um vigia que morre em silêncio é pior que vigia nenhum.

## Segredos necessários

`TG_TOKEN` e `TG_CHAT`, nas configurações de Actions deste repositório. Nada
sensível vive no código.

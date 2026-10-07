# Como a equipe de Social Media trabalhará para a Agrisul canaa

**Pacote reutilizável; configuração inicial pausada.** O repositório contém o desenho, instruções e ferramentas de preparação. Clonar não cria empresa, agentes, conexões ou rotinas. O bootstrap prepara os objetos na instalação escolhida e gera seus próprios IDs; as recomendações editoriais continuam propostas até a aprovação do contexto da marca.

## O trabalho que a empresa entrega

A operação transforma um pedido seu ou uma pauta selecionada em um pacote de conteúdo: imagens finais, sequência de slides quando houver, legenda, CTA, texto alternativo e identificação da versão aprovada. Instagram é o canal principal. Alguns Stories terão versão para WhatsApp, quando selecionados na pauta; Status continua sendo o destino assumido para esse reaproveitamento. Novas redes entram quando você solicitar.

O foco proposto é ajudar produtores rurais, fazendeiros e pecuaristas de Canaã dos Carajás e região a entender aplicações, preparar uma consulta e tomar uma decisão informada. Uma publicação precisa ensinar algo útil, apoiar uma escolha ou encaminhar uma demanda que a equipe consiga atender. Objetivos, diferenciais e tom da marca ainda precisam de definição final; a direção abaixo é proposta editorial, não uma promessa comercial comprovada.

## Quatro agentes, com responsabilidades diferentes

| Agente | Quando atua e o que recebe | Responsabilidade e entrega | Condição para avançar |
|---|---|---|---|
| Pesquisa e Inteligência de Conteúdo | Depois de admitir uma demanda; recebe contexto aprovado, tema, público e perguntas | Pesquisa fontes reais, identifica dúvidas, aplicações, oportunidades e limites; entrega dossiê com fontes, evidências e pautas candidatas | Editorial aceita a revisão da pesquisa e verifica os claims que serão usados |
| Coordenação Editorial | Na entrada, curadoria, aceite dos handoffs e revisão final; recebe o pedido e as entregas dos especialistas | Define objetivo, ângulo, prioridade, formato e CTA; prepara a pauta; acompanha dependências; decide se cada etapa pode avançar | Entrada completa, revisão identificada e critérios da etapa cumpridos; decisões humanas exigidas pela política continuam necessárias |
| Copywriting | Após pesquisa e pauta aceitas; recebe mensagem, evidências, formato, estrutura, voz e limites | Escreve hook, headlines, textos exatos por imagem/slide, legenda e CTA; não transforma hipótese em fato | Editorial aceita clareza, precisão, narrativa e adequação à marca antes do Design |
| Design e Direção Criativa | Após copy aceita; recebe textos, identidade, assets, formato e parâmetros de exportação | Define direção visual, produz/compõe as imagens, aplica o texto, inspeciona todos os arquivos e registra o pacote | Editorial revisa os arquivos reais, a copy aplicada, a identidade e a cadeia de revisões; aprovação humana quando configurada |

O Editorial justifica sua existência por concentrar a decisão de pauta, a coerência entre os especialistas e a revisão cruzada. A equipe não precisa de um quinto agente só para revisar. A especificação completa de cada papel, incluindo ferramentas, limites e condições de conclusão, está em [ARQUITETURA.md](ARQUITETURA.md).

## Uma demanda atravessa a mesma cadeia

`Pedido + contexto da marca → Pesquisa → Curadoria → Pauta → Copy → Direção criativa → Criação visual → Revisão → Pacote aprovado`

1. **Entrada:** você pode pedir “Crie uma campanha para este produto” ou “Quero um carrossel educativo sobre este assunto”. Editorial registra objetivo, produto/tema, canal, formato, prazo quando existir e restrições. Usa os dados conhecidos da marca; só solicita o que falta para a próxima etapa.
2. **Pesquisa:** o especialista parte das dúvidas relevantes ao público e consulta fontes adequadas ao assunto. Informações autorizadas ajudam a formular perguntas; afirmações técnicas exigem evidência apropriada. Uma hipótese editorial não comprova desempenho de equipamentos ou disponibilidade atual.
3. **Curadoria e pauta:** Editorial escolhe uma oportunidade com motivo explícito. Fixa público, mensagem, promessa permitida, formato, função dos slides e próximo passo. Não deixa o redator escolher sozinho entre um conjunto de pesquisas desconectadas.
4. **Copy:** o redator entrega os textos completos, vinculados aos claims e à revisão da pauta. Editorial confere antes de liberar Design.
5. **Produção visual:** Design usa a identidade e os assets autorizados, cria as peças e confere leitura no celular. Prompt ou direção visual não substituem o arquivo final. Geração/edição só será usada se a ferramenta estiver efetivamente conectada ao runtime.
6. **Revisão:** Editorial compara fonte, mensagem, texto, imagem, CTA e arquivos. Confere também estoque, condição ou prazo quando a peça contém uma oferta. Um bom layout não compensa uma promessa sem evidência.
7. **Entrega:** o pacote fica identificado e aprovado sobre uma versão exata. Aprovação significa pronto para entregar; agendamento, publicação, anúncios e envio de mensagens ainda não fazem parte do escopo autorizado.

Campanhas têm uma tarefa principal e peças filhas; a pesquisa pode ser compartilhada quando continuar pertinente. Um post isolado não precisa de campanha artificial. Uma versão de Story para WhatsApp referencia o conteúdo e a revisão de origem, adapta os elementos específicos do Instagram e passa por conferência própria.

## Contratos que evitam perda de informação

| Passagem | Entrada obrigatória para quem recebe |
|---|---|
| Pesquisa → Editorial/Pauta | Perguntas, fontes reais, trechos e páginas, afirmações classificadas, insights, oportunidades, lacunas e pautas sugeridas |
| Pauta aceita → Copy | Objetivo, público, dor/necessidade, ângulo, mensagem, evidências aceitas, promessa permitida, formato, estrutura, CTA e restrições |
| Copy aceita → Design | Hook, headline, texto exato e função de cada slide, ordem, legenda, CTA, claims utilizados, limites de espaço e revisões da marca/pauta/copy |
| Design → Revisão | Arquivos reais e preview, direção adotada, assets e permissões, textos aplicados, dimensões, ordem, fontes/receita editável, manifesto e versões utilizadas |
| Revisão → Entrega | Arquivos aprovados, legenda, CTA, alt text, sequência e decisões válidas sobre o mesmo pacote |

Todos os handoffs identificam demanda, responsável, documento/arquivo e revisão. Quem recebe confirma o aceite ou devolve feedback verificável; “pronto” em comentário não encerra uma etapa.

## Estados e retorno para a causa do erro

`IDEA → RESEARCHING → RESEARCHED → CURATING → BRIEF_READY → COPY_IN_PROGRESS → COPY_READY → DESIGN_IN_PROGRESS → DESIGN_READY → REVIEW → APPROVED`

Os estados editoriais ficam no documento `workflow`. O Paperclip mantém seus status nativos, dependências e gates. `READY` representa uma entrega proposta, que ainda pode ser devolvida. Há um validador local para contratos e transições; ele precisa ser chamado e não intercepta alterações diretas da API.

| Problema encontrado | Etapa responsável | O que precisa voltar a ser conferido |
|---|---|---|
| Fonte incorreta, dado vencido ou promessa sem evidência | Pesquisa | Claims e as partes da pauta/copy/design que dependem deles |
| Ângulo ou objetivo inadequado | Editorial/Pauta | Brief e saídas dependentes |
| Texto, tom, sequência ou CTA incorreto | Copy | Texto corrigido e visuais afetados |
| Cor, composição, asset, texto aplicado ou export incorreto | Design | Arquivos corrigidos e revisão final |

O feedback identifica a versão, o trecho/slide, o critério violado, a mudança pedida e como verificar a correção. A alteração invalida os aceites/aprovações dependentes; as partes preservadas continuam identificadas. Falta de informação ou ferramenta vira impedimento com condição de retomada, sem fingir que o conteúdo está concluído.

## Fatos do exemplo e direção editorial proposta

O usuário informou o nome Agrisul canaa, atuação em irrigação, máquinas e implementos agrícolas, ordenhadeiras, a região de Canaã dos Carajás e os públicos produtores rurais, fazendeiros e pecuaristas. Instagram é o canal inicial, com reaproveitamento selecionado de Stories no WhatsApp. Esses grupos podem se sobrepor; a informação não define marca/modelo, preço, estoque, modalidade de serviço ou perfil financeiro dos clientes.

**Linhas de conteúdo propostas para revisão:**

- Irrigação: o que levantar antes de pedir orçamento; dúvidas sobre aplicação e etapas de avaliação, com base técnica conferida.
- Máquinas e implementos: informações necessárias para discutir adequação ao trabalho; comparações só com modelos e especificações reais.
- Ordenhadeiras: dúvidas de compra e uso pertinentes à pecuária leiteira, sem presumir que todo pecuarista seja produtor de leite. Dados de equipamento e orientações sanitárias exigem fontes apropriadas.
- Cuidados e uso: orientações documentadas, dentro dos limites do fabricante; sem diagnóstico técnico remoto ou resultado garantido.
- Prova real da Agrisul: fotos, casos e depoimentos verdadeiros, com autorização e escopo claro, quando fornecidos.

**Tom proposto:** técnico acessível, direto, respeitoso e prático. Explicar o termo técnico quando necessário e convidar para uma avaliação do caso. Isso é uma recomendação de copy ainda não aprovada. O pacote mantém a proposta separada dos campos oficiais de voz em [CONTEXTO-MARCA.yaml](CONTEXTO-MARCA.yaml) e em [PROPOSTA-EDITORIAL.yaml](PROPOSTA-EDITORIAL.yaml).

**Exemplo de aplicação, sem peça produzida:** pedido de carrossel “O que informar antes de solicitar um orçamento de irrigação”. Pesquisa verifica os dados mínimos; Editorial define a mensagem “um orçamento útil começa com informações da área, água e energia”; Copy organiza a sequência; Design compõe as imagens; revisão impede inserir dimensionamento ou prazo sem validação. O CTA comercial só é definido após confirmar o contato e quem recebe a consulta.

## Preparação e condições para produzir

O pacote contém arquitetura, instruções dos quatro agentes, playbook e ferramentas locais. Após executar o bootstrap autorizado, confira os objetos criados e seus recibos: empresa, agentes e rotinas devem permanecer pausados, sem disparar modelos. O processo de preparação não gera criativos finais nem aprova a marca automaticamente. A implantação está descrita em [plano de implementação](../../doc/plans/2026-10-07-social-media-company-implementation.md).

Antes de produzir, fornecer identidade e assets autorizados, contatos/destinos de atendimento, catálogo atual quando necessário, direção editorial aprovada, orçamento e ferramentas verificadas. O exemplo não inclui logo, paleta, tipografia ou fotos oficiais. Falta também fixar formato/exportação e aprovação de cada tipo de conteúdo. Depois, publicar o contexto pelo fluxo de governança e executar o piloto com arquivos reais; recorrência só começa conforme capacidade, calendário e resultado verificados.

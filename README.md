## Boleto/CNAB 240 para o Bank Of America
Este repositório contém a implementação para geração de boletos emissão/recebimento de CNAB 240 para o Bank Of America.
Tanto a formatação do CNAB 240 quanto o layout do Boleto foram validados pelo banco.

#### Instruções para instalação das bibliotecas.
* O primeiro passo é remover as bibliotecas Boleto e Cnab antigas, caso hajam.
Os comandos "pip uninstall python-boleto" e "pip uninstall python-cnab" realizarão este procedimento.
* Clonar as bibliotecas do Git Hub na pasta desejada.
* Após isso basta instalar as bibliotecas a partir da pasta na qual elas foram clonadas do git. O comando "sudo pip install -e /diretorio/onde/seencontra/biblioteca" realizará a instalação das bibliotecas. Lembrando que este procedimento deve ser realizado uma vez para cada pacote Python que se deseja instalar

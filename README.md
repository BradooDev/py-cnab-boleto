### Boleto/CNAB 240 para o Bank Of America
Este repositório contém a implementação para geração de boletos emissão/recebimento de CNAB 240 para o Bank Of America.
Tanto a formatação do CNAB 240 quanto o layout do Boleto foram validados pelo banco.

#### Instruções para instalação das bibliotecas.

* O primeiro passo é remover as bibliotecas Boleto e Cnab antigas, caso hajam.
```
sudo pip uninstall python-boleto
sudo pip uninstall python-cnab
sudo pip uninstall pyparsing
sudo pip install pyparsing
```
As últimas duas linhas a cima são para corrigir um problema na lista de dependências de metadata do pip

* Clonar as bibliotecas do Git Hub.
```
git clone https://github.com/BradooDev/py-cnab-boleto
```
* Após isso basta instalar as bibliotecas a partir da pasta na qual elas foram clonadas do git. O comando "sudo pip install -e /diretorio/onde/seencontra/biblioteca" realizará a instalação das bibliotecas. Lembrando que este procedimento deve ser realizado uma vez para cada pacote Python que se deseja instalar
```
sudo pip install -e /home/py-cnab-boleto/python-cnab/
sudo pip install -e /home/py-cnab-boleto/python-boleto/
```



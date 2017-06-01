#!/bin/bash

sudo pip uninstall python-boleto
sudo pip uninstall python-cnab
sudo pip uninstall pyparsing
sudo pip install pyparsing

cd /home/
git clone https://github.com/BradooDev/py-cnab-boleto

sudo pip install -e /home/py-cnab-boleto/python-cnab/
sudo pip install -e /home/py-cnab-boleto/python-boleto/
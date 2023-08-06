from sys import platform
import wget
import zipfile
import os

save_as = "./OAT.zip"

if platform == "linux" or platform == "linux2":
    url = 'https://docs.optano.com/algorithm.tuner/current/OPTANO.Algorithm.Tuner.Application.2.1.0_linux-x64.zip'
elif platform == "darwin":
    x=1
elif platform == "win32":
    x=1
if not os.path.isdir('OAT'):
    wget.download(url, out = save_as)
if os.path.isfile('OAT.zip'):
    with zipfile.ZipFile('OAT.zip', 'r') as zip_ref:
        zip_ref.extractall('./OAT')


print(platform)
# witb (where in the bible?)

Prerequisites
```bash
sudo apt-get update
sudo apt-get install -y g++ gcc build-essential

sudo apt update && sudo apt install -y python-3.12 python3.12-venv
```
Setup
```bash
git clone https://github.com/wakrson/witb
cd witb
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

Usage
```bash
# Parse Bible
python -m witb.parse --data=/path/to/pdf
```

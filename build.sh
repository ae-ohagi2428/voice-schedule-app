#!/usr/bin/env bash
# Exit on error
set -o errexit

# パッケージをインストール
pip install -r requirements.txt

(cd theme/static_src && npm install)
python manage.py tailwind build

python manage.py collectstatic --no-input

python manage.py migrate
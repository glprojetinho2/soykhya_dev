from utils import soyquery
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument(
    "query",
    type=str,
    help="Query SQL para consultar o banco do Soynkhya.",
)
args = parser.parse_args()

print(json.dumps(soyquery(args.query), indent=4))

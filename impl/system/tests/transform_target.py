import csv
import json
import ast

input_csv = "tests/data/target.csv"
output_json = "tests/target_queries.json"


def clean_text(text):
    return text.replace("_", " ").replace(":", " ").replace("/", " ").strip()


def main():
    queries = []
    with open(input_csv, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            query = row["query"]
            contracts = ast.literal_eval(row["contract_ids"])
            cleaned = clean_text(query)
            queries.append(
                {
                    "id": query,
                    "query": cleaned,
                    "description": cleaned,
                    "expected_results": {"contract_ids": contracts},
                }
            )
    with open(output_json, "w") as f:
        json.dump({"queries": queries}, f, indent=2)


if __name__ == "__main__":
    main()

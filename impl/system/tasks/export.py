import json
import csv
import os

INPUT_PATH = os.path.join(
    os.path.dirname(__file__), "../data/retrieved_enriched_contracts.json"
)
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "../data/exported.csv")

FIELDS = [
    "uid",
    "ContractDeployment.storage_protocol",
    "ContractDeployment.storage_address",
    "ContractDeployment.experimental",
    "ContractDeployment.solc_version",
    "ContractDeployment.verified_source",
    "ContractDeployment.verified_source_code",
    "ContractDeployment.name",
    "ContractDeployment.description",
    "ContractDeployment.functionality_classification",
    "ContractDeployment.application_domain",
    "ContractDeployment.security_risks_description",
]


def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDS)
        writer.writeheader()
        for item in data:
            row = {field: item.get(field, "") for field in FIELDS}
            writer.writerow(row)
    print(f"Exported {len(data)} contracts to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

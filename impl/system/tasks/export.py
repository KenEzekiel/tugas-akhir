import json
import csv
import os

INPUT_PATH = os.path.join(
    os.path.dirname(__file__), "../data/retrieved_enriched_contracts.json"
)
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "../data/exported.csv")

FIELDS = [
    "uid",
    "ContractDeployment.id",
    "ContractDeployment.storage_protocol",
    "ContractDeployment.storage_address",
    "ContractDeployment.experimental",
    "ContractDeployment.solc_version",
    "ContractDeployment.verified_source",
    "ContractDeployment.name",
    "ContractDeployment.description",
    "ContractDeployment.functionality_classification",
    "ContractDeployment.application_domain",
    "ContractDeployment.security_risks_description",
]


def format_value(value):
    """Convert list values to semicolon-separated strings for CSV compatibility."""
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return value


def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDS)
        writer.writeheader()
        for item in data:
            row = {field: format_value(item.get(field, "")) for field in FIELDS}
            writer.writerow(row)
    print(f"Exported {len(data)} contracts to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

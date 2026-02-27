import os
import yaml
import requests


def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_domains(api_base: str, api_key: str):
    resp = requests.get(f"{api_base}/api/config", headers={
        "X-API-Key": api_key,
    }, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data["emailDomains"].split(",")


if __name__ == "__main__":
    cfg = load_config()
    domains = get_domains(cfg["email_api"], cfg["email_api_key"])
    print(f"共 {len(domains)} 个域名:\n")
    for i, d in enumerate(domains, 1):
        print(f"  {i}. {d}")

# utils/spec_loader.py
import requests
import yaml
import json

def load_spec_from_url(url: str) -> dict:
    """Loads an OpenAPI spec from a URL, trying YAML then JSON."""
    try:
        print(f"Attempting to load OpenAPI spec from: {url}")
        response = requests.get(url)
        response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)

        content = response.content
        # Try loading as YAML first
        try:
            spec = yaml.safe_load(content)
            print("Successfully loaded spec as YAML.")
            if not isinstance(spec, dict):
                 raise ValueError("Loaded YAML content is not a dictionary.")
            return spec
        except yaml.YAMLError:
            # If YAML fails, try JSON
            try:
                spec = json.loads(content)
                print("Successfully loaded spec as JSON.")
                if not isinstance(spec, dict):
                     raise ValueError("Loaded JSON content is not a dictionary.")
                return spec
            except json.JSONDecodeError as json_err:
                print(f"Failed to parse content as YAML or JSON: {json_err}")
                raise ValueError(f"Could not parse OpenAPI spec file from {url}") from json_err

    except requests.exceptions.RequestException as e:
        print(f"Error fetching OpenAPI spec from URL: {e}")
        raise ConnectionError(f"Failed to fetch spec from {url}") from e
    except Exception as e:
        print(f"An unexpected error occurred during spec loading: {e}")
        raise RuntimeError("Failed during spec loading.") from e
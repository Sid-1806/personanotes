import httpx
import time

BASE_URL = "http://localhost:8000/api/v1"


def test_pipeline():
    print("=== Testing Continual Learning Pipeline ===\n")

    with httpx.Client(timeout=60.0) as client:
        # 1. Generate a note
        print("1. Generating an initial note...")
        gen_resp = client.post(
            f"{BASE_URL}/notes/generate",
            json={"prompt": "Explain what a neural network is."},
        )
        gen_data = gen_resp.json()
        note_id = gen_data.get("id")
        print(f"Generated Note ID: {note_id}")
        print(f"Content preview: {gen_data['notes'][:100]}...\n")

        # 2. User edits the note
        print("2. Simulating a user edit (adding code blocks and bullets)...")
        edited_markdown = (
            gen_data["notes"]
            + "\n\n### Examples\nHere are some examples:\n- Example 1\n- Example 2\n\n```python\nprint('Hello Neural Net')\n```\n"
        )

        # 3. Submit feedback
        print("3. Submitting edited note to feedback pipeline...")
        feedback_resp = client.post(
            f"{BASE_URL}/notes/{note_id}/feedback",
            json={"edited_markdown": edited_markdown},
        )
        print(f"Updated Features: {feedback_resp.json().get('updated_features')}\n")

        # 4. Check Explainability endpoint
        print("4. Fetching style explanations...")
        explain_resp = client.get(f"{BASE_URL}/style/explain")
        explain_data = explain_resp.json()

        print("\n=== Current Style Profile (Explainability) ===")
        for key, details in explain_data.items():
            if (
                details.get("confidence", 0) > 0.5
            ):  # Only show ones with decent confidence or that were updated
                print(f"Feature: {key}")
                print(f"  Value: {details['value']}")
                print(f"  Reason: {details['reason']}")
                print(f"  Confidence: {details['confidence']:.2f}\n")


if __name__ == "__main__":
    test_pipeline()

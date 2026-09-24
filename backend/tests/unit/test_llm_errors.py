"""Provider failures must produce advice the user can act on.

"Please retry" is the wrong thing to say when the provider has told us the
quota is exhausted for the next 46 seconds, and it's the wrong thing to say
when the configured model no longer exists.
"""

from app.services.llm_service import describe_llm_error


def test_free_tier_quota_names_the_cause_and_the_wait():
    message = describe_llm_error(
        Exception(
            "429 You exceeded your current quota. Quota exceeded for metric: "
            "generate_content_free_tier_requests, limit: 20. "
            "Please retry in 46.268250555s."
        )
    )

    assert "free-tier quota" in message
    assert "46s" in message
    # Bare "please retry" is exactly the advice that fails here.
    assert "Please retry." not in message


def test_generic_rate_limit_without_a_delay_still_says_to_wait():
    message = describe_llm_error(Exception("429 rate limit exceeded"))

    assert "rate-limiting" in message
    assert "shortly" in message


def test_retired_model_points_at_the_setting_to_change():
    message = describe_llm_error(
        Exception("404 This model models/gemini-2.5-flash is no longer available")
    )

    assert "GEMINI_MODEL" in message


def test_bad_key_is_named_as_a_key_problem():
    message = describe_llm_error(Exception("401 API key not valid"))

    assert "API key" in message


def test_unrecognised_failure_falls_back_to_a_plain_retry():
    message = describe_llm_error(Exception("connection reset by peer"))

    assert message == "The AI service failed partway through. Please retry."


def test_seconds_are_parsed_from_the_structured_retry_delay():
    message = describe_llm_error(
        Exception("429 quota exceeded [retry_delay { seconds: 14 }]")
    )

    assert "14s" in message

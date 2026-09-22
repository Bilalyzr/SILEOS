"""Opt-in error reporting with explicit privacy controls."""
def scrub_event(event, hint):
    request = event.get("request")
    if request:
        # No tokens, cookies, query arguments, request bodies or user identity.
        for key in ("headers", "cookies", "query_string", "data", "env"):
            request.pop(key, None)
        if request.get("url"):
            request["url"] = request["url"].split("?", 1)[0]
    event.pop("user", None)
    event.pop("breadcrumbs", None)
    # SQL parameters can include credential material or personal data.
    event.pop("extra", None)
    event.pop("spans", None)
    for exception in event.get("exception", {}).get("values", []):
        exception["value"] = "Exception details retained in private server diagnostics"
        for frame in exception.get("stacktrace", {}).get("frames", []):
            frame.pop("vars", None)
    return event


def configure(settings):
    if not settings.SENTRY_DSN:
        return
    import sentry_sdk
    sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT,
        send_default_pii=False, traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        before_send=scrub_event, before_send_transaction=scrub_event,
        include_local_variables=False)

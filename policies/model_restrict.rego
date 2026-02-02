# YORI Policy: Model Restrictions
# @description Restrict usage to specific AI models (cost control)
# @author YORI Team
# @version 1.0.0

package yori.policies.model_restrict

default allow = true
default block = false
default alert = false

# Allowed models (cost-effective choices)
allowed_models = {
    "gpt-4o-mini",
    "gpt-3.5-turbo",
    "claude-3-haiku",
    "claude-3.5-sonnet",
    "gemini-1.5-flash",
    "mistral-small",
}

# Premium models that trigger alerts
premium_models = {
    "gpt-4",
    "gpt-4-turbo",
    "claude-3-opus",
    "mistral-large",
}

# Block unknown expensive models
block if {
    model := lower(input.model)
    not model_allowed(model)
    not model_premium(model)
}

# Alert on premium model usage
alert if {
    model := lower(input.model)
    model_premium(model)
}

# Helper: check if model is in allowed list
model_allowed(model) if {
    some allowed in allowed_models
    contains(model, allowed)
}

# Helper: check if model is premium
model_premium(model) if {
    some premium in premium_models
    contains(model, premium)
}

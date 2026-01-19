package yori.homework_helper

# Homework Helper policy: Detect educational/homework-related queries
# Helps parents monitor when children might be using AI for homework

import rego.v1

# Get the prompt text from input
prompt := lower(input.prompt) if {
	input.prompt
} else := lower(input.messages[_].content) if {
	input.messages
} else := ""

# Educational keywords that might indicate homework
homework_keywords := [
	"homework", "assignment", "essay", "paper", "report",
	"study", "exam", "test", "quiz", "problem set",
	"solve", "calculate", "prove", "explain", "analyze",
	"summarize", "compare", "contrast", "discuss",
	"thesis", "research", "bibliography", "citation",
]

# Math/science keywords
academic_keywords := [
	"equation", "formula", "theorem", "proof", "derivative",
	"integral", "matrix", "vector", "molecule", "atom",
	"chemistry", "physics", "biology", "calculus", "algebra",
	"geometry", "trigonometry", "statistics",
]

# Check if prompt contains homework keywords
contains_homework_keywords if {
	some keyword in homework_keywords
	contains(prompt, keyword)
}

# Check if prompt contains academic keywords
contains_academic_keywords if {
	some keyword in academic_keywords
	contains(prompt, keyword)
}

# Detect if this might be homework-related
is_homework_related if {
	contains_homework_keywords
} else if {
	contains_academic_keywords
}

# Extract matched keywords for reporting
matched_keywords := keywords if {
	all_matches := {keyword |
		keyword := homework_keywords[_]
		contains(prompt, keyword)
	} | {keyword |
		keyword := academic_keywords[_]
		contains(prompt, keyword)
	}
	keywords := [k | k := all_matches[_]]
}

# Get time of day if available
hour := input.hour if {
	input.hour
} else := 12  # Default to daytime

# During school hours (8 AM - 3 PM on weekdays)
is_school_hours if {
	hour >= 8
	hour < 15
	# Could also check day of week if available
}

# Allow the request (advisory mode - log but don't block)
allow := true

# Mode: advisory if homework detected
mode := "advisory" if {
	is_homework_related
} else := "observe"

# Reason with context
reason := sprintf("Potential homework-related query detected (keywords: %s)", [concat(", ", matched_keywords)]) if {
	is_homework_related
	count(matched_keywords) > 0
} else := "Potential homework-related query detected" if {
	is_homework_related
} else := "No homework keywords detected"

# Metadata for parent dashboard
metadata := {
	"policy_version": "1.0.0",
	"policy_type": "homework_detection",
	"homework_detected": is_homework_related,
	"matched_keywords": matched_keywords,
	"keyword_count": count(matched_keywords),
	"during_school_hours": is_school_hours,
	"alert_triggered": is_homework_related,
	"user": input.user,
	"device": input.device,
	"hour": hour,
	"timestamp": time.now_ns(),
} if {
	is_homework_related
}

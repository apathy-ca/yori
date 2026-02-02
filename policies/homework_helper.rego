# YORI Policy: Homework Helper
# @description Track educational keywords in prompts
# @author YORI Team
# @version 1.0.0

package yori.policies.homework_helper

default allow = true
default alert = false

# Educational keywords to track
educational_keywords = {
    "homework", "essay", "math", "science", "history",
    "solve", "explain", "calculate", "write my", "help with"
}

# Alert when educational keywords detected
alert if {
    some keyword in educational_keywords
    contains(lower(input.prompt), keyword)
}

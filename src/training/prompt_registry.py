from typing import Dict, Any

class PromptRegistry:
    \"\"\"Handles versioning and interpolation of system and agent prompts.\"\"\"

    def __init__(self):
        self.prompts = {
            "v1.0.0": {
                "writer": (
                    "You are a professional copywriter. Draft a cold email to {name} at {company} "
                    "focusing on their pain points: {pain_points}."
                ),
                "scorer": "Evaluate this lead profile against our target ICP: {icp}."
            },
            "v1.1.0": {
                "writer": (
                    "You are a sales specialist. Draft a hyper-personalized email to {name} (Role: {role}) "
                    "at {company}. Use a PAS framework. Lead details: {details}."
                ),
                "scorer": "Score this lead profile against ICP parameters: {icp} on a scale of 0-100."
            }
        }

    def get_prompt(self, version: str, agent_name: str, variables: Dict[str, Any]) -> str:
        version_prompts = self.prompts.get(version)
        if not version_prompts:
            raise ValueError(f"Prompt version {version} not found in registry")
            
        template = version_prompts.get(agent_name)
        if not template:
            raise ValueError(f"Agent {agent_name} not found in version {version}")
            
        return template.format(**variables)

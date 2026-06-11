from typing import List, Dict, Any

class TrainingDataPreparator:
    \"\"\"Prepares outreach datasets for fine-tuning LLMs.\"\"\"

    def prepare_instruction_dataset(self, success_emails: List[Dict[str, Any]], output_path: str):
        formatted_data = []
        
        for email in success_emails:
            prompt = (
                f"Write a personalized cold email to a lead with the following profile:\\n"
                f"Name: {email.get('lead_name')}\\n"
                f"Company: {email.get('company')}\\n"
                f"Role: {email.get('role')}\\n"
                f"Tech Stack: {', '.join(email.get('tech_stack', []))}\\n"
                f"Pain Points: {', '.join(email.get('pain_points', []))}\\n"
            )
            response = email.get("body", "")
            
            # Instruction-tuning format
            formatted_data.append({
                "instruction": prompt,
                "input": "",
                "output": response
            })
            
        import json
        with open(output_path, "w") as f:
            json.dump(formatted_data, f, indent=2)
            
        return len(formatted_data)

"""Customizable prompt templates for Claude AI interactions"""

from typing import Dict, Any, Optional, List
import json


def convert_prompt_to_messages(prompt_string: str) -> List[Dict[str, str]]:
    """Convert old format prompt string to new SDK message format.
    
    Attempts to split the prompt into system and user messages by looking for
    common patterns. If no clear split is found, treats entire prompt as user message.
    
    Args:
        prompt_string: The combined prompt string in old format
        
    Returns:
        List of message dicts with 'role' and 'content' keys
    """
    # Common patterns that indicate start of user content
    user_markers = [
        "\n\nHTML Content:",
        "\n\nAnalyze the following",
        "\n\nGenerate appropriate answers",
        "\n\nExtract the following",
        "\n\nQuestion:",
        "\n\nFocus on identifying:",
        "\n\nYour task is to"
    ]
    
    # Try to find a user content marker
    split_index = -1
    for marker in user_markers:
        if marker in prompt_string:
            split_index = prompt_string.find(marker)
            break
    
    # If we found a split point, separate system and user
    if split_index > 0:
        system_content = prompt_string[:split_index].strip()
        user_content = prompt_string[split_index:].strip()
        
        messages = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": user_content})
        return messages
    
    # Otherwise, check if it starts with a system-like message
    if prompt_string.startswith("You are"):
        # Find the end of the first paragraph as system message
        first_para_end = prompt_string.find("\n\n")
        if first_para_end > 0:
            return [
                {"role": "system", "content": prompt_string[:first_para_end].strip()},
                {"role": "user", "content": prompt_string[first_para_end:].strip()}
            ]
    
    # Default: treat entire prompt as user message
    return [{"role": "user", "content": prompt_string}]


class PromptTemplates:
    """Manage and customize prompt templates for different extraction tasks"""
    
    def __init__(self):
        self.templates = {
            "info_extraction": InfoExtractionTemplate(),
            "question_extraction": QuestionExtractionTemplate(),
            "answer_generation": AnswerGenerationTemplate()
        }
    
    def get_template(self, template_name: str) -> 'BaseTemplate':
        """Get a specific template by name"""
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")
        return self.templates[template_name]
    
    def customize_template(self, template_name: str, customizations: Dict[str, Any]):
        """Apply customizations to a template"""
        template = self.get_template(template_name)
        template.customize(customizations)


class BaseTemplate:
    """Base class for all prompt templates"""
    
    def __init__(self):
        self.system_prompt = ""
        self.user_prompt_template = ""
        self.output_format = {}
        self.examples = []
    
    def customize(self, customizations: Dict[str, Any]):
        """Apply customizations to the template"""
        if "system_prompt" in customizations:
            self.system_prompt = customizations["system_prompt"]
        if "output_format" in customizations:
            self.output_format.update(customizations["output_format"])
        if "examples" in customizations:
            self.examples.extend(customizations["examples"])
    
    def format_prompt(self, **kwargs) -> str:
        """Format the complete prompt with provided data"""
        prompt_parts = []
        
        # Add system prompt
        if self.system_prompt:
            prompt_parts.append(self.system_prompt)
        
        # Add output format instructions
        if self.output_format:
            prompt_parts.append(self._format_output_instructions())
        
        # Add examples if any
        if self.examples:
            prompt_parts.append(self._format_examples())
        
        # Add the main prompt
        prompt_parts.append(self.user_prompt_template.format(**kwargs))
        
        return "\n\n".join(prompt_parts)
    
    def format_messages(self, **kwargs) -> List[Dict[str, str]]:
        """Format prompts as message array for SDK compatibility.
        
        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        messages = []
        
        # Build system message content
        system_parts = []
        if self.system_prompt:
            system_parts.append(self.system_prompt)
        
        # Add output format instructions to system message
        if self.output_format:
            system_parts.append(self._format_output_instructions())
        
        # Add examples to system message
        if self.examples:
            system_parts.append(self._format_examples())
        
        # Add system message if we have content
        if system_parts:
            messages.append({
                "role": "system",
                "content": "\n\n".join(system_parts)
            })
        
        # Add user message
        messages.append({
            "role": "user",
            "content": self.user_prompt_template.format(**kwargs)
        })
        
        return messages
    
    def _format_output_instructions(self) -> str:
        """Format output structure instructions"""
        return f"Return your response as a valid JSON object with the following structure:\n{json.dumps(self.output_format, indent=2)}"
    
    def _format_examples(self) -> str:
        """Format examples section"""
        if not self.examples:
            return ""
        
        examples_text = "Examples:\n"
        for i, example in enumerate(self.examples, 1):
            examples_text += f"\nExample {i}:\n"
            examples_text += f"Input: {example.get('input', 'N/A')}\n"
            examples_text += f"Output: {json.dumps(example.get('output', {}), indent=2)}\n"
        
        return examples_text


class InfoExtractionTemplate(BaseTemplate):
    """Template for extracting information from websites"""
    
    def __init__(self):
        super().__init__()
        
        self.system_prompt = """You are an expert at analyzing web pages and extracting structured information about applications, programs, and opportunities. You focus on accuracy and completeness while organizing information in a clear, structured format."""
        
        self.user_prompt_template = """Analyze the following webpage content and extract all relevant information about the application or program.

Focus on identifying:
- Program details (name, description, purpose)
- Eligibility criteria and requirements
- Important dates and deadlines
- Benefits and opportunities offered
- Application process and steps
- Required documents and materials
- Contact information and support resources
- Any special notes or important details

Be thorough but concise. Extract factual information as presented on the page.

HTML Content:
{html_content}"""
        
        self.output_format = {
            "program_name": "string - The official name of the program",
            "description": "string - A comprehensive description of the program",
            "program_type": "string - Type of program (grant, scholarship, fellowship, etc.)",
            "eligibility": {
                "requirements": ["array of eligibility requirements"],
                "restrictions": ["array of restrictions or disqualifying factors"],
                "target_audience": "string - Who this program is designed for"
            },
            "dates": {
                "application_deadline": "string - Application deadline (ISO format if possible)",
                "program_start": "string - When the program begins",
                "program_end": "string - When the program ends",
                "notification_date": "string - When applicants will be notified",
                "other_dates": {"key": "value for any other important dates"}
            },
            "benefits": ["array of benefits provided by the program"],
            "funding_amount": "string or null - Amount of funding if applicable",
            "application_process": ["array of steps in the application process"],
            "required_documents": ["array of required documents"],
            "selection_criteria": ["array of how applications are evaluated"],
            "contact": {
                "email": "string or null",
                "phone": "string or null", 
                "website": "string or null",
                "address": "string or null"
            },
            "additional_info": "string - Any other important information not captured above",
            "source_url": "string - The URL this information was extracted from"
        }


class QuestionExtractionTemplate(BaseTemplate):
    """Template for extracting form questions from application pages"""
    
    def __init__(self):
        super().__init__()
        
        self.system_prompt = """You are an expert at analyzing HTML forms and extracting all interactive elements that require user input. You understand various form patterns and can identify questions even when they're not in traditional form tags."""
        
        self.user_prompt_template = """Analyze the following application form webpage and extract ALL questions and input fields.

Your task is to identify:
1. Every question or prompt that requires user input
2. The type of input expected (text, selection, file upload, etc.)
3. Whether the field appears to be required
4. Any constraints or validation rules
5. Helper text or additional instructions
6. How questions are grouped or organized

Look for:
- Traditional form inputs (input, textarea, select)
- Custom form components (divs/spans with form-like behavior)
- File upload areas
- Radio buttons and checkboxes
- Hidden required fields
- Multi-step form indicators

Important: Extract the actual question text as users would see it, not just field names.

HTML Content:
{html_content}"""
        
        self.output_format = [
            {
                "question": "The question or label text as shown to users",
                "field_name": "HTML name/id attribute if available",
                "type": "text|textarea|select|radio|checkbox|file|email|tel|number|date|url|hidden",
                "required": "boolean - true if field is required",
                "placeholder": "Placeholder text if any",
                "options": ["For select/radio/checkbox - list of available options"],
                "constraints": {
                    "max_length": "number or null",
                    "min_length": "number or null",
                    "pattern": "regex pattern if any",
                    "max_file_size": "for file uploads",
                    "allowed_file_types": ["for file uploads"],
                    "other": "any other constraints"
                },
                "section": "Section or group this question belongs to",
                "help_text": "Any helper text or instructions for this field",
                "default_value": "Default value if any",
                "depends_on": "Field name this question depends on (for conditional fields)"
            }
        ]


class AnswerGenerationTemplate(BaseTemplate):
    """Template for generating answers based on extracted information"""
    
    def __init__(self):
        super().__init__()
        
        self.system_prompt = """You are an expert at filling out application forms. You generate appropriate, professional answers based on available information while being honest about what information is missing or uncertain."""
        
        self.user_prompt_template = """Generate appropriate answers for the application form questions based on the program information provided.

Guidelines:
1. Use information from the program details when directly relevant
2. Be concise but complete - respect any length constraints
3. Maintain a professional, appropriate tone
4. For questions lacking clear answers, provide reasonable placeholders
5. Never fabricate specific details (names, dates, numbers)
6. Flag answers that need user review with lower confidence

Consider:
- Match the tone and style expected for this type of application
- Respect character/word limits if specified
- Provide structured responses for complex questions
- Use proper formatting for lists or multi-part questions

Application Information:
{application_info}

Questions to Answer:
{questions}"""
        
        self.output_format = [
            {
                "question": "The original question text",
                "field_name": "Field identifier if available",
                "answer": "Your generated answer",
                "confidence": "high|medium|low - your confidence in this answer",
                "needs_review": "boolean - true if user should review/edit",
                "notes": "Any caveats, assumptions, or guidance for the user",
                "alternatives": ["Optional alternative answers if applicable"]
            }
        ]


class CustomizablePromptBuilder:
    """Build and customize prompts for specific use cases"""
    
    @staticmethod
    def build_focused_extraction_prompt(
        html_content: str,
        focus_areas: list,
        output_fields: dict
    ) -> str:
        """Build a focused extraction prompt for specific information"""
        
        prompt = f"""Extract the following specific information from the webpage:

Focus Areas:
{json.dumps(focus_areas, indent=2)}

Required Output Fields:
{json.dumps(output_fields, indent=2)}

Instructions:
- Only extract information related to the focus areas
- Use null for any fields where information is not found
- Be precise and factual

HTML Content:
{html_content[:8000]}"""
        
        return prompt
    
    @staticmethod
    def build_focused_extraction_messages(
        html_content: str,
        focus_areas: list,
        output_fields: dict
    ) -> List[Dict[str, str]]:
        """Build focused extraction messages in SDK format"""
        
        system_content = f"""You are an expert at extracting specific information from web pages.

Required Output Fields:
{json.dumps(output_fields, indent=2)}

Instructions:
- Only extract information related to the focus areas
- Use null for any fields where information is not found
- Be precise and factual
- Return your response as valid JSON"""
        
        user_content = f"""Extract the following specific information from the webpage:

Focus Areas:
{json.dumps(focus_areas, indent=2)}

HTML Content:
{html_content[:8000]}"""
        
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
    
    @staticmethod
    def build_contextual_answer_prompt(
        question: str,
        context: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build a prompt for answering a single question with context"""
        
        prompt = f"""Generate an appropriate answer for this application question using the provided context.

Question: {question}

Available Context:
{json.dumps(context, indent=2)}
"""
        
        if constraints:
            prompt += f"\nConstraints:\n{json.dumps(constraints, indent=2)}"
        
        prompt += """

Provide your answer in this format:
{
  "answer": "Your answer here",
  "confidence": "high|medium|low",
  "explanation": "Brief explanation of your answer"
}"""
        
        return prompt
    
    @staticmethod
    def build_contextual_answer_messages(
        question: str,
        context: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Build contextual answer messages in SDK format"""
        
        system_content = """You are an expert at answering application questions using provided context.

Provide your answer in this format:
{
  "answer": "Your answer here",
  "confidence": "high|medium|low",
  "explanation": "Brief explanation of your answer"
}"""
        
        user_content = f"""Generate an appropriate answer for this application question using the provided context.

Question: {question}

Available Context:
{json.dumps(context, indent=2)}"""
        
        if constraints:
            user_content += f"\n\nConstraints:\n{json.dumps(constraints, indent=2)}"
        
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
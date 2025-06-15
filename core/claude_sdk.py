"""Claude Code SDK wrapper that mimics the ClaudeMCP interface"""
import anyio
import time
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime
from claude_code_sdk import query

from .utils import url_cache, create_error_response, safe_json_parse, chunk_text


class ClaudeMCPError(Exception):
    """Custom exception for Claude SDK errors"""
    def __init__(self, message: str, error_type: str = "claude_error", details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}


class ClaudeSDK:
    """Wrapper for Claude Code SDK that mimics the ClaudeMCP interface
    
    This class provides a synchronous interface to the async Claude Code SDK,
    maintaining compatibility with the existing ClaudeMCP API.
    """
    
    def __init__(self, work_folder: Optional[str] = None, timeout: int = 60, use_cache: bool = True):
        self.work_folder = work_folder or "."
        self.timeout = timeout
        self.use_cache = use_cache
        self._stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "cache_hits": 0,
            "total_processing_time": 0
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Claude SDK usage statistics"""
        stats = self._stats.copy()
        if stats["total_calls"] > 0:
            stats["average_processing_time"] = stats["total_processing_time"] / stats["total_calls"]
        else:
            stats["average_processing_time"] = 0
        return stats
    
    def _generate_cache_key(self, prompt: str) -> str:
        """Generate cache key for prompt"""
        return f"claude:{hashlib.md5(prompt.encode()).hexdigest()}"
    
    async def _async_call_claude(self, prompt: str) -> str:
        """Async method to call Claude SDK"""
        messages = []
        
        try:
            async for message in query(prompt=prompt):
                # Handle different message types from SDK
                if hasattr(message, 'text'):
                    messages.append(message.text)
                elif isinstance(message, str):
                    messages.append(message)
                elif isinstance(message, dict) and 'text' in message:
                    messages.append(message['text'])
                else:
                    messages.append(str(message))
        except Exception as e:
            # Log error but try to return what we have
            if messages:
                return "".join(messages)
            raise e
        
        # Combine all messages into a single response
        return "".join(messages)
    
    def call_claude(self, prompt: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call Claude SDK and return structured response
        
        This is the main method that provides a synchronous interface to the async SDK.
        
        Args:
            prompt: The prompt to send to Claude
            metadata: Optional metadata for tracking/logging
            
        Returns:
            Dict containing:
                - success: bool
                - response: str - The raw response from Claude
                - processing_time: float - Time taken for the call
                - metadata: Dict - Additional information
        """
        self._stats["total_calls"] += 1
        start_time = time.time()
        
        # Check cache if enabled
        if self.use_cache:
            cache_key = self._generate_cache_key(prompt)
            cached_result = url_cache.get(cache_key, "claude")
            if cached_result:
                self._stats["cache_hits"] += 1
                self._stats["successful_calls"] += 1
                processing_time = time.time() - start_time
                self._stats["total_processing_time"] += processing_time
                
                return {
                    "success": True,
                    "response": cached_result["response"],
                    "processing_time": processing_time,
                    "metadata": {
                        **cached_result.get("metadata", {}),
                        "from_cache": True,
                        "prompt_length": len(prompt)
                    }
                }
        
        try:
            # Run the async SDK call in a sync wrapper
            response = anyio.run(self._async_call_claude, prompt)
            
            processing_time = time.time() - start_time
            self._stats["total_processing_time"] += processing_time
            
            if not response:
                self._stats["failed_calls"] += 1
                raise ClaudeMCPError(
                    "Empty response from Claude SDK",
                    error_type="empty_response_error",
                    details={
                        "processing_time": processing_time
                    }
                )
            
            self._stats["successful_calls"] += 1
            
            result_data = {
                "success": True,
                "response": response.strip(),
                "processing_time": processing_time,
                "metadata": {
                    "prompt_length": len(prompt),
                    "response_length": len(response),
                    "from_cache": False,
                    "sdk_version": "claude-code-sdk",
                    **(metadata or {})
                }
            }
            
            # Cache successful result
            if self.use_cache:
                url_cache.set(cache_key, "claude", result_data)
            
            return result_data
        
        except TimeoutError:
            self._stats["failed_calls"] += 1
            processing_time = time.time() - start_time
            self._stats["total_processing_time"] += processing_time
            
            raise ClaudeMCPError(
                f"Claude SDK timed out after {self.timeout} seconds",
                error_type="timeout_error",
                details={
                    "timeout": self.timeout,
                    "processing_time": processing_time
                }
            )
        
        except ClaudeMCPError:
            raise
            
        except Exception as e:
            self._stats["failed_calls"] += 1
            processing_time = time.time() - start_time
            self._stats["total_processing_time"] += processing_time
            
            raise ClaudeMCPError(
                f"Unexpected error calling Claude SDK: {str(e)}",
                error_type="unexpected_error",
                details={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "processing_time": processing_time
                }
            )
    
    def call_claude_simple(self, prompt: str) -> str:
        """Legacy method for backward compatibility - returns just the response string"""
        try:
            result = self.call_claude(prompt)
            return result.get("response", "") if result.get("success") else ""
        except:
            return ""
    
    def call_claude_web(self, prompt: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Web-optimized Claude call with structured error handling"""
        try:
            result = self.call_claude(prompt, metadata={"request_id": request_id})
            if result.get("success"):
                return {
                    "success": True,
                    "data": {
                        "response": result["response"],
                        "processing_time": result.get("processing_time", 0),
                        "metadata": result.get("metadata", {})
                    }
                }
            else:
                return create_error_response(
                    "Claude processing failed",
                    error_type="processing_error"
                )
        except ClaudeMCPError as e:
            return create_error_response(
                str(e),
                error_type=e.error_type,
                status_code=500
            )
        except Exception as e:
            return create_error_response(
                f"Unexpected error: {str(e)}",
                error_type="unexpected_error",
                status_code=500
            )
    
    def extract_json_from_response(self, response: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Extract JSON from Claude's response with error details
        
        Returns:
            Tuple of (parsed_json, error_message)
        """
        # Try the utility function first
        result = safe_json_parse(response)
        if result:
            return result, None
        
        # If that fails, provide detailed error
        return None, "Could not extract valid JSON from response"
    
    def process_with_chunking(self, prompt_template: str, content: str, 
                            max_chunk_size: int = 5000) -> Dict[str, Any]:
        """Process large content by chunking if necessary
        
        Args:
            prompt_template: Template with {content} placeholder
            content: The content to process
            max_chunk_size: Maximum size per chunk
            
        Returns:
            Dict with success status and combined results
        """
        if len(content) <= max_chunk_size:
            # Process as single chunk
            prompt = prompt_template.format(content=content)
            return self.call_claude(prompt)
        
        # Process in chunks
        chunks = chunk_text(content, max_chunk_size)
        results = []
        total_processing_time = 0
        
        for i, chunk in enumerate(chunks):
            chunk_prompt = prompt_template.format(content=chunk)
            chunk_metadata = {
                "chunk_number": i + 1,
                "total_chunks": len(chunks)
            }
            
            try:
                result = self.call_claude(chunk_prompt, metadata=chunk_metadata)
                results.append(result)
                total_processing_time += result.get("processing_time", 0)
            except ClaudeMCPError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "error_details": e.details,
                    "partial_results": results
                }
        
        # Combine results
        combined_response = "\n\n".join([r["response"] for r in results])
        
        return {
            "success": True,
            "response": combined_response,
            "processing_time": total_processing_time,
            "metadata": {
                "chunks_processed": len(chunks),
                "original_content_length": len(content)
            }
        }
    
    def clear_cache(self):
        """Clear the Claude response cache"""
        if self.use_cache:
            # Note: This clears the entire URL cache, not just Claude responses
            # In production, you might want a separate cache instance
            url_cache.clear()
    
    # Additional compatibility methods for drop-in replacement
    
    def format_error_for_web(self, error: Exception, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Format error messages for web API responses"""
        if isinstance(error, ClaudeMCPError):
            return {
                "error": True,
                "error_type": error.error_type,
                "message": str(error),
                "request_id": request_id or "unknown",
                "timestamp": datetime.now().isoformat(),
                "details": error.details,
                "user_friendly_message": self._get_user_friendly_error(str(error))
            }
        else:
            return {
                "error": True,
                "error_type": "system_error",
                "message": str(error),
                "request_id": request_id or "unknown",
                "timestamp": datetime.now().isoformat(),
                "user_friendly_message": "An unexpected error occurred. Please try again."
            }
    
    @staticmethod
    def _get_user_friendly_error(error_msg: str) -> str:
        """Convert technical errors to user-friendly messages"""
        if "timed out" in error_msg.lower():
            return "The request took too long to process. This might happen with complex pages. Please try again or contact support if the issue persists."
        elif "claude sdk" in error_msg.lower():
            return "The AI assistant encountered an error. Please try again in a moment."
        elif "empty response" in error_msg.lower():
            return "The AI assistant did not provide a response. Please try again."
        else:
            return "An error occurred while processing your request. Please try again."
    
    @staticmethod
    def format_application_info(info_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format extracted application info for web display"""
        return {
            "formatted": True,
            "sections": [
                {
                    "title": "Program Overview",
                    "content": {
                        "name": info_data.get("program_name", "Unknown Program"),
                        "description": info_data.get("description", "No description available")
                    }
                },
                {
                    "title": "Eligibility",
                    "content": {
                        "requirements": info_data.get("eligibility", {}).get("requirements", []),
                        "restrictions": info_data.get("eligibility", {}).get("restrictions", [])
                    }
                },
                {
                    "title": "Important Dates",
                    "content": info_data.get("dates", {})
                },
                {
                    "title": "Benefits",
                    "content": info_data.get("benefits", [])
                },
                {
                    "title": "Application Process",
                    "content": info_data.get("application_process", [])
                },
                {
                    "title": "Required Documents",
                    "content": info_data.get("required_documents", [])
                },
                {
                    "title": "Contact Information",
                    "content": info_data.get("contact", {})
                }
            ],
            "raw_data": info_data
        }
    
    @staticmethod
    def format_questions_for_display(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format extracted questions for web form display"""
        formatted_questions = []
        
        for idx, q in enumerate(questions):
            formatted_q = {
                "id": f"q_{idx}",
                "question": q.get("question", ""),
                "type": q.get("type", "text"),
                "required": q.get("required", False),
                "field_name": q.get("field_name", f"field_{idx}"),
                "section": q.get("section", "General"),
                "help_text": q.get("help_text", ""),
                "constraints": q.get("constraints", {}),
                "options": q.get("options", [])
            }
            
            # Add UI-specific formatting
            formatted_q["ui_type"] = ClaudeSDK._map_to_ui_type(formatted_q["type"])
            formatted_q["validation_rules"] = ClaudeSDK._get_validation_rules(formatted_q)
            
            formatted_questions.append(formatted_q)
        
        return formatted_questions
    
    @staticmethod
    def _map_to_ui_type(field_type: str) -> str:
        """Map field types to UI component types"""
        ui_mapping = {
            "text": "input",
            "textarea": "textarea",
            "select": "dropdown",
            "radio": "radio_group",
            "checkbox": "checkbox_group",
            "email": "email_input",
            "date": "date_picker",
            "file": "file_upload",
            "number": "number_input",
            "tel": "phone_input"
        }
        return ui_mapping.get(field_type.lower(), "input")
    
    @staticmethod
    def _get_validation_rules(question: Dict[str, Any]) -> Dict[str, Any]:
        """Generate validation rules for form fields"""
        rules = {}
        
        if question.get("required"):
            rules["required"] = True
            
        constraints = question.get("constraints", {})
        
        if "max_length" in constraints:
            rules["maxLength"] = constraints["max_length"]
            
        if "pattern" in constraints:
            rules["pattern"] = constraints["pattern"]
            
        if question["type"] == "email":
            rules["email"] = True
            
        if question["type"] == "number":
            if "min" in constraints:
                rules["min"] = constraints["min"]
            if "max" in constraints:
                rules["max"] = constraints["max"]
                
        return rules
    
    @staticmethod
    def format_answers_for_review(answers: List[Dict[str, Any]], include_confidence: bool = True) -> Dict[str, Any]:
        """Format generated answers for user review"""
        formatted = {
            "total_questions": len(answers),
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
            "answers": []
        }
        
        for idx, ans in enumerate(answers):
            confidence = ans.get("confidence", "medium")
            
            # Update confidence counts
            if confidence == "high":
                formatted["high_confidence"] += 1
            elif confidence == "medium":
                formatted["medium_confidence"] += 1
            else:
                formatted["low_confidence"] += 1
            
            formatted_ans = {
                "id": f"ans_{idx}",
                "question": ans.get("question", ""),
                "answer": ans.get("answer", ""),
                "field_name": ans.get("field_name", f"field_{idx}"),
                "needs_review": confidence != "high",
                "notes": ans.get("notes", "")
            }
            
            if include_confidence:
                formatted_ans["confidence"] = confidence
                formatted_ans["confidence_reason"] = ans.get("confidence_reason", "")
            
            formatted["answers"].append(formatted_ans)
        
        return formatted


# Create an alias for backward compatibility
ClaudeMCP = ClaudeSDK


class HTMLContentProcessor:
    """Process HTML content for optimal Claude analysis"""
    
    @staticmethod
    def prepare_html_for_claude(html_content: str, max_chars: int = 8000) -> str:
        """Prepare HTML content for Claude analysis"""
        # Remove script and style tags
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove excessive whitespace
        html_content = re.sub(r'\s+', ' ', html_content)
        
        # If content is too long, try to extract the most relevant parts
        if len(html_content) > max_chars:
            # Prioritize form-related content
            form_content = HTMLContentProcessor._extract_form_content(html_content)
            if form_content and len(form_content) < max_chars:
                return form_content
            
            # Otherwise, take a smart slice
            return HTMLContentProcessor._smart_truncate(html_content, max_chars)
        
        return html_content
    
    @staticmethod
    def _extract_form_content(html: str) -> Optional[str]:
        """Extract form-related content from HTML"""
        # Try to find form tags
        form_match = re.search(r'<form[^>]*>.*?</form>', html, re.DOTALL | re.IGNORECASE)
        if form_match:
            return form_match.group(0)
        
        # Look for common form indicators
        form_indicators = [
            r'<div[^>]*(?:class|id)=["\'][^"\']*(?: form|application|questionnaire)[^"\']["\'][^>]*>.*?</div>',
            r'<section[^>]*(?:class|id)=["\'][^"\']*(?: form|application|questionnaire)[^"\']["\'][^>]*>.*?</section>'
        ]
        
        for pattern in form_indicators:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    @staticmethod
    def _smart_truncate(content: str, max_chars: int) -> str:
        """Truncate content while trying to preserve structure"""
        if len(content) <= max_chars:
            return content
        
        # Try to find a good break point
        truncated = content[:max_chars]
        
        # Look for last complete tag
        last_tag_end = truncated.rfind('>')
        if last_tag_end > max_chars * 0.8:  # If we're not losing too much
            return truncated[:last_tag_end + 1]
        
        return truncated


class ApplicationStateManager:
    """Manage application processing state for web UI"""
    
    def __init__(self):
        self.states = {}
    
    def create_state(self, app_name: str) -> str:
        """Create a new application state and return session ID"""
        session_id = f"{app_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(self)}"
        
        self.states[session_id] = {
            "app_name": app_name,
            "created_at": datetime.now().isoformat(),
            "status": "initialized",
            "steps": {
                "info_extraction": {"status": "pending"},
                "question_extraction": {"status": "pending"},
                "answer_generation": {"status": "pending"}
            },
            "data": {},
            "errors": []
        }
        
        return session_id
    
    def update_step(self, session_id: str, step: str, status: str, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        """Update the status of a processing step"""
        if session_id not in self.states:
            raise ValueError(f"Invalid session ID: {session_id}")
        
        self.states[session_id]["steps"][step] = {
            "status": status,
            "updated_at": datetime.now().isoformat()
        }
        
        if data:
            self.states[session_id]["data"][step] = data
        
        if error:
            self.states[session_id]["errors"].append({
                "step": step,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
    
    def get_state(self, session_id: str) -> Dict[str, Any]:
        """Get the current state of an application"""
        if session_id not in self.states:
            raise ValueError(f"Invalid session ID: {session_id}")
        
        return self.states[session_id]
    
    def get_progress(self, session_id: str) -> Dict[str, Any]:
        """Get progress summary for an application"""
        state = self.get_state(session_id)
        
        total_steps = len(state["steps"])
        completed_steps = sum(1 for step in state["steps"].values() if step["status"] == "completed")
        
        return {
            "percentage": int((completed_steps / total_steps) * 100),
            "completed": completed_steps,
            "total": total_steps,
            "current_step": next((name for name, step in state["steps"].items() if step["status"] == "in_progress"), None),
            "status": state["status"]
        }
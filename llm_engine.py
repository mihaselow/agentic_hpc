import backoff
import logging

# We will try to import a provider from ai4free. 
# Based on the documentation, there are several providers like LEO or Blackbox.
try:
    from ai4free import Blackbox as Provider
    # Fallback to LEO or others if preferred: from ai4free import LEO as Provider
except ImportError:
    # Fallback for type hinting or if ai4free is not installed correctly yet
    class Provider:
        def chat(self, prompt: str) -> str:
            raise NotImplementedError("ai4free provider not installed or imported properly.")

# Configure basic logging for backoff
logging.getLogger('backoff').addHandler(logging.StreamHandler())
logging.getLogger('backoff').setLevel(logging.INFO)

class LLMEngine:
    def __init__(self):
        try:
            self.provider = Provider()
        except Exception as e:
            logging.error(f"Failed to initialize LLM Provider: {e}")
            self.provider = None

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        max_time=60,
        jitter=backoff.full_jitter
    )
    def _call_api(self, prompt: str) -> str:
        """
        Internal method to call the LLM API with exponential backoff.
        Retries up to 5 times or for a maximum of 60 seconds.
        """
        if not self.provider:
            raise RuntimeError("LLM Provider is not initialized.")
        
        # Depending on the specific ai4free provider, the method might be chat() or ask().
        # We try chat() first, fallback to ask() if needed.
        if hasattr(self.provider, 'chat'):
            response = self.provider.chat(prompt)
        elif hasattr(self.provider, 'ask'):
            response = self.provider.ask(prompt)
        else:
            raise NotImplementedError("Provider does not support chat() or ask() methods.")
            
        if not response:
            raise ValueError("Empty response from LLM API")
            
        return response

    def generate(self, user_prompt: str, context: str) -> str:
        """
        Generates a response from the LLM based on the user prompt and the
        Source of Truth context.
        """
        system_prompt = (
            "You are an expert HPC Architect and Senior Full-Stack AI Engineer.
"
            "You are strictly bound by the rules and 'Source of Truth' context provided below.
"
            "Always follow the '1 core per 100k cells' rule and cross-reference hardware limits.
"
            "Provide output strictly as requested, separating the Slurm script and the Solver Journal.
"
            "Ensure 'Architectural Certification' logic is applied:
"
            "1. Validate requested cores against hardware max.
"
            "2. Ensure --exclusive and --cpu-bind=cores in Slurm script.
"
            "3. Ensure the journal ends with an explicit 'exit' command.
"
            "
"
            "--- Source of Truth Context ---
"
            f"{context}
"
            "-------------------------------

"
        )
        
        full_prompt = f"{system_prompt}
User Request:
{user_prompt}"
        
        return self._call_api(full_prompt)

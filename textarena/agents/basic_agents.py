import asyncio
from abc import ABC, abstractmethod
import os, time
from typing import Optional, Tuple

from textarena.core import Agent
import textarena as ta 

__all__ = ["HumanAgent", "OpenRouterAgent", "GeminiAgent", "OpenAIAgent", "HFLocalAgent", "CerebrasAgent", "AWSBedrockAgent", "AnthropicAgent"]
STANDARD_GAME_PROMPT = "You are a competitive game player. Make sure you read the game instructions carefully, and always follow the required format."
    

class HumanAgent(Agent):
    """ Human agent class that allows the user to input actions manually """
    def __init__(self):
        super().__init__()

    def __call__(self, observation: str) -> str:
        """
        Process the observation and return the action.
        
        Args:
            observation (str): The input string to process.
            
        Returns:
            str: The response generated by the agent.
        """
        print("\n\n+++ +++ +++") # for easies visualization of what is part of each turns observation
        return input(f"Current observations: {observation}\nPlease enter the action: ")


class OpenRouterAgent(Agent):
    """ Agent class using the OpenRouter API to generate responses. """
    def __init__(self, model_name: str, system_prompt: Optional[str] = STANDARD_GAME_PROMPT, verbose: bool = False, **kwargs):
        """
        Args:
            model_name (str): The name of the model.
            system_prompt (Optional[str]): The system prompt to use (default: STANDARD_GAME_PROMPT)
            verbose (bool): If True, additional debug info will be printed.
            **kwargs: Additional keyword arguments to pass to the OpenAI API call.
        """
        super().__init__()
        self.model_name = model_name 
        self.verbose = verbose 
        self.system_prompt = system_prompt
        self.kwargs = kwargs

        try:
            from openai import OpenAI
            from openai._exceptions import OpenAIError
        except ImportError:
            raise ImportError("OpenAI package is required for OpenRouterAgent. Install it with: pip install openai")
        
        api_key = os.getenv("OPENROUTER_API_KEY") # Set the open router api key from an environment variable
        if not api_key:
            raise ValueError("OpenRouter API key not found. Please set the OPENROUTER_API_KEY environment variable.")
        self.client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    def _make_request(self, observation: str) -> str:
        """ Make a single API request to OpenRouter and return the generated message. """
        messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": observation}]
        response = self.client.chat.completions.create(model=self.model_name, messages=messages, n=1, stop=None, **self.kwargs)
        return response.choices[0].message.content.strip()

    def _retry_request(self, observation: str, retries: int = 3, delay: int = 5) -> str:
        """
        Attempt to make an API request with retries.

        Args:
            observation (str): The input to process.
            retries (int): The number of attempts to try.
            delay (int): Seconds to wait between attempts.

        Raises:
            Exception: The last exception caught if all retries fail.
        """
        last_exception = None
        for attempt in range(1, retries + 1):
            try:
                response = self._make_request(observation)
                if self.verbose:
                    print(f"\nObservation: {observation}\nResponse: {response}")
                return response

            except Exception as e:
                last_exception = e
                print(f"Attempt {attempt} failed with error: {e}")
                if attempt < retries:
                    time.sleep(delay)
        raise last_exception

    def __call__(self, observation: str) -> str:
        """
        Process the observation using the OpenRouter API and return the action.

        Args:
            observation (str): The input string to process.

        Returns:
            str: The generated response.
        """
        if not isinstance(observation, str):
            raise ValueError(f"Observation must be a string. Received type: {type(observation)}")
        return self._retry_request(observation)


class GeminiAgent(Agent):
    """Agent class using the Google Gemini API to generate responses."""
    def __init__(self, model_name: str, system_prompt: Optional[str]=STANDARD_GAME_PROMPT, verbose: bool=False, generation_config: Optional[dict]=None):
        """
        Initialize the Gemini agent.
        
        Args:
            model_name (str): The name of the model.
            system_prompt (Optional[str]): The system prompt to use (default: STANDARD_GAME_PROMPT).
            verbose (bool): If True, additional debug info will be printed.
            generation_config (Optional[dict]): The configuration for text generation.
        """
        super().__init__()
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.verbose = verbose

        try: import google.generativeai as genai
        except ImportError: raise ImportError("Google Generative AI package is required for GeminiAgent. Install it with: pip install google-generativeai")
        
        # Set the Gemini API key from an environment variable
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("Gemini API key not found. Please set the GEMINI_API_KEY environment variable.")
        
        # Configure the Gemini client
        genai.configure(api_key=api_key)
        
        # Use default generation config if none is provided
        if generation_config is None:
            generation_config = {"temperature": 1, "top_p": 0.95, "top_k": 40, "max_output_tokens": 8192, "response_mime_type": "text/plain"}
        self.generation_config = generation_config
        self.model = genai.GenerativeModel(model_name=self.model_name, generation_config=self.generation_config) # Create the Gemini model
    
    def _make_request(self, observation: str) -> str:
        """
        Make a single API request to Gemini and return the generated message.
        
        Args:
            observation (str): The input string to process.
        
        Returns:
            str: The generated response text.
        """
        response = self.model.generate_content(f"Instructions: {self.system_prompt}\n\n{observation}")
        if self.verbose: print(f"\nObservation: {observation}\nResponse: {response.text}")
        return response.text.strip()
    
    def _retry_request(self, observation: str, retries: int = 3, delay: int = 5) -> str:
        """
        Attempt to make an API request with retries.
        
        Args:
            observation (str): The input to process.
            retries (int): The number of attempts to try.
            delay (int): Seconds to wait between attempts.
        
        Raises:
            Exception: The last exception caught if all retries fail.
        """
        last_exception = None
        for attempt in range(1, retries + 1):
            try:
                return self._make_request(observation)
            except Exception as e:
                last_exception = e
                print(f"Attempt {attempt} failed with error: {e}")
                if attempt < retries:
                    time.sleep(delay)
        raise last_exception
    
    def __call__(self, observation: str) -> str:
        """
        Process the observation using the Gemini API and return the generated response.
        
        Args:
            observation (str): The input string to process.
        
        Returns:
            str: The generated response.
        """
        if not isinstance(observation, str): 
            raise ValueError(f"Observation must be a string. Received type: {type(observation)}")
        return self._retry_request(observation)


class OpenAIAgent(Agent):
    """Agent class using the OpenAI API to generate responses."""

    def __init__(self, model_name: str, system_prompt: Optional[str]=STANDARD_GAME_PROMPT, verbose: bool=False, api_key: str|None=None, base_url: str|None=None,**kwargs):
        """
        Initialize the OpenAI agent.
        
        Args:
            model_name (str): The name of the model.
            system_prompt (Optional[str]): The system prompt to use (default: STANDARD_GAME_PROMPT).
            verbose (bool): If True, additional debug info will be printed.
            api_key (str | None): The API key for the OpenAI API.
            base_url (str | None): The base URL for the OpenAI API.
            **kwargs: Additional keyword arguments to pass to the OpenAI API call.
        """
        super().__init__()
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.verbose = verbose
        self.kwargs = kwargs

        try: from openai import OpenAI
        except ImportError: raise ImportError("OpenAI package is required for OpenAIAgent. Install it with: pip install openai")

        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key: raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
    
    def _make_request(self, observation: str) -> str:
        """
        Make a single API request to OpenAI and return the generated message.
        
        Args:
            observation (str): The input string to process.
        
        Returns:
            str: The generated response text.
        """
        messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": observation}]
        
        # Make the API call using the provided model and messages.
        completion = self.client.chat.completions.create(model=self.model_name, messages=messages, n=1, stop=None, **self.kwargs)
        return completion.choices[0].message.content.strip()
    
    def _retry_request(self, observation: str, retries: int=3, delay: int=5) -> str:
        """
        Attempt to make an API request with retries.
        
        Args:
            observation (str): The input to process.
            retries (int): The number of attempts to try.
            delay (int): Seconds to wait between attempts.
        
        Raises:
            Exception: The last exception caught if all retries fail.
        """
        last_exception = None
        for attempt in range(1, retries + 1):
            try:
                response = self._make_request(observation)
                if self.verbose:
                    print(f"\nObservation: {observation}\nResponse: {response}")
                return response
            except Exception as e:
                last_exception = e
                print(f"Attempt {attempt} failed with error: {e}")
                if attempt < retries:
                    time.sleep(delay)
        raise last_exception
    
    def __call__(self, observation: str) -> str:
        """
        Process the observation using the OpenAI API and return the generated response.
        
        Args:
            observation (str): The input string to process.
        
        Returns:
            str: The generated response.
        """
        if not isinstance(observation, str):
            raise ValueError(f"Observation must be a string. Received type: {type(observation)}")
        return self._retry_request(observation)


class HFLocalAgent(Agent):
    """ Hugging Face local agent class that uses the Hugging Face Transformers library """
    def __init__(self, model_name: str, device: str = "auto", quantize: bool = False, max_new_tokens: int = 1024,
                 hf_kwargs: dict = None,):
        """
        Initialize the Hugging Face local agent.
        
        Args:
            model_name (str): The name of the model.
            device (str): Device to use for model inference (default: "auto").
            quantize (bool): Whether to load the model in 8-bit quantized format (default: False).
        """
        super().__init__()
        
        try:
            from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
        except ImportError:
            raise ImportError("Transformers library is required for HFLocalAgent. Install it with: pip install transformers")
            
        ## Initialize the Hugging Face model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if quantize: self.model = AutoModelForCausalLM.from_pretrained(model_name, load_in_8bit=True, device_map=device, **hf_kwargs)
        else: self.model = AutoModelForCausalLM.from_pretrained(model_name, device_map=device, **hf_kwargs)
        self.system_prompt = STANDARD_GAME_PROMPT
        self.pipeline = pipeline('text-generation', max_new_tokens=max_new_tokens, model=self.model, tokenizer=self.tokenizer) ## Initialize the Hugging Face pipeline
    
    def __call__(self, observation: str) -> str:
        """
        Process the observation using the Hugging Face model and return the action.
        
        Args:
            observation (str): The input string to process.
        
        Returns:
            str: The response generated by the model.
        """
        try: # Generate a response
            response = self.pipeline(self.system_prompt+"\n"+observation, num_return_sequences=1, return_full_text=False)
            action = response[0]['generated_text'].strip() # Extract and return the text output
            return action
        except Exception as e:
            return f"An error occurred: {e}"



class CerebrasAgent(Agent):
    """ Cerebras agent class that uses the Cerebras API to generate responses """
    def __init__(self, model_name: str, system_prompt: str | None = None):
        """
        Initialize the Cerebras agent.

        Args:
            model_name (str): The name of the model.
            system_prompt (str): The system prompt to use (default: "You are a competitive game player.").
        """
        super().__init__()
        self.model_name = model_name
        
        try: from cerebras.cloud.sdk import Cerebras
        except ImportError: raise ImportError("Cerebras SDK is required for CerebrasAgent. Install it with: pip install cerebras-cloud-sdk")
            
        self.client = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY")) # This is the default and can be omitted

        ## Set the system prompt
        if system_prompt is None:
            self.system_prompt = "You are a competitive game player. Make sure you read the game instructions carefully, and always follow the required format."
        else:
            self.system_prompt = system_prompt

    def __call__(self, observation: str) -> str:
        """
        Process the observation using the Cerebras model and return the action.

        Args:
            observation (str): The input string to process.

        Returns:
            str: The response generated by the model.
        """
        try:
            messages=[{"role": "system", "content": self.system_prompt}, {"role": "user", "content": observation}]
            response = self.client.chat.completions.create(model=self.model_name, messages=messages, top_p=0.9, temperature=0.9)
            action = response.choices[0].message.content.strip() # Extract the assistant's reply
            return action
        except Exception as e:
            return f"An error occurred: {e}"


class AWSBedrockAgent(Agent):
    """ AWS Bedrock agent class that interacts with Claude 3 Haiku via AWS Bedrock Runtime API """
    def __init__(self, model_id: str,  region_name: str="us-east-1", system_prompt: Optional[str]=STANDARD_GAME_PROMPT, verbose: bool=False, **kwargs):
        """
        Initialize the AWS Bedrock agent.
        
        Args:
            model_name (str): The ID of the AWS Bedrock model to use.
            region_name (str): AWS region for Bedrock service.
            system_prompt (Optional[str]): The system prompt to use.
            verbose (bool): If True, print debug information.
            **kwargs: Additional parameters for inference configuration.
        """
        super().__init__()
        self.model_id = model_id
        self.region_name = region_name
        self.system_prompt = system_prompt
        self.verbose = verbose
        self.kwargs = kwargs

        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            raise ImportError("Boto3 is required for AWSBedrockAgent. Install it with: pip install boto3")
        self.client = boto3.client("bedrock-runtime", region_name=self.region_name)

    def _make_request(self, observation: str) -> str:
        """ Make an API request to AWS Bedrock."""
        conversation = [{"role": "user", "content": [{"text": observation}]}]
        systemPrompt = [{ "text": self.system_prompt }]
        try:
            inference_config={"maxTokens": 512, "temperature": 0.9, "topP": 0.9, **self.kwargs}
            response = self.client.converse(modelId=self.model_id, messages=conversation, system=systemPrompt, inferenceConfig=inference_config)
            response_text = response["output"]["message"]["content"][0]["text"].strip()
            if self.verbose:
                print(f"\nObservation: {observation}\nResponse: {response_text}")
            return response_text
        except Exception as e:
            return f"ERROR: Can't invoke '{self.model_id}'. Reason: {e}"

    def __call__(self, observation: str) -> str:
        """ Process the observation using AWS Bedrock and return the response."""
        if not isinstance(observation, str):
            raise ValueError(f"Observation must be a string. Received type: {type(observation)}")
        return self._make_request(observation)


class AnthropicAgent(Agent):
    """Agent class using the Anthropic Claude API to generate responses."""
    def __init__(self, model_name: str, system_prompt: Optional[str]=STANDARD_GAME_PROMPT, max_tokens: int=1000, temperature: float=0.9, verbose: bool=False):
        """
        Initialize the Anthropic agent.

        Args:
            model_name (str): The name of the Claude model (e.g., "claude-3-5-sonnet-20241022").
            system_prompt (Optional[str]): The system prompt to use (default: STANDARD_GAME_PROMPT).
            max_tokens (int): The maximum number of tokens to generate.
            temperature (float): The temperature for randomness in response generation.
            verbose (bool): If True, additional debug info will be printed.
        """
        super().__init__()
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.verbose = verbose
        
        try: import anthropic
        except ImportError: raise ImportError("Anthropic package is required for AnthropicAgent. Install it with: pip install anthropic")
        self.client = anthropic.Anthropic()
    
    def _make_request(self, observation: str) -> str:
        """ Make a single API request to Anthropic and return the generated message """
        messages=[{"role": "user", "content": [{"type": "text", "text": observation}]}]
        response = self.client.messages.create(model=self.model_name, max_tokens=self.max_tokens, temperature=self.temperature, system=self.system_prompt, messages=messages)
        return response.content[0].text.strip()
    
    def _retry_request(self, observation: str, retries: int=3, delay: int=5) -> str:
        """
        Attempt to make an API request with retries.

        Args:
            observation (str): The input to process.
            retries (int): The number of attempts to try.
            delay (int): Seconds to wait between attempts.

        Raises:
            Exception: The last exception caught if all retries fail.
        """
        last_exception = None
        for attempt in range(1, retries + 1):
            try:
                response = self._make_request(observation)
                if self.verbose:
                    print(f"\nObservation: {observation}\nResponse: {response}")
                return response
            except Exception as e:
                last_exception = e
                print(f"Attempt {attempt} failed with error: {e}")
                if attempt < retries:
                    time.sleep(delay)
        raise last_exception
    
    def __call__(self, observation: str) -> str:
        """
        Process the observation using the Anthropic API and return the generated response.
        
        Args:
            observation (str): The input string to process.
        
        Returns:
            str: The generated response.
        """
        if not isinstance(observation, str):
            raise ValueError(f"Observation must be a string. Received type: {type(observation)}")
        return self._retry_request(observation)

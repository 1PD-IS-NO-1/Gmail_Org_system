from langchain_google_genai import ChatGoogleGenerativeAI
import pandas as pd
import json
from langchain_core.messages import HumanMessage, SystemMessage
import matplotlib.pyplot as plt  # Corrected import for matplotlib

# Configure Google Generative AI
GOOGLE_GENAI_API_KEY = "AIzaSyD5tZR02ryMjdV3unPEqHzlNFUZuPtSPyk"  # Replace with your actual API key
llm = ChatGoogleGenerativeAI(
    api_key=GOOGLE_GENAI_API_KEY,
    model="gemini-1.5-flash",  # Replace with the actual model name
    temperature=0.7
)

# Load JSON data
with open("emails.json", "r", errors="replace") as f:
    json_data = json.load(f)

class EmailAnalyzer:
    def __init__(self, llm, data):
        self.llm = llm
        self.df = pd.DataFrame(data)

    def get_code_from_llm(self, question: str) -> str:
        """Get Python code from LLM to answer the question"""
        system_message = f"""You are a Python coding assistant. Given a pandas DataFrame 'df' with the following columns:
        {self.df.columns.tolist()}

        Generate Python code to answer the user's question if required; if not required, then you can manually give the answer to the user's question according to you using print and you can give your suggestion.
        - Use pandas operations on the DataFrame 'df'
        - Return only the executable Python code, no explanations
        - Make sure the code prints the result
        - Don't include triple backticks or markdown formatting
        
        Example:
        Question: "Show number of emails per category"
        Response: print(df['category'].value_counts())
        """

        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=f"Generate code to answer: {question}")
        ]

        response = self.llm.invoke(messages)
        return response.content.strip().replace('```python', '').replace('```', '')

    def execute_code(self, code: str):
        """Execute the generated code safely"""
        try:
            # Create a safe execution environment with necessary objects
            exec_globals = {
                'df': self.df,
                'pd': pd,
                'plt': plt,
                'print': print
            }
            # Execute the code
            exec(code, exec_globals)
            
        except Exception as e:
            print(f"Error executing code: {str(e)}")

def process_question(question: str):
    """Process a user question and return the answer"""
    analyzer = EmailAnalyzer(llm, json_data)
    code = analyzer.get_code_from_llm(question)
    analyzer.execute_code(code)

if __name__ == "__main__":
    print("Email Analysis Assistant (type 'exit' to quit)")
    
    while True:
        question = input("\nEnter your question: ")
        if question.lower() == 'exit':
            break
        
        process_question(question)